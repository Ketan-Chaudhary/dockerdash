"""Input dialog modals for user text input."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static


class InputDialog(ModalScreen[str | None]):
    """Single-field input dialog. Returns the entered value or None if cancelled."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        title: str,
        label: str,
        placeholder: str = "",
        default_value: str = "",
    ) -> None:
        super().__init__()
        self._title = title
        self._label = label
        self._placeholder = placeholder
        self._default_value = default_value

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Static(self._title, classes="modal-title")
            with Vertical(classes="modal-body"):
                yield Label(self._label)
                yield Input(
                    value=self._default_value,
                    placeholder=self._placeholder,
                    id="input-field",
                )
            with Horizontal(classes="modal-footer"):
                yield Button("Cancel", id="cancel-btn")
                yield Button("OK", id="ok-btn", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#input-field", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-btn":
            value = self.query_one("#input-field", Input).value.strip()
            self.dismiss(value if value else None)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        self.dismiss(value if value else None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class MultiInputDialog(ModalScreen[dict[str, str] | None]):
    """Multi-field input dialog. Returns a dict of field_id -> value, or None."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        title: str,
        fields: list[dict],
    ) -> None:
        """fields: list of dicts with keys: id, label, placeholder, default, type(optional)."""
        super().__init__()
        self._title = title
        self._fields = fields

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Static(self._title, classes="modal-title")
            with Vertical(classes="modal-body"):
                for field in self._fields:
                    yield Label(field.get("label", ""))
                    yield Input(
                        value=field.get("default", ""),
                        placeholder=field.get("placeholder", ""),
                        id=f"field-{field['id']}",
                        password=field.get("type") == "password",
                    )
            with Horizontal(classes="modal-footer"):
                yield Button("Cancel", id="cancel-btn")
                yield Button("OK", id="ok-btn", variant="primary")

    def on_mount(self) -> None:
        if self._fields:
            self.query_one(f"#field-{self._fields[0]['id']}", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-btn":
            result = {}
            for field in self._fields:
                inp = self.query_one(f"#field-{field['id']}", Input)
                result[field["id"]] = inp.value.strip()
            self.dismiss(result)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)
