"""Help dialog showing keyboard shortcuts reference."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

GLOBAL_SHORTCUTS = [
    ("q / Ctrl+C", "Quit application"),
    ("1-6", "Jump to tab (Containers/Images/Volumes/Networks/Compose/System)"),
    ("r / F5", "Refresh current view"),
    ("/", "Open search / filter"),
    ("? / F1", "Show this help"),
    ("Escape", "Close dialog / search"),
    ("↑ ↓ / j k", "Navigate table rows"),
    ("Enter", "Select / confirm"),
]

CONTAINER_SHORTCUTS = [
    ("s", "Start container"),
    ("S", "Stop container"),
    ("R", "Restart container"),
    ("d", "Delete container"),
    ("l", "View container logs"),
    ("i", "Inspect container (JSON)"),
    ("t", "Attach terminal (exec shell)"),
    ("p", "Pause / Unpause container"),
    ("n", "Rename container"),
    ("a", "View container stats"),
]

IMAGE_SHORTCUTS = [
    ("p", "Pull new image"),
    ("d", "Delete image"),
    ("t", "Tag / rename image"),
    ("c", "Create container from image"),
    ("i", "Inspect image (JSON)"),
    ("h", "View image history / layers"),
]

VOLUME_SHORTCUTS = [
    ("c", "Create volume"),
    ("d", "Delete volume"),
    ("i", "Inspect volume"),
]

NETWORK_SHORTCUTS = [
    ("c", "Create network"),
    ("d", "Delete network"),
    ("i", "Inspect network"),
]

COMPOSE_SHORTCUTS = [
    ("u", "Compose up -d"),
    ("d", "Compose down"),
    ("s", "Start stack containers"),
    ("S", "Stop stack containers"),
    ("R", "Restart stack containers"),
    ("l", "View combined stack logs"),
    ("e", "Edit compose file in editor"),
    ("p", "Pull stack images"),
]

SYSTEM_SHORTCUTS = [
    ("c", "Prune stopped containers"),
    ("i", "Prune dangling images"),
    ("v", "Prune unused volumes"),
    ("n", "Prune unused networks"),
    ("x", "Full system prune"),
]


def _render_section(title: str, shortcuts: list[tuple[str, str]]) -> str:
    """Render a section of shortcuts as Rich markup."""
    lines = [f"[#3fb9a0 bold]━━ {title} ━━[/]\n"]
    for key, desc in shortcuts:
        lines.append(f"  [#79c0ff bold]{key:<16}[/] [#e6edf3]{desc}[/]")
    return "\n".join(lines)


class HelpDialog(ModalScreen[None]):
    """Full keyboard shortcuts reference."""

    BINDINGS = [
        ("escape", "close", "Close"),
        ("question_mark", "close", "Close"),
        ("f1", "close", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog") as dialog:
            dialog.styles.width = "70"
            dialog.styles.height = "80%"
            yield Static(
                "⟨ KEYBOARD SHORTCUTS ⟩", classes="modal-title"
            )
            with VerticalScroll(classes="modal-body"):
                yield Static(_render_section("GLOBAL", GLOBAL_SHORTCUTS))
                yield Static("")
                yield Static(_render_section("CONTAINERS", CONTAINER_SHORTCUTS))
                yield Static("")
                yield Static(_render_section("IMAGES", IMAGE_SHORTCUTS))
                yield Static("")
                yield Static(_render_section("VOLUMES", VOLUME_SHORTCUTS))
                yield Static("")
                yield Static(_render_section("NETWORKS", NETWORK_SHORTCUTS))
                yield Static("")
                yield Static(_render_section("COMPOSE STACKS", COMPOSE_SHORTCUTS))
                yield Static("")
                yield Static(_render_section("SYSTEM & CLEANUP", SYSTEM_SHORTCUTS))
            yield Button("Close", id="close-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)
