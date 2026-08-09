"""Inline search/filter bar for DataTable views."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Input, Static


class SearchBar(Horizontal):
    """A search bar that filters DataTable rows.

    Posts a SearchBar.Changed message with the current query.
    """

    DEFAULT_CSS = """
    SearchBar {
        dock: top;
        height: 3;
        background: #161b22;
        border-bottom: solid #30363d;
        padding: 0 1;
        display: none;
    }
    SearchBar.-visible {
        display: block;
    }
    SearchBar .search-icon {
        width: 4;
        height: 3;
        content-align: center middle;
        color: #58a6ff;
    }
    SearchBar Input {
        width: 1fr;
    }
    """

    class Changed(Message):
        """Posted when the search query changes."""

        def __init__(self, query: str) -> None:
            super().__init__()
            self.query = query

    class Dismissed(Message):
        """Posted when the search bar is dismissed."""

    def compose(self) -> ComposeResult:
        yield Static(" / ", classes="search-icon")
        yield Input(placeholder="Type to filter...", id="search-input")

    def show(self) -> None:
        """Show the search bar and focus input."""
        self.add_class("-visible")
        self.query_one("#search-input", Input).value = ""
        self.query_one("#search-input", Input).focus()

    def hide(self) -> None:
        """Hide the search bar."""
        self.remove_class("-visible")
        self.query_one("#search-input", Input).value = ""
        self.post_message(self.Changed(""))

    @property
    def visible_search(self) -> bool:
        return self.has_class("-visible")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.post_message(self.Changed(event.value))

    def on_key(self, event) -> None:
        if event.key == "escape":
            event.prevent_default()
            event.stop()
            self.hide()
            self.post_message(self.Dismissed())
