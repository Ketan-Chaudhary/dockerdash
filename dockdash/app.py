"""DockDash — Docker Dashboard for the Terminal.

Main application entry point. Assembles all tabs and manages
the global lifecycle.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from textual import work
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Center, Vertical

if TYPE_CHECKING:
    from textual.screen import Screen
from textual.widgets import (
    Footer,
    Header,
    Static,
    TabbedContent,
    TabPane,
)

from dockdash.docker_client import DockerClient
from dockdash.modals.exit_dialog import ExitDialog
from dockdash.modals.help_dialog import HelpDialog
from dockdash.modals.theme_dialog import ThemeDialog
from dockdash.screens.compose import ComposeTab
from dockdash.screens.containers import ContainersTab
from dockdash.screens.images import ImagesTab
from dockdash.screens.networks import NetworksTab
from dockdash.screens.system import SystemTab
from dockdash.screens.volumes import VolumesTab
from dockdash.themes import get_saved_theme, register_themes

if getattr(sys, "frozen", False):
    # PyInstaller bundle path
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    CSS_PATH = base_dir / "dockdash" / "styles.tcss"
    if not CSS_PATH.exists():
        CSS_PATH = base_dir / "styles.tcss"
else:
    CSS_PATH = Path(__file__).parent / "styles.tcss"


class DockerDashApp(App):
    """The main DockDash application."""

    TITLE = "DockDash"
    SUB_TITLE = "Docker Dashboard"
    CSS_PATH = CSS_PATH

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True, priority=True),
        Binding("t", "open_themes", "Theme", show=True),
        Binding("T", "open_themes", "Theme", show=False),
        Binding("question_mark", "show_help", "Help", show=True, key_display="?"),
        Binding("f1", "show_help", "Help", show=False),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("f5", "refresh", "Refresh", show=False),
        Binding("1", "tab_1", "Containers (1)", show=False),
        Binding("2", "tab_2", "Images (2)", show=False),
        Binding("3", "tab_3", "Volumes (3)", show=False),
        Binding("4", "tab_4", "Networks (4)", show=False),
        Binding("5", "tab_5", "Compose (5)", show=False),
        Binding("6", "tab_6", "System (6)", show=False),
        Binding("slash", "search", "Search", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        register_themes(self)
        try:
            self.theme = get_saved_theme()
        except Exception:
            pass
        self._docker = DockerClient()
        # Attempt connection immediately so compose() can branch
        self._connected = self._docker.connect()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        if not self._connected:
            # Show connection error
            with Center(), Vertical(classes="error-panel"):
                yield Static(
                    "⟨ CONNECTION ERROR ⟩",
                    classes="error-title",
                )
                yield Static(
                    "\nCannot connect to Docker daemon.\n\n"
                    "Make sure Docker is installed and running:\n"
                    "  [#38bdf8 bold]sudo systemctl start docker[/]\n"
                    "  [#38bdf8 bold]sudo usermod -aG docker $USER[/]\n\n"
                    "Then restart DockDash.",
                    classes="error-message",
                )
        else:
            with TabbedContent(
                "Containers (1)",
                "Images (2)",
                "Volumes (3)",
                "Networks (4)",
                "Compose (5)",
                "System (6)",
                id="main-tabs",
            ):
                with TabPane("Containers (1)", id="tab-containers"):
                    yield ContainersTab(id="containers-tab")
                with TabPane("Images (2)", id="tab-images"):
                    yield ImagesTab(id="images-tab")
                with TabPane("Volumes (3)", id="tab-volumes"):
                    yield VolumesTab(id="volumes-tab")
                with TabPane("Networks (4)", id="tab-networks"):
                    yield NetworksTab(id="networks-tab")
                with TabPane("Compose (5)", id="tab-compose"):
                    yield ComposeTab(id="compose-tab")
                with TabPane("System (6)", id="tab-system"):
                    yield SystemTab(id="system-tab")

        yield Footer()

    def on_mount(self) -> None:
        """Load data for the initially visible tab."""
        if not self._connected:
            self.notify(
                "Cannot connect to Docker daemon", severity="error"
            )
            return
        self.call_later(self._initial_load)

    async def _initial_load(self) -> None:
        """Load data for the initially visible tab."""
        if not self._connected:
            return
        try:
            containers = self.query_one("#containers-tab", ContainersTab)
            await containers.refresh_data()
        except Exception:
            pass

    # ── Tab switching ─────────────────────────────────────────────────

    def action_tab_1(self) -> None:
        if len(self.screen_stack) > 1:
            return
        self._switch_tab("tab-containers")

    def action_tab_2(self) -> None:
        if len(self.screen_stack) > 1:
            return
        self._switch_tab("tab-images")

    def action_tab_3(self) -> None:
        if len(self.screen_stack) > 1:
            return
        self._switch_tab("tab-volumes")

    def action_tab_4(self) -> None:
        if len(self.screen_stack) > 1:
            return
        self._switch_tab("tab-networks")

    def action_tab_5(self) -> None:
        if len(self.screen_stack) > 1:
            return
        self._switch_tab("tab-compose")

    def action_tab_6(self) -> None:
        if len(self.screen_stack) > 1:
            return
        self._switch_tab("tab-system")

    def on_key(self, event) -> None:
        """Global key interceptor for tab switching and tab-bar navigation."""
        # Don't switch background tabs when a modal dialog is displayed
        if len(self.screen_stack) > 1:
            return

        focused = self.focused

        # When focused on the tab bar, pressing down arrow enters the active tab content
        if event.key == "down" and focused is not None:
            class_name = type(focused).__name__
            if class_name in ("ContentTabs", "Tab", "Tabs", "Underline"):
                self._focus_active_tab_content()
                event.prevent_default()
                event.stop()
                return

        if event.key in ("1", "2", "3", "4", "5", "6"):
            # Don't intercept if user is typing in a text Input box
            if focused and focused.__class__.__name__ == "Input":
                return
            key_map = {
                "1": "tab-containers",
                "2": "tab-images",
                "3": "tab-volumes",
                "4": "tab-networks",
                "5": "tab-compose",
                "6": "tab-system",
            }
            tab_id = key_map.get(event.key)
            if tab_id:
                self._switch_tab(tab_id)

    def _focus_active_tab_content(self) -> None:
        """Move focus to the first focusable widget inside the active tab pane."""
        try:
            from textual.widgets import DataTable
            tabs = self.query_one("#main-tabs", TabbedContent)
            active_pane = tabs.query_one(f"#{tabs.active}")

            # Prefer focusing the DataTable (lists) first
            data_tables = active_pane.query(DataTable)
            if data_tables:
                data_tables.first().focus()
                return

            # Fallback to the first focusable widget
            for child in active_pane.walk_children():
                if child.can_focus:
                    # Skip Input widgets if they are part of a hidden SearchBar
                    if child.__class__.__name__ == "Input" and child.parent and child.parent.styles.display == "none":
                        continue
                    child.focus()
                    return
        except Exception:
            pass

    def _switch_tab(self, tab_id: str) -> None:
        try:
            tabs = self.query_one("#main-tabs", TabbedContent)
            tabs.active = tab_id
            self.call_later(self._focus_active_tab_content)
        except Exception:
            pass

    def action_search(self) -> None:
        """Forward search action to the active tab's SearchBar."""
        from dockdash.widgets.search_bar import SearchBar
        try:
            tabs = self.query_one("#main-tabs", TabbedContent)
            active_pane = tabs.query_one(f"#{tabs.active}")
            search_bars = active_pane.query(SearchBar)
            if search_bars:
                search_bars.first().show()
        except Exception:
            pass

    def on_tabbed_content_tab_activated(
        self, event: TabbedContent.TabActivated
    ) -> None:
        """Refresh data when a tab is activated."""
        self._refresh_active_tab()
        self.call_later(self._focus_active_tab_content)

    async def _do_refresh_active_tab(self) -> None:
        """Core logic to refresh whichever tab is currently active."""
        if not self._connected:
            return

        try:
            tabs = self.query_one("#main-tabs", TabbedContent)
            active = tabs.active
        except Exception:
            return

        tab_map = {
            "tab-containers": ("#containers-tab", ContainersTab),
            "tab-images": ("#images-tab", ImagesTab),
            "tab-volumes": ("#volumes-tab", VolumesTab),
            "tab-networks": ("#networks-tab", NetworksTab),
            "tab-compose": ("#compose-tab", ComposeTab),
            "tab-system": ("#system-tab", SystemTab),
        }

        entry = tab_map.get(active)
        if entry:
            selector, cls = entry
            try:
                widget = self.query_one(selector, cls)
                await widget.refresh_data()
            except Exception as e:
                self.notify(f"Refresh error: {e}", severity="error")

    @work(exclusive=True)
    async def _refresh_active_tab(self) -> None:
        """Refresh whichever tab is currently active with transition delay."""
        import asyncio
        # Wait for the tab transition animation to finish to avoid lag/stutter
        await asyncio.sleep(0.3)
        await self._do_refresh_active_tab()

    # ── Global actions ────────────────────────────────────────────────

    @work(exclusive=True)
    async def action_refresh(self) -> None:
        """Refresh the current tab's data immediately."""
        await self._do_refresh_active_tab()
        self.notify("Refreshed", severity="information")

    def action_show_help(self) -> None:
        """Show the help dialog."""
        self.push_screen(HelpDialog())

    def action_quit(self) -> None:
        """Prompt user with Exit Dialog (Quit / Theme Settings / Cancel)."""

        def on_exit_choice(choice: str | None) -> None:
            if choice == "quit":
                self.exit()
            elif choice == "settings":
                self.action_open_themes()

        self.push_screen(ExitDialog(), on_exit_choice)

    def action_open_themes(self) -> None:
        """Open the color templates and theme selector modal."""
        self.push_screen(ThemeDialog())

    def action_change_theme(self) -> None:
        """Route command palette theme change to DockDash theme selector."""
        self.action_open_themes()

    def search_themes(self) -> None:
        """Route command palette search_themes to DockDash theme selector."""
        self.action_open_themes()

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        """Provide custom system commands for the command palette.

        Allows quitting immediately without an exit dialog when selected from the command palette.
        """
        for cmd in super().get_system_commands(screen):
            if cmd.title == "Quit":
                yield SystemCommand(
                    "Quit",
                    "Quit the application immediately",
                    self.exit,
                )
            elif cmd.title == "Theme":
                yield SystemCommand(
                    "Theme",
                    "Change the current color template & theme",
                    self.action_open_themes,
                )
            else:
                yield cmd


def main() -> None:
    """Entry point for the dockdash CLI."""
    app = DockerDashApp()
    app.run()


if __name__ == "__main__":
    main()
