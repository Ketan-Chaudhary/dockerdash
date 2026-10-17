"""Unit tests for ShellPickerDialog and terminal attach."""

from __future__ import annotations

import pytest

from dockdash.app import DockerDashApp
from dockdash.modals.shell_picker import ShellPickerDialog
from dockdash.screens.containers import ContainersTab


def test_shell_picker_options():
    dummy_container = {
        "id": "123456789abc",
        "name": "test-box",
        "image": "alpine:latest",
    }
    dialog = ShellPickerDialog(dummy_container)
    assert dialog.container["name"] == "test-box"
    assert dialog._selected_choice == "auto"


@pytest.mark.asyncio
async def test_shell_picker_interactions():
    dummy_container = {
        "id": "123456789abc",
        "name": "test-box",
        "image": "alpine:latest",
    }
    app = DockerDashApp()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        dialog = ShellPickerDialog(dummy_container)
        app.push_screen(dialog)
        await pilot.pause(0.2)

        assert app.screen.__class__.__name__ == "ShellPickerDialog"

        # Press '2' to pick bash
        await pilot.press("2")
        await pilot.pause(0.1)
        assert dialog._selected_choice == "bash"

        # Press '3' to pick sh
        await pilot.press("3")
        await pilot.pause(0.1)
        assert dialog._selected_choice == "sh"

        # Press '1' to pick auto
        await pilot.press("1")
        await pilot.pause(0.1)
        assert dialog._selected_choice == "auto"

        # Press Escape to cancel
        await pilot.press("escape")
        await pilot.pause(0.1)
        assert app.screen.__class__.__name__ != "ShellPickerDialog"


@pytest.mark.asyncio
async def test_containers_tab_t_key_opens_shell_picker(monkeypatch):
    """Verify pressing 't' on running container pushes ShellPickerDialog."""
    app = DockerDashApp()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        containers_tab = app.query_one("#containers-tab", ContainersTab)

        # Mock selected running container
        monkeypatch.setattr(
            containers_tab,
            "_get_selected_container",
            lambda: {
                "id": "abc123456789",
                "full_id": "sha256:abc123456789",
                "name": "web",
                "image": "nginx:alpine",
                "status": "running",
            },
        )

        # Press 't'
        await pilot.press("t")
        await pilot.pause(0.2)

        assert app.screen.__class__.__name__ == "ShellPickerDialog"
        await pilot.press("escape")
        await pilot.pause(0.1)
        assert app.screen.__class__.__name__ != "ShellPickerDialog"
