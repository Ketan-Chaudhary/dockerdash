"""Confirmation dialog modal for destructive actions."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class ConfirmDialog(ModalScreen[bool]):
    """A reusable confirmation dialog with danger level styling.

    Yields True if confirmed, False if cancelled.
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "confirm", "Confirm"),
    ]

    def __init__(
        self,
        title: str,
        message: str,
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
        danger: bool = False,
    ) -> None:
        super().__init__()
        self._title = title
        self._message = message
        self._confirm_label = confirm_label
        self._cancel_label = cancel_label
        self._danger = danger

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Static(self._title, classes="modal-title")
            with Vertical(classes="modal-body"):
                if self._danger:
                    yield Static(
                        "⚠ WARNING — This action cannot be undone.",
                        classes="text-error text-bold",
                    )
                yield Label(self._message)
            with Horizontal(classes="modal-footer"):
                yield Button(
                    self._cancel_label, id="cancel-btn", variant="default"
                )
                yield Button(
                    self._confirm_label,
                    id="confirm-btn",
                    variant="error" if self._danger else "primary",
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-btn":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)
