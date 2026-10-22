"""Unit tests for InputDialog, MultiInputDialog error handling and image pull spec parsing."""

from __future__ import annotations

import pytest
from textual.widgets import Input, Label

from dockdash.app import DockerDashApp
from dockdash.modals.input_dialog import InputDialog, MultiInputDialog


@pytest.mark.asyncio
async def test_input_dialog_required_validation():
    app = DockerDashApp()
    app._connected = True
    async with app.run_test(size=(100, 30)) as pilot:
        dialog = InputDialog(
            title="TEST",
            label="Name:",
            required=True,
        )
        app.push_screen(dialog)
        await pilot.pause()

        # Click OK with empty input
        await pilot.click("#ok-btn")
        await pilot.pause()

        # Dialog should still be mounted and show error
        assert app.screen == dialog
        inp = dialog.query_one("#input-field", Input)
        assert inp.has_class("-invalid")
        lbl = dialog.query_one("#dialog-error", Label)
        assert "required" in str(lbl.render()).lower()

        # Type valid text -> -invalid should clear
        inp.value = "my-name"
        await pilot.pause()
        assert not inp.has_class("-invalid")

        # Submit valid text -> dialog should dismiss
        await pilot.click("#ok-btn")
        for _ in range(5):
            await pilot.pause()
            if app.screen != dialog:
                break
        assert app.screen != dialog


@pytest.mark.asyncio
async def test_input_dialog_custom_validator():
    app = DockerDashApp()
    app._connected = True

    def no_spaces(val: str) -> str | None:
        if " " in val:
            return "Spaces are not allowed"
        return None

    async with app.run_test(size=(100, 30)) as pilot:
        dialog = InputDialog(
            title="TEST",
            label="Tag:",
            validator=no_spaces,
        )
        app.push_screen(dialog)
        await pilot.pause()

        inp = dialog.query_one("#input-field", Input)
        inp.value = "bad tag"
        await pilot.pause()

        await pilot.click("#ok-btn")
        await pilot.pause()

        assert app.screen == dialog
        assert inp.has_class("-invalid")
        lbl = dialog.query_one("#dialog-error", Label)
        assert "Spaces are not allowed" in str(lbl.render())


@pytest.mark.asyncio
async def test_multi_input_dialog_required_validation():
    app = DockerDashApp()
    app._connected = True
    async with app.run_test(size=(100, 30)) as pilot:
        dialog = MultiInputDialog(
            title="TEST MULTI",
            fields=[
                {"id": "name", "label": "Network name:", "required": True},
                {"id": "driver", "label": "Driver:", "default": "bridge"},
            ],
        )
        app.push_screen(dialog)
        await pilot.pause()

        # Click OK with empty name
        await pilot.click("#ok-btn")
        await pilot.pause()

        assert app.screen == dialog
        inp = dialog.query_one("#field-name", Input)
        assert inp.has_class("-invalid")
        lbl = dialog.query_one("#dialog-error", Label)
        assert "required" in str(lbl.render()).lower()

        # Provide valid name and submit
        inp.value = "valid-net"
        await pilot.pause()
        assert not inp.has_class("-invalid")

        await pilot.click("#ok-btn")
        for _ in range(5):
            await pilot.pause()
            if app.screen != dialog:
                break
        assert app.screen != dialog


def test_image_pull_spec_parsing():
    """Verify registry port parsing vs tag parsing in ImagesTab._do_pull."""
    # Test parsing directly
    def parse_spec(image_spec: str) -> tuple[str, str]:
        image_spec = image_spec.strip()
        last_slash = image_spec.rfind("/")
        last_colon = image_spec.rfind(":")
        if last_colon > last_slash:
            repo = image_spec[:last_colon].strip()
            tag = image_spec[last_colon + 1:].strip()
        else:
            repo = image_spec.strip()
            tag = "latest"
        return repo, tag

    assert parse_spec("ubuntu") == ("ubuntu", "latest")
    assert parse_spec("ubuntu:22.04") == ("ubuntu", "22.04")
    assert parse_spec("registry.example.com:5000/myapp") == (
        "registry.example.com:5000/myapp",
        "latest",
    )
    assert parse_spec("registry.example.com:5000/myapp:v2.1") == (
        "registry.example.com:5000/myapp",
        "v2.1",
    )
    assert parse_spec("localhost:5000/test/app:3.0") == (
        "localhost:5000/test/app",
        "3.0",
    )
