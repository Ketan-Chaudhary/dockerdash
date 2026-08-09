"""Image pull progress display widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import ProgressBar, Static


class PullProgress(Vertical):
    """Displays image pull progress."""

    DEFAULT_CSS = """
    PullProgress {
        height: auto;
        min-height: 5;
        border: solid #30363d;
        background: #161b22;
        padding: 1 2;
    }
    PullProgress .pull-title {
        color: #79c0ff;
        text-style: bold;
    }
    PullProgress .pull-status-text {
        color: #8b949e;
        padding: 0 0 0 2;
    }
    """

    def __init__(self, image_name: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._image_name = image_name

    def compose(self) -> ComposeResult:
        yield Static(
            f"[bold]⟨ PULLING ⟩[/]  {self._image_name}",
            classes="pull-title",
        )
        yield ProgressBar(total=100, show_eta=False, id="pull-bar")
        yield Static("Preparing...", id="pull-status", classes="pull-status-text")

    def update_progress(self, percent: float, status: str = "") -> None:
        """Update the progress bar and status text."""
        bar = self.query_one("#pull-bar", ProgressBar)
        bar.update(progress=percent)
        if status:
            self.query_one("#pull-status", Static).update(status)

    def set_complete(self) -> None:
        """Mark the pull as complete."""
        bar = self.query_one("#pull-bar", ProgressBar)
        bar.update(progress=100)
        self.query_one("#pull-status", Static).update(
            "[#3fb950]✓ Pull complete[/]"
        )

    def set_error(self, message: str) -> None:
        """Show an error state."""
        self.query_one("#pull-status", Static).update(
            f"[#f85149]✕ {message}[/]"
        )
