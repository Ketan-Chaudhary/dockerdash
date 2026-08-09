"""Docker Compose stack management tab."""

from __future__ import annotations

import os

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import DataTable, Static

from dockdash.docker_client import DockerClient, DockerClientError
from dockdash.modals.confirm_dialog import ConfirmDialog
from dockdash.modals.dockerfile_editor import DockerfileEditorDialog
from dockdash.widgets.log_viewer import LogViewerScreen
from dockdash.widgets.search_bar import SearchBar


class ComposeTab(Vertical):
    """Docker Compose project & stack management tab."""

    BINDINGS = [
        Binding("u", "compose_up", "Up", show=True),
        Binding("d", "compose_down", "Down", show=True),
        Binding("s", "compose_start", "Start", show=True),
        Binding("S", "compose_stop", "Stop", show=True),
        Binding("R", "compose_restart", "Restart", show=True),
        Binding("l", "compose_logs", "Logs", show=True),
        Binding("e", "edit_compose_file", "Edit File", show=True),
        Binding("p", "compose_pull", "Pull", show=True),
        Binding("slash", "search", "Search", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._docker = DockerClient()
        self._projects: list[dict] = []
        self._filtered: list[dict] = []

    def compose(self) -> ComposeResult:
        yield SearchBar(id="compose-search")
        yield Static(
            "[#79c0ff bold]COMPOSE STACKS[/]  [#484f58]u[/]=up  "
            "[#484f58]d[/]=down  [#484f58]s[/]=start  "
            "[#484f58]S[/]=stop  [#484f58]R[/]=restart  "
            "[#484f58]l[/]=logs  [#484f58]e[/]=edit file  "
            "[#484f58]p[/]=pull  [#484f58]/[/]=search",
            classes="actions-bar",
        )
        with Horizontal(id="compose-layout"):
            with Vertical(id="compose-main"):
                yield DataTable(id="compose-table", cursor_type="row")
            with Vertical(id="compose-side", classes="panel") as side:
                side.styles.display = "none"
                side.styles.width = "40%"
                yield Static("⟨ STACK SERVICES ⟩", classes="panel-title")
                with VerticalScroll():
                    yield Static("", id="compose-services-detail")

    def on_mount(self) -> None:
        table = self.query_one("#compose-table", DataTable)
        table.add_columns("STATUS", "STACK NAME", "SERVICES", "CONFIG FILE", "WORKING DIR")

    async def refresh_data(self) -> None:
        try:
            self._projects = await self._docker.list_compose_projects()
            self._filtered = list(self._projects)
            self._update_table()
            self._update_side_panel()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    def _update_table(self) -> None:
        table = self.query_one("#compose-table", DataTable)
        table.clear()

        for proj in self._filtered:
            status = proj.get("status", "stopped")
            if status == "running":
                status_markup = "[#3fb950 bold]▸ RUNNING[/]"
            elif status == "partial":
                status_markup = "[#d29922 bold]PARTIAL[/]"
            else:
                status_markup = "[#f85149]■ STOPPED[/]"

            services = proj.get("services", [])
            running_cnt = sum(1 for s in services if s["status"] == "running")
            svc_str = f"{running_cnt}/{len(services)}" if services else "0 (local file)"

            config_file = proj.get("config_file") or "—"
            work_dir = proj.get("working_dir") or "—"

            table.add_row(
                status_markup,
                proj["name"],
                svc_str,
                config_file,
                work_dir,
                key=proj["name"],
            )

    def _get_selected_project(self) -> dict | None:
        table = self.query_one("#compose-table", DataTable)
        if table.row_count == 0:
            return None
        cursor_row = table.cursor_row
        if cursor_row < len(self._filtered):
            return self._filtered[cursor_row]
        return None

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Toggle or update side panel showing stack services."""
        side = self.query_one("#compose-side")
        if side.styles.display == "none":
            side.styles.display = "block"
        self._update_side_panel()

    def _update_side_panel(self) -> None:
        side = self.query_one("#compose-side")
        if side.styles.display == "none":
            return
        proj = self._get_selected_project()
        if not proj:
            return

        detail = self.query_one("#compose-services-detail", Static)
        lines = [f"[#79c0ff bold]Stack:[/] [#f0f6fc]{proj['name']}[/]\n"]

        services = proj.get("services", [])
        if services:
            lines.append("[#3fb9a0 bold]━━ Services ━━[/]\n")
            for s in services:
                st_color = "#3fb950" if s["status"] == "running" else "#f85149"
                lines.append(
                    f"  [{st_color} bold]•[/] [#f0f6fc bold]{s['name']}[/]  "
                    f"[#8b949e]({s['container_name']})[/]"
                )
                lines.append(f"    [#8b949e]Image:[/] {s['image']}")
                lines.append(f"    [#8b949e]Status:[/] {s['status']}  [#8b949e]Ports:[/] {s['ports']}")
                lines.append("")
        else:
            lines.append("[#8b949e italic]No containers currently running for this stack.[/]\n")
            if proj.get("config_file"):
                lines.append(f"[#79c0ff]Press [#f0f6fc bold]u[/] to run [#f0f6fc bold]docker compose up -d[/][/]")

        detail.update("\n".join(lines))

    # ── Search ────────────────────────────────────────────────────────

    def action_search(self) -> None:
        self.query_one("#compose-search", SearchBar).show()

    def on_search_bar_changed(self, event: SearchBar.Changed) -> None:
        query = event.query.lower().strip()
        if not query:
            self._filtered = list(self._projects)
        else:
            self._filtered = [
                p for p in self._projects
                if query in p["name"].lower()
                or query in p.get("config_file", "").lower()
            ]
        self._update_table()

    def on_search_bar_dismissed(self, event: SearchBar.Dismissed) -> None:
        self.query_one("#compose-table", DataTable).focus()

    # ── Navigation ────────────────────────────────────────────────────

    def action_cursor_down(self) -> None:
        self.query_one("#compose-table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#compose-table", DataTable).action_cursor_up()

    # ── Compose Actions ───────────────────────────────────────────────

    async def action_compose_up(self) -> None:
        proj = self._get_selected_project()
        if not proj:
            return
        self.notify(f"Starting stack '{proj['name']}' (docker compose up -d)...", severity="information")
        try:
            code, out = await self._docker.run_compose_action(
                proj["name"], "up", proj.get("config_file", ""), proj.get("working_dir", "")
            )
            if code == 0:
                self.notify(f"Stack '{proj['name']}' started successfully", severity="information")
            else:
                self.notify(f"Compose up error: {out}", severity="error")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_compose_down(self) -> None:
        proj = self._get_selected_project()
        if not proj:
            return

        def on_confirm(result: bool) -> None:
            if result:
                self.app.call_later(self._do_compose_down, proj)

        self.app.push_screen(
            ConfirmDialog(
                title="⟨ COMPOSE DOWN ⟩",
                message=f"Stop and remove containers for stack '{proj['name']}'?",
                confirm_label="Compose Down",
                danger=True,
            ),
            on_confirm,
        )

    async def _do_compose_down(self, proj: dict) -> None:
        self.notify(f"Stopping stack '{proj['name']}' (docker compose down)...", severity="information")
        try:
            code, out = await self._docker.run_compose_action(
                proj["name"], "down", proj.get("config_file", ""), proj.get("working_dir", "")
            )
            if code == 0:
                self.notify(f"Stack '{proj['name']}' stopped and removed", severity="information")
            else:
                self.notify(f"Compose down error: {out}", severity="error")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_compose_start(self) -> None:
        proj = self._get_selected_project()
        if not proj:
            return
        try:
            code, out = await self._docker.run_compose_action(
                proj["name"], "start", proj.get("config_file", ""), proj.get("working_dir", "")
            )
            self.notify(f"Started stack '{proj['name']}'", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_compose_stop(self) -> None:
        proj = self._get_selected_project()
        if not proj:
            return
        try:
            code, out = await self._docker.run_compose_action(
                proj["name"], "stop", proj.get("config_file", ""), proj.get("working_dir", "")
            )
            self.notify(f"Stopped stack '{proj['name']}'", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_compose_restart(self) -> None:
        proj = self._get_selected_project()
        if not proj:
            return
        try:
            code, out = await self._docker.run_compose_action(
                proj["name"], "restart", proj.get("config_file", ""), proj.get("working_dir", "")
            )
            self.notify(f"Restarted stack '{proj['name']}'", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_compose_pull(self) -> None:
        proj = self._get_selected_project()
        if not proj:
            return
        self.notify(f"Pulling images for stack '{proj['name']}'...", severity="information")
        try:
            code, out = await self._docker.run_compose_action(
                proj["name"], "pull", proj.get("config_file", ""), proj.get("working_dir", "")
            )
            self.notify(f"Images pulled for stack '{proj['name']}'", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_compose_logs(self) -> None:
        proj = self._get_selected_project()
        if not proj:
            return
        try:
            logs = await self._docker.get_compose_logs(
                proj["name"], proj.get("config_file", ""), proj.get("working_dir", ""), tail=500
            )
            self.app.push_screen(
                LogViewerScreen(
                    title=f"COMPOSE LOGS — {proj['name']}",
                    content=logs,
                )
            )
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_edit_compose_file(self) -> None:
        proj = self._get_selected_project()
        config_path = proj.get("config_file") if proj else ""

        if not config_path or not os.path.isfile(config_path):
            config_path = os.path.join(os.getcwd(), "docker-compose.yml")

        def on_result(result: dict | None) -> None:
            if result and result.get("action") == "build":
                self.app.call_later(self.action_compose_up)

        self.app.push_screen(
            DockerfileEditorDialog(file_path=config_path),
            on_result,
        )
