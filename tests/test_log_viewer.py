"""Unit tests for LogViewerScreen live streaming, filtering, and auto-scroll."""

from __future__ import annotations

import os

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input, RichLog, Static

from dockdash.widgets.log_viewer import LogViewerScreen


class DummyLogApp(App[None]):
    """Test harness for mounting LogViewerScreen."""

    def __init__(self, screen: LogViewerScreen) -> None:
        super().__init__()
        self._test_screen = screen

    def compose(self) -> ComposeResult:
        yield Static("App Root")

    def on_mount(self) -> None:
        self.push_screen(self._test_screen)


@pytest.mark.asyncio
async def test_log_viewer_mount_and_content():
    """Verify LogViewerScreen displays initial content and header."""
    sample_content = (
        "2026-10-11T12:00:00.000Z Starting web server...\n"
        "2026-10-11T12:00:01.000Z Listening on port 8080\n"
        "2026-10-11T12:00:02.000Z Ready for connections"
    )
    screen = LogViewerScreen(title="TEST-CONTAINER", content=sample_content)
    app = DummyLogApp(screen)

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert len(screen._all_lines) == 3
        assert "TEST-CONTAINER" in screen._title

        rich_log = screen.query_one("#log-output", RichLog)
        assert rich_log is not None

        header = screen.query_one("#log-header", Static)
        assert "3 lines" in str(header.content)


@pytest.mark.asyncio
async def test_log_viewer_search_and_filter():
    """Verify live search filtering and match counting."""
    sample_content = (
        "INFO server started\n"
        "ERROR database connection failed\n"
        "WARN high memory usage\n"
        "ERROR retry failed"
    )
    screen = LogViewerScreen(title="SEARCH-TEST", content=sample_content)
    app = DummyLogApp(screen)

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        # Open search bar
        screen.action_open_filter()
        await pilot.pause()

        search_bar = screen.query_one("#log-search-bar")
        assert "visible" in search_bar.classes

        # Filter by ERROR
        search_input = screen.query_one("#log-search-input", Input)
        search_input.value = "error"
        await pilot.pause()

        assert screen._match_count == 2
        matches_label = screen.query_one("#log-search-matches", Static)
        assert "2/4 matches" in str(matches_label.content)

        # Clear filter via action_close while search is focused
        screen.action_close()
        await pilot.pause()

        assert screen._filter_query == ""
        assert "visible" not in search_bar.classes


@pytest.mark.asyncio
async def test_log_viewer_toggles_and_clear():
    """Verify auto-scroll, timestamps, wrap, and clear actions."""
    sample_content = "2026-10-11T12:00:00Z line one\n2026-10-11T12:00:01Z line two"
    screen = LogViewerScreen(title="TOGGLES-TEST", content=sample_content)
    app = DummyLogApp(screen)

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        # Toggle auto-scroll
        assert screen._auto_scroll is True
        screen.action_toggle_auto_scroll()
        assert screen._auto_scroll is False
        screen.action_toggle_auto_scroll()
        assert screen._auto_scroll is True

        # Toggle timestamps
        assert screen._show_timestamps is True
        screen.action_toggle_timestamps()
        assert screen._show_timestamps is False

        # Toggle wrap
        assert screen._wrap is True
        screen.action_toggle_wrap()
        assert screen._wrap is False

        # Clear logs
        screen.action_clear_log()
        assert len(screen._all_lines) == 0
        assert screen._match_count == 0


@pytest.mark.asyncio
async def test_log_viewer_save_action(tmp_path):
    """Verify log file export functionality."""
    sample_content = "line 1\nline 2\nline 3"
    screen = LogViewerScreen(title="EXPORT-TEST", content=sample_content)
    app = DummyLogApp(screen)

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        # Call action_save_log
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            screen.action_save_log()
            saved_files = list(tmp_path.glob("*.log"))
            assert len(saved_files) == 1
            content = saved_files[0].read_text(encoding="utf-8")
            assert "line 1\nline 2\nline 3" in content
        finally:
            os.chdir(original_cwd)
