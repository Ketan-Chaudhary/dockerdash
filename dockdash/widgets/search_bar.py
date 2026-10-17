"""Inline search/filter bar for DataTable views."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Input, Static


class SearchBar(Horizontal):
    """A search bar that filters DataTable rows.

    Posts SearchBar.Changed when query changes,
    SearchBar.Submitted when Enter is pressed,
    and SearchBar.Dismissed when Escape is pressed.
    """

    DEFAULT_CSS = """
    SearchBar {
        dock: top;
        height: 3;
        background: $surface;
        border: solid $primary;
        padding: 0 1;
        layout: horizontal;
        display: none;
        margin-bottom: 1;
    }
    SearchBar.-visible {
        display: block;
    }
    SearchBar .search-icon {
        width: auto;
        height: 1;
        color: $primary;
        text-style: bold;
        margin: 0 1 0 0;
    }
    SearchBar Input {
        width: 1fr;
        height: 1;
        border: none;
        background: transparent;
        color: $foreground;
        padding: 0;
    }
    SearchBar Input:focus {
        border: none;
    }
    """

    class Changed(Message):
        """Posted when the search query changes."""

        def __init__(self, query: str) -> None:
            super().__init__()
            self.query = query

    class Submitted(Message):
        """Posted when Enter is pressed to navigate into results."""

        def __init__(self, query: str) -> None:
            super().__init__()
            self.query = query

    class Dismissed(Message):
        """Posted when the search bar is dismissed."""

    def compose(self) -> ComposeResult:
        yield Static(" / ", classes="search-icon")
        yield Input(placeholder="Type to filter... (Enter: results, Esc: exit)", id="search-input")

    def show(self) -> None:
        """Show the search bar and focus input."""
        self.add_class("-visible")
        inp = self.query_one("#search-input", Input)
        inp.value = ""
        inp.focus()

    def hide(self) -> None:
        """Hide the search bar and clear the search filter."""
        self.remove_class("-visible")
        inp = self.query_one("#search-input", Input)
        inp.value = ""
        self.post_message(self.Changed(""))

    @property
    def visible_search(self) -> bool:
        return self.has_class("-visible")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.post_message(self.Changed(event.value))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            event.stop()
            self.post_message(self.Submitted(event.value))

    def on_key(self, event) -> None:
        if event.key == "escape":
            event.prevent_default()
            event.stop()
            self.hide()
            self.post_message(self.Dismissed())
        elif event.key == "enter":
            event.prevent_default()
            event.stop()
            inp = self.query_one("#search-input", Input)
            self.post_message(self.Submitted(inp.value))
