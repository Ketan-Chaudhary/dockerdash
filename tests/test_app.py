"""Unit tests for DockerDashApp TUI navigation, ComposeTab, and screens."""

import pytest

from dockdash.app import DockerDashApp


@pytest.mark.asyncio
async def test_app_launch_and_title():
    app = DockerDashApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert app.TITLE.startswith("DockDash")
        assert app.SUB_TITLE == "Docker Dashboard"


@pytest.mark.asyncio
async def test_help_modal():
    app = DockerDashApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.action_show_help()
        await pilot.pause()
        assert app.screen.__class__.__name__ == "HelpDialog"

        await pilot.press("escape")
        await pilot.pause()
        assert app.screen.__class__.__name__ != "HelpDialog"


@pytest.mark.asyncio
async def test_compose_tab_presence():
    app = DockerDashApp()
    # Force _connected = True to test DOM tab presence on headless CI runners (macOS, Windows, Linux)
    app._connected = True
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        compose_tab = app.query_one("#compose-tab")
        assert compose_tab is not None


@pytest.mark.asyncio
async def test_container_selection_matches_cursor_row_key():
    from textual.app import App
    from textual.widgets import DataTable

    from dockdash.screens.containers import ContainersTab

    class TestApp(App):
        def compose(self):
            yield ContainersTab(id="containers-tab")

    app = TestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        tab = app.query_one(ContainersTab)
        tab._containers = [
            {"id": "111", "full_id": "full_111", "name": "c1", "image": "img1", "status": "running", "state": "running", "ports": ""},
            {"id": "222", "full_id": "full_222", "name": "c2", "image": "img2", "status": "running", "state": "running", "ports": ""},
        ]
        tab._filtered = list(tab._containers)
        tab._update_table()

        table = tab.query_one("#container-table", DataTable)
        assert tab._get_selected_container()["name"] == "c1"

        table.cursor_coordinate = (1, 0)
        assert tab._get_selected_container()["name"] == "c2"

        # Reverse _filtered to mimic docker list reordering / filtering desync
        tab._filtered = list(reversed(tab._containers))
        # Cursor is at row 1 (which visual table still has as c2)
        assert tab._get_selected_container()["name"] == "c2"

        # Move cursor to row 0 (which visual table has as c1)
        table.cursor_coordinate = (0, 0)
        assert tab._get_selected_container()["name"] == "c1"


@pytest.mark.asyncio
async def test_image_search_enter_and_escape():
    from textual.app import App
    from textual.widgets import DataTable, Input

    from dockdash.screens.images import ImagesTab
    from dockdash.widgets.search_bar import SearchBar

    class TestApp(App):
        def compose(self):
            yield ImagesTab(id="images-tab")

    app = TestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        tab = app.query_one(ImagesTab)
        tab._images = [
            {"id": "img1", "full_id": "full_img1", "repository": "nginx", "tag": "latest", "size": 1000, "created": "2026-01-01"},
            {"id": "img2", "full_id": "full_img2", "repository": "redis", "tag": "alpine", "size": 2000, "created": "2026-01-01"},
        ]
        tab._filtered = list(tab._images)
        tab._update_table()

        table = tab.query_one("#image-table", DataTable)
        table.focus()
        await pilot.pause()

        # Open search with slash
        await pilot.press("slash")
        await pilot.pause()
        search_bar = tab.query_one("#image-search", SearchBar)
        assert search_bar.visible_search
        assert isinstance(app.focused, Input)

        # Type filter query
        await pilot.press("n", "g", "i", "n", "x")
        await pilot.pause()
        assert len(tab._filtered) == 1
        assert tab._filtered[0]["repository"] == "nginx"

        # Press Enter to navigate into the results table
        await pilot.press("enter")
        await pilot.pause()
        assert app.focused == table
        assert search_bar.visible_search

        # Press Escape from table to exit search and restore full list
        await pilot.press("escape")
        await pilot.pause()
        assert not search_bar.visible_search
        assert len(tab._filtered) == 2

