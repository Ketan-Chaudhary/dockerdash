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
from dockdash.modals.image_layers import ImageLayersDialog
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
        Binding("l", "image_layers", "Layers", show=True),
        Binding("h", "image_layers", "History", show=False),
        Binding("u", "toggle_filter_mode", "Filter", show=True),
        Binding("P", "prune_dangling_images", "Prune Dangling", show=True),
        Binding("e", "edit_dockerfile", "Dockerfile", show=True),
        Binding("slash", "search", "Search", show=False),
        Binding("escape", "exit_search", "Exit Search", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._docker = DockerClient()
        self._images: list[dict] = []
        self._filtered: list[dict] = []
        self._filter_mode: str = "all"  # "all", "dangling", "unused"
        self._search_query: str = ""

    def compose(self) -> ComposeResult:
        yield SearchBar(id="image-search")
        yield DataTable(id="image-table", cursor_type="row")
        yield Static(
            "[#38bdf8 bold] ⯈ IMAGES [/]  [#38bdf8 bold]p[/][#cbd5e1]=pull  "
            "[#38bdf8 bold]d[/][#cbd5e1]=delete  [#38bdf8 bold]t[/][#cbd5e1]=tag  "
            "[#38bdf8 bold]c[/][#cbd5e1]=create container  "
            "[#38bdf8 bold]i[/][#cbd5e1]=inspect  [#38bdf8 bold]l[/][#cbd5e1]=layers  "
            "[#38bdf8 bold]u[/][#cbd5e1]=filter  "
            "[#38bdf8 bold]P[/][#cbd5e1]=prune  "
            "[#38bdf8 bold]e[/][#cbd5e1]=dockerfile  "
            "[#38bdf8 bold]/[/][#cbd5e1]=search",
            classes="actions-bar",
        )

    def on_mount(self) -> None:
        table = self.query_one("#image-table", DataTable)
        table.add_columns("REPOSITORY", "TAG", "IMAGE ID", "SIZE", "CREATED")

    async def refresh_data(self) -> None:
        try:
            self._images = await self._docker.list_images(all=True)
            self._apply_filters()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    def _apply_filters(self) -> None:
        query = self._search_query.lower().strip()
        candidates = list(self._images)

        if self._filter_mode == "dangling":
            candidates = [img for img in candidates if img.get("is_dangling")]
        elif self._filter_mode == "unused":
            candidates = [img for img in candidates if not img.get("in_use")]

        if query:
            candidates = [
                img for img in candidates
                if query in img["repository"].lower()
                or query in img["tag"].lower()
                or query in img["id"].lower()
            ]

        self._filtered = candidates
        self._update_table()
        self._update_actions_bar()

    def _update_actions_bar(self) -> None:
        try:
            bar = self.query_one(".actions-bar", Static)
            if self._filter_mode == "dangling":
                filter_badge = f"[#f87171 bold]u=dangling ({len(self._filtered)})[/]"
            elif self._filter_mode == "unused":
                filter_badge = f"[#fbbf24 bold]u=unused ({len(self._filtered)})[/]"
            else:
                filter_badge = "[#38bdf8 bold]u[/][#cbd5e1]=filter[/]"

            bar.update(
                f"[#38bdf8 bold] ⯈ IMAGES [/]  [#38bdf8 bold]p[/][#cbd5e1]=pull  "
                f"[#38bdf8 bold]d[/][#cbd5e1]=delete  [#38bdf8 bold]t[/][#cbd5e1]=tag  "
                f"[#38bdf8 bold]c[/][#cbd5e1]=create container  "
                f"[#38bdf8 bold]i[/][#cbd5e1]=inspect  [#38bdf8 bold]l[/][#cbd5e1]=layers  "
                f"{filter_badge}  "
                f"[#38bdf8 bold]P[/][#cbd5e1]=prune  "
                f"[#38bdf8 bold]e[/][#cbd5e1]=dockerfile  "
                f"[#38bdf8 bold]/[/][#cbd5e1]=search"
            )
        except Exception:
            pass

    def _update_table(self) -> None:
        with self.app.batch_update():
            table = self.query_one("#image-table", DataTable)
            current_keys = {row_key.value for row_key in table.rows.keys()}
            new_keys = {f"{img['full_id']}:{img['repository']}:{img['tag']}" for img in self._filtered}

            for key in current_keys - new_keys:
                table.remove_row(key)

            columns = list(table.columns.keys())

            for img in self._filtered:
                size_str = DockerClient.format_bytes(img.get("size", 0))
                created = img.get("created", "")[:19]

                repo_str = img["repository"]
                tag_str = img["tag"]
                if img.get("is_dangling"):
                    repo_str = "[#f87171 italic]<none>[/]"
                    tag_str = "[#f87171 italic]<dangling>[/]"
                elif not img.get("in_use"):
                    tag_str = f"{tag_str} [#94a3b8](unused)[/]"

                row_data = (
                    repo_str,
                    tag_str,
                    img["id"],
                    size_str,
                    created,
                )
                key = f"{img['full_id']}:{img['repository']}:{img['tag']}"

                if key in current_keys:
                    for col_key, cell_val in zip(columns, row_data):
                        table.update_cell(key, col_key, cell_val, update_width=True)
                else:
                    table.add_row(*row_data, key=key)

    def _get_selected_image(self) -> dict | None:
        table = self.query_one("#image-table", DataTable)
        if table.row_count == 0:
            return None
        selected_key = None
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            selected_key = row_key.value
        except Exception:
            try:
                if 0 <= table.cursor_row < len(table.ordered_rows):
                    selected_key = table.ordered_rows[table.cursor_row].key.value
            except Exception:
                pass

        if selected_key:
            for img in self._filtered:
                if f"{img['full_id']}:{img['repository']}:{img['tag']}" == selected_key:
                    return img
            for img in self._images:
                if f"{img['full_id']}:{img['repository']}:{img['tag']}" == selected_key:
                    return img

        cursor_row = table.cursor_row
        if cursor_row < len(self._filtered):
            return self._filtered[cursor_row]
        return None

    # ── Quick Filter & Prune ──────────────────────────────────────────

    def action_toggle_filter_mode(self) -> None:
        """Cycle filter mode: all -> dangling -> unused -> all."""
        modes = ["all", "dangling", "unused"]
        curr_idx = modes.index(self._filter_mode) if self._filter_mode in modes else 0
        self._filter_mode = modes[(curr_idx + 1) % len(modes)]
        self._apply_filters()

        labels = {
            "all": f"Showing all images ({len(self._filtered)})",
            "dangling": f"Filtered: Dangling (<none>) ({len(self._filtered)})",
            "unused": f"Filtered: Unused (no container) ({len(self._filtered)})",
        }
        self.notify(labels[self._filter_mode], severity="information")

    async def action_prune_dangling_images(self) -> None:
        """Prune all dangling (<none>) images."""
        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                self.app.call_later(self._do_prune_dangling)

        self.app.push_screen(
            ConfirmDialog(
                title="Prune Dangling Images",
                message="Are you sure you want to prune all untagged / dangling (<none>) images?",
                danger=True,
            ),
            on_confirm,
        )

    async def _do_prune_dangling(self) -> None:
        try:
            res = await self._docker.prune_images(dangling_only=True)
            deleted = res.get("ImagesDeleted") or []
            reclaimed = DockerClient.format_bytes(res.get("SpaceReclaimed", 0))
            self.notify(f"Pruned {len(deleted)} dangling images ({reclaimed} reclaimed)", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    # ── Search ────────────────────────────────────────────────────────

    def action_search(self) -> None:
        self.query_one("#image-search", SearchBar).show()

    def on_search_bar_changed(self, event: SearchBar.Changed) -> None:
        self._search_query = event.query
        self._apply_filters()

    def action_exit_search(self) -> None:
        """Exit search and restore list with Escape."""
        search_bar = self.query_one("#image-search", SearchBar)
        if search_bar.visible_search or self._search_query:
            self._search_query = ""
            search_bar.hide()
            self._apply_filters()
            self.query_one("#image-table", DataTable).focus()

    def on_search_bar_submitted(self, event: SearchBar.Submitted) -> None:
        """When pressing Enter in search bar, navigate into the results table."""
        table = self.query_one("#image-table", DataTable)
        table.focus()
        if table.row_count > 0:
            table.cursor_coordinate = (0, 0)

    def on_search_bar_dismissed(self, event: SearchBar.Dismissed) -> None:
        self._search_query = ""
        self._apply_filters()
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

    async def action_image_layers(self) -> None:
        image = self._get_selected_image()
        if not image:
            return
        try:
            history = await self._docker.image_history(image["full_id"])
            image_name = f"{image['repository']}:{image['tag']}"
            self.app.push_screen(
                ImageLayersDialog(
                    image_name=image_name,
                    raw_layers=history,
                )
            )
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_image_history(self) -> None:
        """Alias for action_image_layers."""
        await self.action_image_layers()

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
