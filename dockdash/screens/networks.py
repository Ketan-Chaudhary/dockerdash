"""Networks management tab."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Static

from dockdash.docker_client import DockerClient, DockerClientError
from dockdash.modals.confirm_dialog import ConfirmDialog
from dockdash.modals.input_dialog import MultiInputDialog
from dockdash.modals.inspect_dialog import InspectDialog
from dockdash.widgets.search_bar import SearchBar


class NetworksTab(Vertical):
    """Network management tab."""

    BINDINGS = [
        Binding("c", "create_network", "Create", show=True),
        Binding("d", "delete_network", "Delete", show=True),
        Binding("i", "inspect_network", "Inspect", show=True),
        Binding("slash", "search", "Search", show=False),
        Binding("escape", "exit_search", "Exit Search", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._docker = DockerClient()
        self._networks: list[dict] = []
        self._filtered: list[dict] = []

    def compose(self) -> ComposeResult:
        yield SearchBar(id="network-search")
        yield Static(
            "[#79c0ff bold]NETWORKS[/]  [#484f58]c[/]=create  "
            "[#484f58]d[/]=delete  [#484f58]i[/]=inspect  "
            "[#484f58]/[/]=search",
            classes="actions-bar",
        )
        yield DataTable(id="network-table", cursor_type="row")

    def on_mount(self) -> None:
        table = self.query_one("#network-table", DataTable)
        table.add_columns("NAME", "ID", "DRIVER", "SCOPE", "CONTAINERS")

    async def refresh_data(self) -> None:
        try:
            self._networks = await self._docker.list_networks()
            self._filtered = list(self._networks)
            self._update_table()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    def _update_table(self) -> None:
        with self.app.batch_update():
            table = self.query_one("#network-table", DataTable)
            current_keys = {row_key.value for row_key in table.rows.keys()}
            new_keys = {n["full_id"] for n in self._filtered}

            for key in current_keys - new_keys:
                table.remove_row(key)

            columns = list(table.columns.keys())

            for n in self._filtered:
                row_data = (
                    n["name"],
                    n["id"],
                    n["driver"],
                    n["scope"],
                    str(n.get("containers", 0)),
                )
                key = n["full_id"]

                if key in current_keys:
                    for col_key, cell_val in zip(columns, row_data):
                        table.update_cell(key, col_key, cell_val, update_width=True)
                else:
                    table.add_row(*row_data, key=key)

    def _get_selected_network(self) -> dict | None:
        table = self.query_one("#network-table", DataTable)
        if table.row_count == 0:
            return None
        selected_id = None
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            selected_id = row_key.value
        except Exception:
            try:
                if 0 <= table.cursor_row < len(table.ordered_rows):
                    selected_id = table.ordered_rows[table.cursor_row].key.value
            except Exception:
                pass

        if selected_id:
            for n in self._filtered:
                if n["full_id"] == selected_id:
                    return n
            for n in self._networks:
                if n["full_id"] == selected_id:
                    return n

        cursor_row = table.cursor_row
        if cursor_row < len(self._filtered):
            return self._filtered[cursor_row]
        return None

    # ── Search ────────────────────────────────────────────────────────

    def action_search(self) -> None:
        self.query_one("#network-search", SearchBar).show()

    def on_search_bar_changed(self, event: SearchBar.Changed) -> None:
        query = event.query.lower().strip()
        if not query:
            self._filtered = list(self._networks)
        else:
            self._filtered = [
                n for n in self._networks
                if query in n["name"].lower()
                or query in n.get("driver", "").lower()
                or query in n["id"].lower()
            ]
        self._update_table()

    def action_exit_search(self) -> None:
        """Exit search and restore full list with Escape."""
        search_bar = self.query_one("#network-search", SearchBar)
        if search_bar.visible_search or len(self._filtered) < len(self._networks):
            search_bar.hide()
            self.query_one("#network-table", DataTable).focus()

    def on_search_bar_submitted(self, event: SearchBar.Submitted) -> None:
        """When pressing Enter in search bar, navigate into the results table."""
        table = self.query_one("#network-table", DataTable)
        table.focus()
        if table.row_count > 0:
            table.cursor_coordinate = (0, 0)

    def on_search_bar_dismissed(self, event: SearchBar.Dismissed) -> None:
        self._filtered = list(self._networks)
        self._update_table()
        self.query_one("#network-table", DataTable).focus()

    # ── Navigation ────────────────────────────────────────────────────

    def action_cursor_down(self) -> None:
        self.query_one("#network-table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#network-table", DataTable).action_cursor_up()

    # ── Network Actions ───────────────────────────────────────────────

    async def action_create_network(self) -> None:
        def on_input(result: dict[str, str] | None) -> None:
            if result:
                name = result.get("name", "")
                driver = result.get("driver", "bridge") or "bridge"
                if name:
                    self.app.call_later(self._do_create, name, driver)

        self.app.push_screen(
            MultiInputDialog(
                title="⟨ CREATE NETWORK ⟩",
                fields=[
                    {
                        "id": "name",
                        "label": "Network name:",
                        "placeholder": "e.g. my-app-network",
                    },
                    {
                        "id": "driver",
                        "label": "Driver:",
                        "placeholder": "bridge (default)",
                        "default": "bridge",
                    },
                ],
            ),
            on_input,
        )

    async def _do_create(self, name: str, driver: str) -> None:
        try:
            await self._docker.create_network(name=name, driver=driver)
            self.notify(f"Network '{name}' created", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_delete_network(self) -> None:
        net = self._get_selected_network()
        if not net:
            return

        # Protect built-in networks
        if net["name"] in ("bridge", "host", "none"):
            self.notify("Cannot delete built-in network", severity="warning")
            return

        def on_confirm(result: bool) -> None:
            if result:
                self.app.call_later(self._do_delete, net["full_id"])

        self.app.push_screen(
            ConfirmDialog(
                title="⟨ DELETE NETWORK ⟩",
                message=f"Delete network '{net['name']}'?",
                confirm_label="Delete",
                danger=True,
            ),
            on_confirm,
        )

    async def _do_delete(self, network_id: str) -> None:
        try:
            await self._docker.remove_network(network_id)
            self.notify("Network deleted", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_inspect_network(self) -> None:
        net = self._get_selected_network()
        if not net:
            return
        try:
            data = await self._docker.inspect_network(net["full_id"])
            self.app.push_screen(
                InspectDialog(title=net["name"], data=data)
            )
        except DockerClientError as e:
            self.notify(str(e), severity="error")
