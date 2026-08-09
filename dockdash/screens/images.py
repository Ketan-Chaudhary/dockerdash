"""Images management tab."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Static

from dockdash.docker_client import DockerClient, DockerClientError
from dockdash.modals.confirm_dialog import ConfirmDialog
from dockdash.modals.container_create import ContainerCreateDialog
from dockdash.modals.dockerfile_editor import DockerfileEditorDialog
from dockdash.modals.input_dialog import InputDialog, MultiInputDialog
from dockdash.modals.inspect_dialog import InspectDialog
from dockdash.widgets.search_bar import SearchBar


class ImagesTab(Vertical):
    """Image management tab with table and actions."""

    BINDINGS = [
        Binding("p", "pull_image", "Pull", show=True),
        Binding("d", "delete_image", "Delete", show=True),
        Binding("t", "tag_image", "Tag", show=True),
        Binding("c", "create_container", "Create Container", show=True),
        Binding("i", "inspect_image", "Inspect", show=True),
        Binding("h", "image_history", "History", show=True),
        Binding("e", "edit_dockerfile", "Dockerfile", show=True),
        Binding("slash", "search", "Search", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._docker = DockerClient()
        self._images: list[dict] = []
        self._filtered: list[dict] = []

    def compose(self) -> ComposeResult:
        yield SearchBar(id="image-search")
        yield Static(
            "[#79c0ff bold]IMAGES[/]  [#484f58]p[/]=pull  "
            "[#484f58]d[/]=delete  [#484f58]t[/]=tag  "
            "[#484f58]c[/]=create container  "
            "[#484f58]i[/]=inspect  [#484f58]h[/]=history  "
            "[#484f58]e[/]=dockerfile editor  "
            "[#484f58]/[/]=search",
            classes="actions-bar",
        )
        yield DataTable(id="image-table", cursor_type="row")

    def on_mount(self) -> None:
        table = self.query_one("#image-table", DataTable)
        table.add_columns("REPOSITORY", "TAG", "IMAGE ID", "SIZE", "CREATED")

    async def refresh_data(self) -> None:
        try:
            self._images = await self._docker.list_images()
            self._filtered = list(self._images)
            self._update_table()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    def _update_table(self) -> None:
        table = self.query_one("#image-table", DataTable)
        table.clear()
        for img in self._filtered:
            size_str = DockerClient.format_bytes(img.get("size", 0))
            created = img.get("created", "")[:19]
            table.add_row(
                img["repository"],
                img["tag"],
                img["id"],
                size_str,
                created,
                key=img["full_id"],
            )

    def _get_selected_image(self) -> dict | None:
        table = self.query_one("#image-table", DataTable)
        if table.row_count == 0:
            return None
        cursor_row = table.cursor_row
        if cursor_row < len(self._filtered):
            return self._filtered[cursor_row]
        return None

    # ── Search ────────────────────────────────────────────────────────

    def action_search(self) -> None:
        self.query_one("#image-search", SearchBar).show()

    def on_search_bar_changed(self, event: SearchBar.Changed) -> None:
        query = event.query.lower().strip()
        if not query:
            self._filtered = list(self._images)
        else:
            self._filtered = [
                img for img in self._images
                if query in img["repository"].lower()
                or query in img["tag"].lower()
                or query in img["id"].lower()
            ]
        self._update_table()

    def on_search_bar_dismissed(self, event: SearchBar.Dismissed) -> None:
        self.query_one("#image-table", DataTable).focus()

    # ── Navigation ────────────────────────────────────────────────────

    def action_cursor_down(self) -> None:
        self.query_one("#image-table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#image-table", DataTable).action_cursor_up()

    # ── Image Actions ─────────────────────────────────────────────────

    async def action_pull_image(self) -> None:
        def on_input(value: str | None) -> None:
            if value:
                self.app.call_later(self._do_pull, value)

        self.app.push_screen(
            InputDialog(
                title="⟨ PULL IMAGE ⟩",
                label="Image name (repository:tag):",
                placeholder="e.g. nginx:latest, python:3.12-slim, ubuntu",
            ),
            on_input,
        )

    async def _do_pull(self, image_spec: str) -> None:
        parts = image_spec.split(":")
        repo = parts[0]
        tag = parts[1] if len(parts) > 1 else "latest"

        self.notify(f"Pulling {repo}:{tag}...", severity="information")
        try:
            await self._docker.pull_image(repo, tag)
            self.notify(f"Pulled {repo}:{tag} successfully", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_delete_image(self) -> None:
        image = self._get_selected_image()
        if not image:
            return

        def on_confirm(result: bool) -> None:
            if result:
                self.app.call_later(self._do_delete, image["full_id"])

        self.app.push_screen(
            ConfirmDialog(
                title="⟨ DELETE IMAGE ⟩",
                message=f"Delete image '{image['repository']}:{image['tag']}'?",
                confirm_label="Delete",
                danger=True,
            ),
            on_confirm,
        )

    async def _do_delete(self, image_id: str) -> None:
        try:
            await self._docker.remove_image(image_id, force=True)
            self.notify("Image deleted", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_tag_image(self) -> None:
        image = self._get_selected_image()
        if not image:
            return

        def on_input(result: dict[str, str] | None) -> None:
            if result:
                self.app.call_later(
                    self._do_tag,
                    image["full_id"],
                    result.get("repo", ""),
                    result.get("tag", "latest"),
                )

        self.app.push_screen(
            MultiInputDialog(
                title="⟨ TAG IMAGE ⟩",
                fields=[
                    {
                        "id": "repo",
                        "label": "Repository name:",
                        "placeholder": "e.g. myapp, myregistry/myapp",
                        "default": image["repository"],
                    },
                    {
                        "id": "tag",
                        "label": "Tag:",
                        "placeholder": "e.g. latest, v1.0",
                        "default": image["tag"],
                    },
                ],
            ),
            on_input,
        )

    async def _do_tag(self, image_id: str, repo: str, tag: str) -> None:
        if not repo:
            self.notify("Repository name is required", severity="error")
            return
        try:
            await self._docker.tag_image(image_id, repo, tag)
            self.notify(f"Tagged as {repo}:{tag}", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_create_container(self) -> None:
        image = self._get_selected_image()
        default_image = ""
        if image:
            default_image = f"{image['repository']}:{image['tag']}"

        def on_config(config: dict | None) -> None:
            if config:
                self.app.call_later(self._do_create_container, config)

        self.app.push_screen(
            ContainerCreateDialog(default_image=default_image),
            on_config,
        )

    async def _do_create_container(self, config: dict) -> None:
        try:
            cid = await self._docker.create_container(config)
            self.notify(f"Container created: {cid}", severity="information")
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_inspect_image(self) -> None:
        image = self._get_selected_image()
        if not image:
            return
        try:
            data = await self._docker.inspect_image(image["full_id"])
            self.app.push_screen(
                InspectDialog(
                    title=f"{image['repository']}:{image['tag']}",
                    data=data,
                )
            )
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_image_history(self) -> None:
        image = self._get_selected_image()
        if not image:
            return
        try:
            history = await self._docker.image_history(image["full_id"])
            self.app.push_screen(
                InspectDialog(
                    title=f"History: {image['repository']}:{image['tag']}",
                    data={"layers": history},
                )
            )
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_edit_dockerfile(self) -> None:
        def on_result(result: dict | None) -> None:
            if result and result.get("action") == "build":
                self.app.call_later(
                    self._do_build,
                    result["path"],
                    result.get("tag"),
                    result.get("dockerfile", "Dockerfile"),
                )

        self.app.push_screen(DockerfileEditorDialog(), on_result)

    async def _do_build(
        self, path: str, tag: str | None, dockerfile: str
    ) -> None:
        self.notify(f"Building image from {path}...", severity="information")
        try:
            image_id = await self._docker.build_image(
                path=path, tag=tag, dockerfile=dockerfile
            )
            self.notify(f"Image built: {image_id}", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")
