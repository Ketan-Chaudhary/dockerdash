"""Modal dialog for choosing a shell or command when attaching to a container."""

from __future__ import annotations

import re
import shlex
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, Static


class ShellPickerDialog(ModalScreen[dict[str, Any] | None]):
    """Modal dialog allowing users to pick or enter a shell to exec into a container."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("1", "select_opt_1", "Auto", show=False),
        Binding("2", "select_opt_2", "bash", show=False),
        Binding("3", "select_opt_3", "sh", show=False),
        Binding("4", "select_opt_4", "zsh", show=False),
        Binding("5", "select_opt_5", "ash", show=False),
        Binding("6", "select_opt_6", "Custom", show=False),
    ]

    DEFAULT_CSS = """
    ShellPickerDialog {
        align: center middle;
        background: #000000bb;
    }

    ShellPickerDialog .picker-container {
        width: 82;
        max-width: 96%;
        height: auto;
        max-height: 24;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    ShellPickerDialog .picker-title {
        color: $primary;
        text-style: bold;
        text-align: center;
        width: 100%;
    }

    ShellPickerDialog .container-info {
        color: $text-muted;
        text-align: center;
        margin-bottom: 1;
        border-bottom: solid $border;
        padding-bottom: 0;
    }

    ShellPickerDialog .error-label {
        color: #f87171;
        text-style: bold;
        text-align: center;
        width: 100%;
        margin-bottom: 1;
        display: none;
    }

    ShellPickerDialog .picker-body {
        height: auto;
        width: 100%;
    }

    ShellPickerDialog .picker-col-left {
        width: 36;
        height: auto;
        padding-right: 1;
        border-right: solid $border;
    }

    ShellPickerDialog .picker-col-right {
        width: 1fr;
        height: auto;
        padding-left: 2;
    }

    ShellPickerDialog .section-label {
        color: $secondary;
        text-style: bold;
        margin-bottom: 0;
    }

    ShellPickerDialog RadioSet {
        background: transparent;
        border: none;
        padding: 0;
        margin-bottom: 0;
    }

    ShellPickerDialog RadioButton {
        background: transparent;
        color: $foreground;
        padding: 0 1;
        height: 1;
        margin: 0;
    }

    ShellPickerDialog RadioButton:focus {
        background: $panel;
        color: $primary;
        text-style: bold;
    }

    ShellPickerDialog Input {
        width: 100%;
        background: $panel;
        border: solid $border;
        color: $foreground;
        margin-bottom: 0;
        height: 3;
    }

    ShellPickerDialog Input:focus {
        border: solid $primary;
    }

    ShellPickerDialog .picker-buttons {
        layout: horizontal;
        align: right middle;
        margin-top: 1;
        height: 3;
    }

    ShellPickerDialog Button {
        margin-left: 1;
        min-width: 12;
    }
    """

    def __init__(self, container: dict[str, Any]) -> None:
        super().__init__()
        self.container = container
        self._selected_choice = "auto"

    def compose(self) -> ComposeResult:
        name = self.container.get("name", "unknown")
        image = self.container.get("image", "unknown")
        cid = self.container.get("id", "")[:12]

        with Vertical(classes="picker-container"):
            yield Static("⟨ ATTACH TERMINAL ⟩", classes="picker-title")
            yield Static(
                f"[#f8fafc bold]{name}[/]  [#38bdf8]({image})[/]  [#94a3b8][{cid}][/]",
                classes="container-info",
            )
            yield Label("", id="picker-error", classes="error-label")

            with Horizontal(classes="picker-body"):
                with Vertical(classes="picker-col-left"):
                    yield Label("Select Shell [1-6]:", classes="section-label")
                    with RadioSet(id="shell-radios"):
                        yield RadioButton("1. Auto-detect", id="opt-auto", value=True)
                        yield RadioButton("2. /bin/bash", id="opt-bash")
                        yield RadioButton("3. /bin/sh", id="opt-sh")
                        yield RadioButton("4. /bin/zsh", id="opt-zsh")
                        yield RadioButton("5. /bin/ash", id="opt-ash")
                        yield RadioButton("6. Custom Command", id="opt-custom")

                with Vertical(classes="picker-col-right"):
                    yield Label("Custom Command (opt 6):", classes="section-label")
                    yield Input(
                        placeholder="e.g. python, /bin/sh",
                        id="custom-command-input",
                    )

                    yield Label("User / UID (optional):", classes="section-label")
                    yield Input(
                        placeholder="e.g. root, 1000",
                        id="user-input",
                    )

                    with Horizontal(classes="picker-buttons"):
                        yield Button("Cancel [Esc]", variant="default", id="btn-cancel")
                        yield Button("Attach [Enter]", variant="primary", id="btn-attach")

    def _show_error(self, message: str) -> None:
        try:
            lbl = self.query_one("#picker-error", Label)
            lbl.update(f"⚠ {message}")
            lbl.styles.display = "block"
        except Exception:
            self.notify(message, severity="error")

    def _clear_error(self) -> None:
        try:
            lbl = self.query_one("#picker-error", Label)
            lbl.update("")
            lbl.styles.display = "none"
        except Exception:
            pass


    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        radio_id = event.pressed.id or ""
        mapping = {
            "opt-auto": "auto",
            "opt-bash": "bash",
            "opt-sh": "sh",
            "opt-zsh": "zsh",
            "opt-ash": "ash",
            "opt-custom": "custom",
        }
        self._selected_choice = mapping.get(radio_id, "auto")
        if self._selected_choice == "custom":
            try:
                self.query_one("#custom-command-input", Input).focus()
            except Exception:
                pass

    def action_select_opt_1(self) -> None:
        self._set_radio_and_choice("opt-auto", "auto")

    def action_select_opt_2(self) -> None:
        self._set_radio_and_choice("opt-bash", "bash")

    def action_select_opt_3(self) -> None:
        self._set_radio_and_choice("opt-sh", "sh")

    def action_select_opt_4(self) -> None:
        self._set_radio_and_choice("opt-zsh", "zsh")

    def action_select_opt_5(self) -> None:
        self._set_radio_and_choice("opt-ash", "ash")

    def action_select_opt_6(self) -> None:
        self._set_radio_and_choice("opt-custom", "custom")
        try:
            self.query_one("#custom-command-input", Input).focus()
        except Exception:
            pass

    def _set_radio_and_choice(self, radio_id: str, choice: str) -> None:
        try:
            radio = self.query_one(f"#{radio_id}", RadioButton)
            radio.value = True
            self._selected_choice = choice
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-attach":
            self._submit()
        elif event.button.id == "btn-cancel":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _submit(self) -> None:
        self._clear_error()
        user_val = self.query_one("#user-input", Input).value.strip() or None

        # Validate user / UID format
        if user_val:
            if not re.match(r"^[a-zA-Z0-9_.\-]+(?::[a-zA-Z0-9_.\-]+)?$", user_val):
                self._show_error("Invalid User/UID format. Use 'user', 'uid', or 'user:group'.")
                self.query_one("#user-input", Input).focus()
                return

        if self._selected_choice == "auto":
            command = [
                "/bin/sh",
                "-c",
                "if command -v bash >/dev/null 2>&1; then exec bash; "
                "elif command -v zsh >/dev/null 2>&1; then exec zsh; "
                "elif command -v ash >/dev/null 2>&1; then exec ash; "
                "else exec sh; fi",
            ]
        elif self._selected_choice == "bash":
            command = ["/bin/bash"]
        elif self._selected_choice == "sh":
            command = ["/bin/sh"]
        elif self._selected_choice == "zsh":
            command = ["/bin/zsh"]
        elif self._selected_choice == "ash":
            command = ["/bin/ash"]
        elif self._selected_choice == "custom":
            custom_val = self.query_one("#custom-command-input", Input).value.strip()
            if not custom_val:
                self._show_error("Please enter a custom command to execute.")
                self.query_one("#custom-command-input", Input).focus()
                return
            try:
                command = shlex.split(custom_val)
            except ValueError as e:
                self._show_error(f"Invalid command syntax: {e}")
                self.query_one("#custom-command-input", Input).focus()
                return
            if not command:
                self._show_error("Please enter a custom command to execute.")
                self.query_one("#custom-command-input", Input).focus()
                return
        else:
            command = ["/bin/sh"]

        self.dismiss({
            "command": command,
            "user": user_val,
            "choice": self._selected_choice,
        })
