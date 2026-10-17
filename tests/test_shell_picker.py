"""Unit tests for ShellPickerDialog and terminal attach."""

from __future__ import annotations

import subprocess

import pytest
from textual.widgets import Input, Label

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
async def test_shell_picker_validation_errors():
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

        # 1. Invalid username format (spaces/special characters)
        user_input = dialog.query_one("#user-input", Input)
        user_input.value = "invalid user name!"
        dialog._submit()
        await pilot.pause(0.1)

        # Verify dialog stayed open and error label was updated
        assert app.screen.__class__.__name__ == "ShellPickerDialog"
        err_lbl = dialog.query_one("#picker-error", Label)
        assert "Invalid User/UID format" in str(err_lbl.render())

        # Clear user input
        user_input.value = "validuser"

        # 2. Custom command option selected with empty command
        dialog.action_select_opt_6()  # selects custom
        custom_input = dialog.query_one("#custom-command-input", Input)
        custom_input.value = ""
        dialog._submit()
        await pilot.pause(0.1)

        assert app.screen.__class__.__name__ == "ShellPickerDialog"
        assert "Please enter a custom command" in str(err_lbl.render())

        # 3. Custom command option selected with unmatched quote syntax error
        custom_input.value = 'bash -c "unclosed string'
        dialog._submit()
        await pilot.pause(0.1)

        assert app.screen.__class__.__name__ == "ShellPickerDialog"
        assert "Invalid command syntax" in str(err_lbl.render())

        # Close dialog
        await pilot.press("escape")
        await pilot.pause(0.1)
        assert app.screen.__class__.__name__ != "ShellPickerDialog"


@pytest.mark.asyncio
async def test_containers_tab_user_not_found_precheck(monkeypatch):
    """Verify that if user does not exist in container, attach aborts with error notification."""
    app = DockerDashApp()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        containers_tab = app.query_one("#containers-tab", ContainersTab)

        container = {
            "id": "abc123456789",
            "full_id": "sha256:abc123456789",
            "name": "test-web",
            "image": "nginx:alpine",
            "status": "running",
        }

        # Mock inspect_container to report running
        async def mock_inspect(_):
            return {"State": {"Running": True, "Status": "running"}}
        monkeypatch.setattr(containers_tab._docker, "inspect_container", mock_inspect)

        # Mock subprocess.run to simulate Docker daemon error: user not found
        fake_probe = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="Error response from daemon: unable to find user ghost: no matching entries in passwd file",
        )
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: fake_probe)

        # Track notify calls
        notified = []
        monkeypatch.setattr(containers_tab, "notify", lambda msg, **kw: notified.append((msg, kw)))

        # Track _do_attach calls (should NOT be called)
        do_attach_called = []
        monkeypatch.setattr(containers_tab, "_do_attach", lambda *args: do_attach_called.append(args))

        # Run _validate_and_attach
        await containers_tab._validate_and_attach(container, ["/bin/sh"], user="ghost")

        assert len(do_attach_called) == 0
        assert len(notified) == 1
        assert "User 'ghost' not found in container 'test-web'" in notified[0][0]


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


@pytest.mark.asyncio
async def test_containers_tab_custom_command_not_found_precheck(monkeypatch):
    """Verify that if custom command does not exist in container, attach aborts with error notification."""
    app = DockerDashApp()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        containers_tab = app.query_one("#containers-tab", ContainersTab)

        container = {
            "id": "abc123456789",
            "full_id": "sha256:abc123456789",
            "name": "test-web",
            "image": "nginx:alpine",
            "status": "running",
        }

        # Mock inspect_container to report running
        async def mock_inspect(_):
            return {"State": {"Running": True, "Status": "running"}}
        monkeypatch.setattr(containers_tab._docker, "inspect_container", mock_inspect)

        # Mock subprocess.run to simulate command not found in container
        fake_probe = subprocess.CompletedProcess(
            args=[],
            returncode=127,
            stdout="",
            stderr="",
        )
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: fake_probe)

        # Track notify calls
        notified = []
        monkeypatch.setattr(containers_tab, "notify", lambda msg, **kw: notified.append((msg, kw)))

        # Track _do_attach calls (should NOT be called)
        do_attach_called = []
        monkeypatch.setattr(containers_tab, "_do_attach", lambda *args: do_attach_called.append(args))

        # Run _validate_and_attach with custom choice
        await containers_tab._validate_and_attach(
            container,
            ["nonexistent_tool"],
            user=None,
            choice="custom",
        )

        assert len(do_attach_called) == 0
        assert len(notified) == 1
        assert "Command 'nonexistent_tool' not found in container 'test-web'" in notified[0][0]

