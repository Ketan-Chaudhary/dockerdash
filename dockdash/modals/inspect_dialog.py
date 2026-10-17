"""JSON inspect dialog — full-screen for docker inspect output."""

from __future__ import annotations

import json

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static, TextArea


class InspectDialog(ModalScreen[None]):
    """Full-screen JSON inspect view with syntax highlighting."""

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
    ]

    DEFAULT_CSS = """
    InspectDialog {
        align: center middle;
        background: #0a0e17ee;
    }
    InspectDialog .inspect-container {
        width: 100%;
        height: 100%;
        background: #0a0e17;
        border: solid #2b384e;
    }
    InspectDialog .inspect-header {
        height: 1;
        background: #121824;
        color: #38bdf8;
        text-style: bold;
        padding: 0 1;
        border-bottom: solid #2b384e;
    }
    InspectDialog TextArea {
        height: 1fr;
        width: 100%;
    }
    """

    def __init__(self, title: str, data: dict) -> None:
        super().__init__()
        self._title = title
        self._data = data

    def compose(self) -> ComposeResult:
        formatted = json.dumps(self._data, indent=2, default=str)
        with Vertical(classes="inspect-container"):
            yield Static(
                f"⟨ INSPECT ⟩  {self._title}  "
                f"[#cbd5e1]Press [#38bdf8 bold]Esc[/][#cbd5e1] or [/]"
                f"[#38bdf8 bold]q[/][#cbd5e1] to close[/]",
                classes="inspect-header",
            )
            try:
                yield TextArea.code_editor(
                    formatted,
                    language="json",
                    read_only=True,
                    id="inspect-area",
                )
            except Exception:
                yield TextArea(
                    formatted,
                    read_only=True,
                    id="inspect-area",
                )

    def action_close(self) -> None:
        self.dismiss(None)
