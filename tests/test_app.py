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


@pytest.mark.asyncio
async def test_footer_tab_and_actions_bar_visibility():
    """Verify that active tab title, footer keys, and actions bar are visible and on-screen."""
    from textual.widgets import Footer

    app = DockerDashApp()
    app._connected = True
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()

        # 1. Active tab title must be rendered with non-zero height
        tab = app.query_one("Tab.-active")
        assert tab.content_size.height == 1
        assert "Containers" in str(tab.render())

        # 2. Footer keys must be within visible screen height (y < 30)
        footer = app.query_one(Footer)
        assert footer.size.height == 1
        for child in footer.children:
            assert child.region.y < 30

        # 3. Actions bar must have non-zero content height
        bar = app.query_one(".actions-bar")
        assert bar.content_size.height == 1
        assert "CONTAINERS" in str(bar.render())


@pytest.mark.asyncio
async def test_tab_titles_have_number_notations():
    """Verify that all tabs display the expected name and number notation (1-6)."""
    from textual.widgets import Tab

    app = DockerDashApp()
    app._connected = True
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        tab_labels = [t.label.plain for t in app.query(Tab)]
        expected = [
            "Containers (1)",
            "Images (2)",
            "Volumes (3)",
            "Networks (4)",
            "Compose (5)",
            "System (6)",
        ]
        assert tab_labels == expected


@pytest.mark.asyncio
async def test_exit_dialog_cancel():
    """Verify that action_quit shows ExitDialog and Escape cancels."""
    app = DockerDashApp()
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        app.action_quit()
        await pilot.pause()
        assert app.screen.__class__.__name__ == "ExitDialog"

        # Cancel with Escape
        await pilot.press("escape")
        await pilot.pause()
        assert app.screen.__class__.__name__ != "ExitDialog"


@pytest.mark.asyncio
async def test_exit_dialog_opens_theme_settings():
    """Verify that pressing 's' in ExitDialog transitions to ThemeDialog."""
    app = DockerDashApp()
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        app.action_quit()
        await pilot.pause()
        assert app.screen.__class__.__name__ == "ExitDialog"

        # Press 's' to choose Theme Settings
        await pilot.press("s")
        await pilot.pause()
        assert app.screen.__class__.__name__ == "ThemeDialog"

        # Cancel theme dialog
        await pilot.press("escape")
        await pilot.pause()
        assert app.screen.__class__.__name__ != "ThemeDialog"


@pytest.mark.asyncio
async def test_theme_dialog_reverts_on_cancel():
    """Verify that cancelling ThemeDialog reverts the previewed theme."""
    from dockdash.modals.theme_dialog import ThemeDialog

    app = DockerDashApp()
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        orig_theme = app.theme

        app.push_screen(ThemeDialog())
        await pilot.pause()
        assert app.screen.__class__.__name__ == "ThemeDialog"

        # Arrow down to preview next theme
        await pilot.press("down")
        await pilot.pause()
        # Theme should have previewed a different theme
        assert app.theme != orig_theme

        # Escape should cancel and restore orig_theme
        await pilot.press("escape")
        await pilot.pause()
        assert app.theme == orig_theme


@pytest.mark.asyncio
async def test_theme_dialog_apply_saves(monkeypatch, tmp_path):
    """Verify that pressing Enter on ThemeDialog saves and applies the theme."""
    import dockdash.themes as themes_mod
    from dockdash.modals.theme_dialog import ThemeDialog

    fake_config = tmp_path / "config.json"
    monkeypatch.setattr(themes_mod, "CONFIG_FILE", fake_config)
    monkeypatch.setattr(themes_mod, "CONFIG_DIR", tmp_path)

    app = DockerDashApp()
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()

        app.push_screen(ThemeDialog())
        await pilot.pause()

        # Arrow down to select next theme
        await pilot.press("down")
        await pilot.pause()
        new_theme = app.theme

        # Press enter on the option list to save
        await pilot.press("enter")
        await pilot.pause()

        assert app.screen.__class__.__name__ != "ThemeDialog"
        assert app.theme == new_theme
        assert themes_mod.get_saved_theme() == new_theme


def test_theme_fallback_and_config(monkeypatch, tmp_path):
    """Test get_saved_theme and save_theme behavior with fallbacks."""
    import dockdash.themes as themes_mod

    fake_config = tmp_path / "config.json"
    monkeypatch.setattr(themes_mod, "CONFIG_FILE", fake_config)
    monkeypatch.setattr(themes_mod, "CONFIG_DIR", tmp_path)

    # When file doesn't exist, return default theme
    assert themes_mod.get_saved_theme() == "cyber-slate"

    # Saving valid theme works
    assert themes_mod.save_theme("tokyo-night")
    assert themes_mod.get_saved_theme() == "tokyo-night"

    # Invalid theme in config falls back to default
    themes_mod.save_config({"theme": "non-existent-theme-xyz"})
    assert themes_mod.get_saved_theme() == "cyber-slate"


@pytest.mark.asyncio
async def test_command_palette_quit_quits_directly():
    """Verify that selecting Quit from command palette exits directly without modal."""
    app = DockerDashApp()
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        commands = list(app.get_system_commands(app.screen))
        quit_cmd = next((c for c in commands if c.title == "Quit"), None)
        assert quit_cmd is not None
        # The callback must be app.exit directly, not action_quit which shows the modal
        assert quit_cmd.callback == app.exit


@pytest.mark.asyncio
async def test_command_palette_theme_routes_to_dialog():
    """Verify that Theme command in palette routes to action_open_themes."""
    app = DockerDashApp()
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        commands = list(app.get_system_commands(app.screen))
        theme_cmd = next((c for c in commands if c.title == "Theme"), None)
        assert theme_cmd is not None
        assert theme_cmd.callback == app.action_open_themes



