"""Input dialog modals for user text input."""

from __future__ import annotations

from typing import Callable

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
        required: bool = False,
        validator: Callable[[str], str | None] | None = None,
    ) -> None:
        super().__init__()
        self._title = title
        self._label = label
        self._placeholder = placeholder
        self._default_value = default_value
        self._required = required
        self._validator = validator

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
                yield Label("", id="dialog-error", classes="error-label")
            with Horizontal(classes="modal-footer"):
                yield Button("Cancel", id="cancel-btn")
                yield Button("OK", id="ok-btn", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#input-field", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        event.input.remove_class("-invalid")
        self._clear_error()

    def _show_error(self, message: str) -> None:
        try:
            lbl = self.query_one("#dialog-error", Label)
            lbl.update(f"⚠ {message}")
            lbl.styles.display = "block"
        except Exception:
            pass
        try:
            inp = self.query_one("#input-field", Input)
            inp.add_class("-invalid")
            inp.focus()
        except Exception:
            pass
        self.notify(message, severity="error")

    def _clear_error(self) -> None:
        try:
            lbl = self.query_one("#dialog-error", Label)
            lbl.update("")
            lbl.styles.display = "none"
        except Exception:
            pass

    def _submit(self) -> None:
        self._clear_error()
        inp = self.query_one("#input-field", Input)
        value = inp.value.strip()

        if self._required and not value:
            self._show_error("This field is required.")
            return

        if self._validator and value:
            err = self._validator(value)
            if err:
                self._show_error(err)
                return

        self.dismiss(value if value else None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-btn":
            self._submit()
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

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
        """fields: list of dicts with keys: id, label, placeholder, default, type(optional), required(optional), validator(optional)."""
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
                yield Label("", id="dialog-error", classes="error-label")
            with Horizontal(classes="modal-footer"):
                yield Button("Cancel", id="cancel-btn")
                yield Button("OK", id="ok-btn", variant="primary")

    def on_mount(self) -> None:
        if self._fields:
            self.query_one(f"#field-{self._fields[0]['id']}", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        event.input.remove_class("-invalid")
        self._clear_error()

    def _show_error(self, field_id: str, message: str) -> None:
        try:
            lbl = self.query_one("#dialog-error", Label)
            lbl.update(f"⚠ {message}")
            lbl.styles.display = "block"
        except Exception:
            pass
        try:
            inp = self.query_one(f"#field-{field_id}", Input)
            inp.add_class("-invalid")
            inp.focus()
        except Exception:
            pass
        self.notify(message, severity="error")

    def _clear_error(self) -> None:
        try:
            lbl = self.query_one("#dialog-error", Label)
            lbl.update("")
            lbl.styles.display = "none"
        except Exception:
            pass

    def _submit(self) -> None:
        self._clear_error()
        result = {}
        for field in self._fields:
            fid = field["id"]
            inp = self.query_one(f"#field-{fid}", Input)
            inp.remove_class("-invalid")
            val = inp.value.strip()

            if field.get("required") and not val:
                label = field.get("label", fid).rstrip(":")
                self._show_error(fid, f"{label} is required.")
                return

            validator = field.get("validator")
            if validator and val:
                err = validator(val)
                if err:
                    self._show_error(fid, err)
                    return

            result[fid] = val

        self.dismiss(result)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-btn":
            self._submit()
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def action_cancel(self) -> None:
        self.dismiss(None)

