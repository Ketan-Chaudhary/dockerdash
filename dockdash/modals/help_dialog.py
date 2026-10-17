"""Help dialog showing keyboard shortcuts reference."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

GLOBAL_SHORTCUTS = [
    ("q / Ctrl+C", "Exit dialog (Quit / Themes)"),
    ("t / T", "Theme & appearance settings"),
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
    ("t", "Attach terminal (Shell picker)"),
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
    ("l / h", "View visual image layers & history"),
    ("u", "Filter (all / dangling / unused)"),
    ("P", "Prune dangling images"),
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

LOG_VIEWER_SHORTCUTS = [
    ("Esc / q", "Close log viewer / clear filter"),
    ("f", "Toggle live follow stream (tail -f)"),
    ("a", "Toggle auto-scroll to bottom"),
    ("/", "Open search & live filter input"),
    ("t", "Toggle timestamp display"),
    ("w", "Toggle line wrapping"),
    ("c", "Clear displayed logs"),
    ("s", "Export logs to local file"),
]


def _render_section(title: str, shortcuts: list[tuple[str, str]]) -> str:
    """Render a section of shortcuts as Rich markup."""
    lines = [f"[$primary bold]━━ {title} ━━[/]\n"]
    for key, desc in shortcuts:
        lines.append(f"  [$primary bold]{key:<16}[/] [$foreground]{desc}[/]")
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
            dialog.styles.width = "72"
            dialog.styles.height = "80%"
            yield Static(
                "⟨ KEYBOARD SHORTCUTS ⟩", classes="modal-title"
            )
            with VerticalScroll(classes="modal-body"):
                yield Static(_render_section("GLOBAL", GLOBAL_SHORTCUTS))
                yield Static("")
                yield Static(_render_section("CONTAINERS", CONTAINER_SHORTCUTS))
                yield Static("")
                yield Static(_render_section("LOG VIEWER", LOG_VIEWER_SHORTCUTS))
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
            with Horizontal(classes="modal-footer"):
                yield Button("Close [Esc]", id="close-btn", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)
