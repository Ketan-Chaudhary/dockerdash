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
