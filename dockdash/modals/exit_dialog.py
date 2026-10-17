"""Exit confirmation and theme settings modal."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ExitDialog(ModalScreen[str]):
    """Dialog shown when user attempts to exit the application.

    Offers:
    1. Quit DockDash [Q]
    2. Theme Settings [S]

    Press Escape to close the dialog and resume.
    """

    BINDINGS = [
        ("escape", "cancel", "Close"),
        ("q", "quit_app", "Quit"),
        ("s", "open_settings", "Settings"),
        ("t", "open_settings", "Themes"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog exit-dialog"):
            yield Static("⟨ EXIT DOCKDASH ⟩", classes="modal-title")
            with Vertical(classes="exit-buttons"):
                yield Button(
                    "Quit DockDash [Q]",
                    id="quit-btn",
                    variant="error",
                )
                yield Button(
                    "Theme Settings [S]",
                    id="settings-btn",
                    variant="primary",
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit-btn":
            self.dismiss("quit")
        elif event.button.id == "settings-btn":
            self.dismiss("settings")

    def action_quit_app(self) -> None:
        self.dismiss("quit")

    def action_open_settings(self) -> None:
        self.dismiss("settings")

    def action_cancel(self) -> None:
        self.dismiss("cancel")
