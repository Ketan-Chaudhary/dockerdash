"""Containers management tab — core view of DockDash."""

from __future__ import annotations

import os
import subprocess
import sys

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Static

from dockdash.docker_client import DockerClient, DockerClientError
from dockdash.modals.confirm_dialog import ConfirmDialog
from dockdash.modals.input_dialog import InputDialog
from dockdash.modals.inspect_dialog import InspectDialog
from dockdash.widgets.container_detail import ContainerDetail
from dockdash.widgets.log_viewer import LogViewerScreen
from dockdash.widgets.search_bar import SearchBar
from dockdash.widgets.stats_display import StatsDisplay


class ContainersTab(Vertical):
    """Container management tab with table, detail panel, and actions."""

    BINDINGS = [
        Binding("s", "start_container", "Start", show=True),
        Binding("S", "stop_container", "Stop", show=True),
        Binding("R", "restart_container", "Restart", show=True),
        Binding("d", "delete_container", "Delete", show=True),
        Binding("l", "view_logs", "Logs", show=True),
        Binding("i", "inspect_container", "Inspect", show=True),
        Binding("t", "attach_terminal", "Terminal", show=True),
        Binding("p", "pause_container", "Pause", show=True),
        Binding("n", "rename_container", "Rename", show=True),
        Binding("a", "view_stats", "Stats", show=True),
        Binding("escape", "close_side_panel", "Close Panel", show=False),
        Binding("slash", "search", "Search", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._docker = DockerClient()
        self._containers: list[dict] = []
        self._filtered: list[dict] = []

    def compose(self) -> ComposeResult:
        yield SearchBar(id="container-search")
        yield Static(
            "[#79c0ff bold]CONTAINERS[/]  [#484f58]s[/]=start  "
            "[#484f58]S[/]=stop  [#484f58]R[/]=restart  "
            "[#484f58]d[/]=delete  [#484f58]l[/]=logs  "
            "[#484f58]i[/]=inspect  [#484f58]t[/]=terminal  "
            "[#484f58]a[/]=stats  [#484f58]n[/]=rename  "
            "[#484f58]/[/]=search",
            classes="actions-bar",
        )
        with Horizontal(id="container-layout"):
            with Vertical(id="container-main"):
                yield DataTable(id="container-table", cursor_type="row")
            with Vertical(id="container-side", classes="panel") as side:
                side.styles.display = "none"
                side.styles.width = "45%"
                yield ContainerDetail(id="container-detail")
                yield StatsDisplay(id="container-stats")

    def on_mount(self) -> None:
        table = self.query_one("#container-table", DataTable)
        table.add_columns(
            "STATUS", "CONTAINER", "IMAGE", "STATE", "PORTS", "ID"
        )
        # Hide optional panels
        self.query_one("#container-stats", StatsDisplay).styles.display = "none"
        self.query_one("#container-detail", ContainerDetail).styles.display = "none"

    async def refresh_data(self) -> None:
        """Refresh the container list from Docker."""
        try:
            self._containers = await self._docker.list_containers(all=True)
            self._filtered = list(self._containers)
            self._update_table()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    def _update_table(self) -> None:
        table = self.query_one("#container-table", DataTable)
        table.clear()

        for c in self._filtered:
            status_text, status_class = DockerClient.format_status(c["status"])
            # Use Rich markup for status coloring
            status_colors = {
                "status-running": "#3fb950",
                "status-exited": "#f85149",
                "status-paused": "#d29922",
                "status-created": "#58a6ff",
                "status-restarting": "#db6d28",
                "status-removing": "#484f58",
                "status-dead": "#f85149",
                "status-unknown": "#8b949e",
            }
            color = status_colors.get(status_class, "#8b949e")

            table.add_row(
                f"[{color} bold]{status_text}[/]",
                c["name"],
                c["image"],
                c["state"],
                c["ports"],
                c["id"],
                key=c["full_id"],
            )

    def _get_selected_container(self) -> dict | None:
        """Get the currently selected container dict."""
        table = self.query_one("#container-table", DataTable)
        if table.row_count == 0:
            return None
        try:
            row_key = table.get_row_at(table.cursor_row)
        except Exception:
            return None

        cursor_row = table.cursor_row
        if cursor_row < len(self._filtered):
            return self._filtered[cursor_row]
        return None

    def _get_selected_id(self) -> str | None:
        """Get the full ID of the selected container."""
        container = self._get_selected_container()
        return container["full_id"] if container else None

    # ── Close side panel ──────────────────────────────────────────────

    def action_close_side_panel(self) -> None:
        """Close the detail/stats side panel with Escape."""
        side = self.query_one("#container-side")
        if side.styles.display != "none":
            side.styles.display = "none"
            self.query_one("#container-detail", ContainerDetail).styles.display = "none"
            self.query_one("#container-stats", StatsDisplay).styles.display = "none"
            self.query_one("#container-table", DataTable).focus()

    # ── Search ────────────────────────────────────────────────────────

    def action_search(self) -> None:
        self.query_one("#container-search", SearchBar).show()

    def on_search_bar_changed(self, event: SearchBar.Changed) -> None:
        query = event.query.lower().strip()
        if not query:
            self._filtered = list(self._containers)
        else:
            self._filtered = [
                c for c in self._containers
                if query in c["name"].lower()
                or query in c["image"].lower()
                or query in c["id"].lower()
                or query in c["status"].lower()
            ]
        self._update_table()

    def on_search_bar_dismissed(self, event: SearchBar.Dismissed) -> None:
        table = self.query_one("#container-table", DataTable)
        table.focus()

    # ── Navigation ────────────────────────────────────────────────────

    def action_cursor_down(self) -> None:
        table = self.query_one("#container-table", DataTable)
        table.action_cursor_down()

    def action_cursor_up(self) -> None:
        table = self.query_one("#container-table", DataTable)
        table.action_cursor_up()

    # ── Container Actions ─────────────────────────────────────────────

    async def action_start_container(self) -> None:
        cid = self._get_selected_id()
        if not cid:
            return
        try:
            await self._docker.start_container(cid)
            self.notify("Container started", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_stop_container(self) -> None:
        cid = self._get_selected_id()
        if not cid:
            return
        try:
            await self._docker.stop_container(cid)
            self.notify("Container stopped", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_restart_container(self) -> None:
        cid = self._get_selected_id()
        if not cid:
            return
        try:
            await self._docker.restart_container(cid)
            self.notify("Container restarted", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_pause_container(self) -> None:
        cid = self._get_selected_id()
        if not cid:
            return
        container = self._get_selected_container()
        if not container:
            return
        try:
            if container["status"] == "paused":
                await self._docker.unpause_container(cid)
                self.notify("Container unpaused", severity="information")
            else:
                await self._docker.pause_container(cid)
                self.notify("Container paused", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_delete_container(self) -> None:
        container = self._get_selected_container()
        if not container:
            return

        def on_confirm(result: bool) -> None:
            if result:
                self.app.call_later(self._do_delete, container["full_id"])

        self.app.push_screen(
            ConfirmDialog(
                title="⟨ DELETE CONTAINER ⟩",
                message=f"Delete container '{container['name']}'?\nThis will force-remove the container.",
                confirm_label="Delete",
                danger=True,
            ),
            on_confirm,
        )

    async def _do_delete(self, cid: str) -> None:
        try:
            await self._docker.remove_container(cid, force=True)
            self.notify("Container deleted", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_rename_container(self) -> None:
        container = self._get_selected_container()
        if not container:
            return

        def on_name(new_name: str | None) -> None:
            if new_name:
                self.app.call_later(
                    self._do_rename, container["full_id"], new_name
                )

        self.app.push_screen(
            InputDialog(
                title="⟨ RENAME CONTAINER ⟩",
                label=f"New name for '{container['name']}':",
                default_value=container["name"],
                placeholder="new-container-name",
            ),
            on_name,
        )

    async def _do_rename(self, cid: str, new_name: str) -> None:
        try:
            await self._docker.rename_container(cid, new_name)
            self.notify(f"Renamed to '{new_name}'", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    # ── View Actions ──────────────────────────────────────────────────

    async def action_view_logs(self) -> None:
        """Open logs in a full-screen modal."""
        container = self._get_selected_container()
        if not container:
            return
        try:
            logs = await self._docker.container_logs(
                container["full_id"], tail=500, timestamps=True
            )
            self.app.push_screen(
                LogViewerScreen(
                    title=f"LOGS — {container['name']}",
                    content=logs,
                )
            )
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_inspect_container(self) -> None:
        cid = self._get_selected_id()
        if not cid:
            return
        try:
            data = await self._docker.inspect_container(cid)
            name = data.get("Name", "").lstrip("/")
            self.app.push_screen(InspectDialog(title=name, data=data))
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_view_stats(self) -> None:
        container = self._get_selected_container()
        if not container:
            return
        if container["status"] != "running":
            self.notify("Container is not running", severity="warning")
            return
        try:
            stats = await self._docker.container_stats(container["full_id"])
            side = self.query_one("#container-side")
            side.styles.display = "block"

            self.query_one("#container-detail", ContainerDetail).styles.display = "none"

            stats_w = self.query_one("#container-stats", StatsDisplay)
            stats_w.styles.display = "block"
            stats_w.update_stats(stats)
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_attach_terminal(self) -> None:
        """Suspend the TUI and exec into the container with an interactive shell."""
        container = self._get_selected_container()
        if not container:
            return
        if container["status"] != "running":
            self.notify("Container must be running to attach", severity="warning")
            return

        cid = container["full_id"]
        name = container["name"]

        # Suspend the app, run docker exec, then resume
        driver = self.app._driver  # type: ignore
        if driver is not None:
            driver.stop_application_mode()

        try:
            print(f"\n── Attaching to container '{name}' ──")
            print("── Type 'exit' to return to DockDash ──\n")
            subprocess.run(
                ["docker", "exec", "-it", cid, "/bin/sh", "-c",
                 "if command -v bash >/dev/null 2>&1; then exec bash; else exec sh; fi"],
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
        except FileNotFoundError:
            print("Error: 'docker' command not found in PATH")
        except Exception as e:
            print(f"Error: {e}")

        if driver is not None:
            driver.start_application_mode()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Show detail panel when a row is selected (Enter)."""
        idx = event.cursor_row
        if idx < len(self._filtered):
            container = self._filtered[idx]
            self._show_detail(container)

    async def _show_detail(self, container: dict) -> None:
        """Show the detail panel for a container."""
        try:
            attrs = await self._docker.inspect_container(container["full_id"])
            side = self.query_one("#container-side")
            side.styles.display = "block"

            self.query_one("#container-stats", StatsDisplay).styles.display = "none"

            detail = self.query_one("#container-detail", ContainerDetail)
            detail.styles.display = "block"
            detail.update_detail(attrs)
        except DockerClientError as e:
            self.notify(str(e), severity="error")
