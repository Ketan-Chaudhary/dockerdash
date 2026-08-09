"""Volumes management tab."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Static

from dockdash.docker_client import DockerClient, DockerClientError
from dockdash.modals.confirm_dialog import ConfirmDialog
from dockdash.modals.input_dialog import InputDialog, MultiInputDialog
from dockdash.modals.inspect_dialog import InspectDialog
from dockdash.widgets.search_bar import SearchBar


class VolumesTab(Vertical):
    """Volume management tab."""

    BINDINGS = [
        Binding("c", "create_volume", "Create", show=True),
        Binding("d", "delete_volume", "Delete", show=True),
        Binding("i", "inspect_volume", "Inspect", show=True),
        Binding("slash", "search", "Search", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._docker = DockerClient()
        self._volumes: list[dict] = []
        self._filtered: list[dict] = []

    def compose(self) -> ComposeResult:
        yield SearchBar(id="volume-search")
        yield Static(
            "[#79c0ff bold]VOLUMES[/]  [#484f58]c[/]=create  "
            "[#484f58]d[/]=delete  [#484f58]i[/]=inspect  "
            "[#484f58]/[/]=search",
            classes="actions-bar",
        )
        yield DataTable(id="volume-table", cursor_type="row")

    def on_mount(self) -> None:
        table = self.query_one("#volume-table", DataTable)
        table.add_columns("NAME", "DRIVER", "MOUNTPOINT", "CREATED")

    async def refresh_data(self) -> None:
        try:
            self._volumes = await self._docker.list_volumes()
            self._filtered = list(self._volumes)
            self._update_table()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    def _update_table(self) -> None:
        table = self.query_one("#volume-table", DataTable)
        table.clear()
        for v in self._filtered:
            created = v.get("created", "")[:19]
            mountpoint = v.get("mountpoint", "")
            # Truncate long mountpoints
            if len(mountpoint) > 50:
                mountpoint = "..." + mountpoint[-47:]
            table.add_row(
                v["name"],
                v["driver"],
                mountpoint,
                created,
                key=v["name"],
            )

    def _get_selected_volume(self) -> dict | None:
        table = self.query_one("#volume-table", DataTable)
        if table.row_count == 0:
            return None
        cursor_row = table.cursor_row
        if cursor_row < len(self._filtered):
            return self._filtered[cursor_row]
        return None

    # ── Search ────────────────────────────────────────────────────────

    def action_search(self) -> None:
        self.query_one("#volume-search", SearchBar).show()

    def on_search_bar_changed(self, event: SearchBar.Changed) -> None:
        query = event.query.lower().strip()
        if not query:
            self._filtered = list(self._volumes)
        else:
            self._filtered = [
                v for v in self._volumes
                if query in v["name"].lower()
                or query in v.get("driver", "").lower()
            ]
        self._update_table()

    def on_search_bar_dismissed(self, event: SearchBar.Dismissed) -> None:
        self.query_one("#volume-table", DataTable).focus()

    # ── Navigation ────────────────────────────────────────────────────

    def action_cursor_down(self) -> None:
        self.query_one("#volume-table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#volume-table", DataTable).action_cursor_up()

    # ── Volume Actions ────────────────────────────────────────────────

    async def action_create_volume(self) -> None:
        def on_input(result: dict[str, str] | None) -> None:
            if result:
                name = result.get("name", "")
                driver = result.get("driver", "local") or "local"
                if name:
                    self.app.call_later(self._do_create, name, driver)

        self.app.push_screen(
            MultiInputDialog(
                title="⟨ CREATE VOLUME ⟩",
                fields=[
                    {
                        "id": "name",
                        "label": "Volume name:",
                        "placeholder": "e.g. my-data-volume",
                    },
                    {
                        "id": "driver",
                        "label": "Driver:",
                        "placeholder": "local (default)",
                        "default": "local",
                    },
                ],
            ),
            on_input,
        )

    async def _do_create(self, name: str, driver: str) -> None:
        try:
            await self._docker.create_volume(name=name, driver=driver)
            self.notify(f"Volume '{name}' created", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_delete_volume(self) -> None:
        vol = self._get_selected_volume()
        if not vol:
            return

        def on_confirm(result: bool) -> None:
            if result:
                self.app.call_later(self._do_delete, vol["name"])

        self.app.push_screen(
            ConfirmDialog(
                title="⟨ DELETE VOLUME ⟩",
                message=f"Delete volume '{vol['name']}'?",
                confirm_label="Delete",
                danger=True,
            ),
            on_confirm,
        )

    async def _do_delete(self, name: str) -> None:
        try:
            await self._docker.remove_volume(name, force=True)
            self.notify("Volume deleted", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_inspect_volume(self) -> None:
        vol = self._get_selected_volume()
        if not vol:
            return
        try:
            data = await self._docker.inspect_volume(vol["name"])
            self.app.push_screen(
                InspectDialog(title=vol["name"], data=data)
            )
        except DockerClientError as e:
            self.notify(str(e), severity="error")
