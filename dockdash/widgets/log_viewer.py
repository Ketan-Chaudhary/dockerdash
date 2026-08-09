"""Container log viewer screen — full-screen view with clean scrolling and controls."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import RichLog, Static


class LogViewerScreen(ModalScreen[None]):
    """Full-screen log viewer screen. Press Escape or q to close."""

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
        ("c", "clear_log", "Clear"),
    ]

    DEFAULT_CSS = """
    LogViewerScreen {
        align: center middle;
        background: #0d1117;
    }
    LogViewerScreen .log-container {
        width: 100%;
        height: 100%;
        background: #0d1117;
    }
    LogViewerScreen .log-header {
        dock: top;
        height: 1;
        background: #161b22;
        color: #79c0ff;
        padding: 0 1;
        border-bottom: solid #30363d;
    }
    LogViewerScreen RichLog {
        height: 1fr;
        background: #0d1117;
        padding: 0 1;
    }
    """

    def __init__(self, title: str = "Logs", content: str = "") -> None:
        super().__init__()
        self._title = title
        self._content = content

    def compose(self) -> ComposeResult:
        with Vertical(classes="log-container"):
            yield Static(
                f"[bold cyan]⟨ {self._title} ⟩[/]  "
                f"[#8b949e]Keys:[/] [#79c0ff bold]Esc[/]/[#79c0ff bold]q[/] close  "
                f"[#79c0ff bold]c[/] clear  "
                f"[#79c0ff bold]↑↓[/] scroll",
                classes="log-header",
            )
            yield RichLog(
                highlight=True,
                markup=True,
                wrap=True,
                id="log-output",
            )

    def on_mount(self) -> None:
        log = self.query_one("#log-output", RichLog)
        log.clear()
        if self._content and self._content.strip():
            # Write raw text without trying to interpret random bracket tokens as markup
            log.markup = False
            for line in self._content.splitlines():
                log.write(line)
        else:
            log.markup = True
            log.write("[dim italic]No log output recorded for this container.[/dim italic]")
        log.focus()

    def action_clear_log(self) -> None:
        log = self.query_one("#log-output", RichLog)
        log.clear()
        log.markup = True
        log.write("[dim italic]Log display cleared.[/dim italic]")

    def action_close(self) -> None:
        self.dismiss(None)
