"""DockDash — Docker Dashboard for the Terminal.

Main application entry point. Assembles all tabs and manages
the global lifecycle.
"""

from __future__ import annotations

import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical
from textual.widgets import (
    Footer,
    Header,
    Static,
    TabbedContent,
    TabPane,
)

from dockdash import __app_name__, __version__
from dockdash.docker_client import DockerClient
from dockdash.modals.help_dialog import HelpDialog
from dockdash.screens.containers import ContainersTab
from dockdash.screens.images import ImagesTab
from dockdash.screens.networks import NetworksTab
from dockdash.screens.system import SystemTab
from dockdash.screens.volumes import VolumesTab


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

    TITLE = f"{__app_name__} v{__version__}"
    SUB_TITLE = "Docker Dashboard"
    CSS_PATH = CSS_PATH

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True, priority=True),
        Binding("question_mark", "show_help", "Help", show=True, key_display="?"),
        Binding("f1", "show_help", "Help", show=False),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("f5", "refresh", "Refresh", show=False),
        Binding("1", "tab_1", "Containers", show=False, priority=True),
        Binding("2", "tab_2", "Images", show=False, priority=True),
        Binding("3", "tab_3", "Volumes", show=False, priority=True),
        Binding("4", "tab_4", "Networks", show=False, priority=True),
        Binding("5", "tab_5", "System", show=False, priority=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._docker = DockerClient()
        # Attempt connection immediately so compose() can branch
        self._connected = self._docker.connect()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        if not self._connected:
            # Show connection error
            with Center():
                with Vertical(classes="error-panel"):
                    yield Static(
                        "⟨ CONNECTION ERROR ⟩",
                        classes="error-title",
                    )
                    yield Static(
                        "\nCannot connect to Docker daemon.\n\n"
                        "Make sure Docker is installed and running:\n"
                        "  [#79c0ff]sudo systemctl start docker[/]\n"
                        "  [#79c0ff]sudo usermod -aG docker $USER[/]\n\n"
                        "Then restart DockDash.",
                        classes="error-message",
                    )
        else:
            with TabbedContent(
                "Containers",
                "Images",
                "Volumes",
                "Networks",
                "System",
                id="main-tabs",
            ):
                with TabPane("Containers", id="tab-containers"):
                    yield ContainersTab(id="containers-tab")
                with TabPane("Images", id="tab-images"):
                    yield ImagesTab(id="images-tab")
                with TabPane("Volumes", id="tab-volumes"):
                    yield VolumesTab(id="volumes-tab")
                with TabPane("Networks", id="tab-networks"):
                    yield NetworksTab(id="networks-tab")
                with TabPane("System", id="tab-system"):
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
        self._switch_tab("tab-containers")

    def action_tab_2(self) -> None:
        self._switch_tab("tab-images")

    def action_tab_3(self) -> None:
        self._switch_tab("tab-volumes")

    def action_tab_4(self) -> None:
        self._switch_tab("tab-networks")

    def action_tab_5(self) -> None:
        self._switch_tab("tab-system")

    def on_key(self, event) -> None:
        """Global key interceptor for tab switching."""
        if event.key in ("1", "2", "3", "4", "5"):
            # Don't intercept if user is typing in a text Input box
            focused = self.focused
            if focused and focused.__class__.__name__ == "Input":
                return
            key_map = {
                "1": "tab-containers",
                "2": "tab-images",
                "3": "tab-volumes",
                "4": "tab-networks",
                "5": "tab-system",
            }
            tab_id = key_map.get(event.key)
            if tab_id:
                self._switch_tab(tab_id)

    def _switch_tab(self, tab_id: str) -> None:
        try:
            tabs = self.query_one("#main-tabs", TabbedContent)
            tabs.active = tab_id
        except Exception:
            pass

    def on_tabbed_content_tab_activated(
        self, event: TabbedContent.TabActivated
    ) -> None:
        """Refresh data when a tab is activated."""
        self.call_later(self._refresh_active_tab)

    async def _refresh_active_tab(self) -> None:
        """Refresh whichever tab is currently active."""
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

    # ── Global actions ────────────────────────────────────────────────

    async def action_refresh(self) -> None:
        """Refresh the current tab's data."""
        await self._refresh_active_tab()
        self.notify("Refreshed", severity="information")

    def action_show_help(self) -> None:
        """Show the help dialog."""
        self.push_screen(HelpDialog())


def main() -> None:
    """Entry point for the dockdash CLI."""
    app = DockerDashApp()
    app.run()


if __name__ == "__main__":
    main()
