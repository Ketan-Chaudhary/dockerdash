"""Comprehensive interactive UI and unit tests for error handling across all input forms."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from textual.widgets import Input

from dockdash.app import DockerDashApp
from dockdash.modals.container_create import ContainerCreateDialog
from dockdash.modals.dockerfile_editor import DockerfileEditorDialog
from dockdash.screens.containers import ContainersTab
from dockdash.screens.images import ImagesTab
from dockdash.screens.networks import NetworksTab
from dockdash.screens.volumes import VolumesTab


@pytest.mark.asyncio
async def test_container_create_validation_flows():
    """Verify ContainerCreateDialog highlights invalid fields and blocks submission."""
    app = DockerDashApp()
    app._connected = True
    async with app.run_test(size=(120, 40)) as pilot:
        dialog = ContainerCreateDialog()
        app.push_screen(dialog)
        await pilot.pause()

        # 1. Empty image
        dialog.action_create()
        await pilot.pause()
        assert app.screen == dialog
        assert dialog.query_one("#field-image", Input).has_class("-invalid")

        # Set valid image
        dialog.query_one("#field-image", Input).value = "nginx:alpine"
        await pilot.pause()
        assert not dialog.query_one("#field-image", Input).has_class("-invalid")

        # 2. Invalid CPUs (non-numeric)
        dialog.query_one("#field-cpus", Input).value = "two"
        await pilot.pause()
        dialog.action_create()
        await pilot.pause()
        assert app.screen == dialog
        assert dialog.query_one("#field-cpus", Input).has_class("-invalid")

        # Invalid CPUs (zero or negative)
        dialog.query_one("#field-cpus", Input).value = "0"
        await pilot.pause()
        await pilot.pause()  # extra drain for Input.Changed on slower runners
        dialog.action_create()
        await pilot.pause()
        await pilot.pause()
        assert app.screen == dialog
        assert dialog.query_one("#field-cpus", Input).has_class("-invalid")

        # Fix CPUs
        dialog.query_one("#field-cpus", Input).value = "2"
        await pilot.pause()

        # 3. Invalid memory format
        dialog.query_one("#field-memory", Input).value = "512mb_bad"
        await pilot.pause()
        dialog.action_create()
        await pilot.pause()
        assert app.screen == dialog
        assert dialog.query_one("#field-memory", Input).has_class("-invalid")

        # Fix memory
        dialog.query_one("#field-memory", Input).value = "512m"
        await pilot.pause()

        # 4. Invalid volume mapping (missing container target)
        dialog.query_one("#field-volumes", Input).value = "/tmp/host"
        await pilot.pause()
        dialog.action_create()
        await pilot.pause()
        assert app.screen == dialog
        assert dialog.query_one("#field-volumes", Input).has_class("-invalid")

        # Fix volume
        dialog.query_one("#field-volumes", Input).value = "/tmp/host:/app:ro"
        await pilot.pause()

        # 5. Invalid env variable (empty key)
        dialog.query_one("#field-env", Input).value = "=value"
        await pilot.pause()
        dialog.action_create()
        await pilot.pause()
        assert app.screen == dialog
        assert dialog.query_one("#field-env", Input).has_class("-invalid")

        # Fix env
        dialog.query_one("#field-env", Input).value = "NODE_ENV=production"
        await pilot.pause()

        # Now all valid -> create succeeds and dialog dismisses
        dialog.action_create()
        await pilot.pause()
        assert app.screen != dialog


@pytest.mark.asyncio
async def test_container_create_port_conflict_validation():
    """Verify ContainerCreateDialog flags port conflicts and prevents submission."""
    mock_docker = AsyncMock()
    mock_docker.client = MagicMock()
    mock_container = MagicMock()
    mock_container.name = "active-nginx"
    mock_container.short_id = "112233445566"
    mock_container.attrs = {
        "NetworkSettings": {
            "Ports": {
                "80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]
            }
        }
    }
    mock_docker.client.containers.list.return_value = [mock_container]

    app = DockerDashApp()
    app._connected = True
    async with app.run_test(size=(120, 40)) as pilot:
        dialog = ContainerCreateDialog(
            default_image="nginx:alpine", docker_client=mock_docker
        )
        app.push_screen(dialog)
        await pilot.pause()

        ports_input = dialog.query_one("#field-ports", Input)

        # 1. Duplicate host port in form
        ports_input.value = "8080:80, 8080:8080"
        await pilot.pause()
        dialog.action_create()
        await pilot.pause()
        assert app.screen == dialog
        assert ports_input.has_class("-invalid")

        # Clear invalid state on edit
        ports_input.value = "8080:80"
        await pilot.pause()
        assert not ports_input.has_class("-invalid")

        # 2. Port conflict with already running container
        dialog.action_create()
        await pilot.pause()
        assert app.screen == dialog
        assert ports_input.has_class("-invalid")

        # 3. Clean non-conflicting port
        ports_input.value = "9999:80"
        await pilot.pause()
        assert not ports_input.has_class("-invalid")



@pytest.mark.asyncio
async def test_dockerfile_editor_validation_flows(tmp_path):
    """Verify DockerfileEditorDialog validates path, content, and tag format."""
    app = DockerDashApp()
    app._connected = True
    async with app.run_test(size=(120, 40)) as pilot:
        editor = DockerfileEditorDialog(content="FROM alpine:latest\nCMD ['sh']")
        app.push_screen(editor)
        await pilot.pause()

        # 1. Path is a directory
        editor.query_one("#file-path", Input).value = str(tmp_path)
        editor.action_save()
        await pilot.pause()
        assert app.screen == editor

        # 2. Build with empty content
        file_path = str(tmp_path / "Dockerfile")
        editor.query_one("#file-path", Input).value = file_path
        # Clear editor content
        from textual.widgets import TextArea

        editor.query_one("#dockerfile-editor", TextArea).text = "   "
        editor._do_build()
        await pilot.pause()
        assert app.screen == editor

        # 3. Build with invalid tag format (contains spaces)
        editor.query_one("#dockerfile-editor", TextArea).text = "FROM alpine:latest"
        editor.query_one("#build-tag", Input).value = "bad tag with spaces"
        editor._do_build()
        await pilot.pause()
        assert app.screen == editor

        # 4. Valid build
        editor.query_one("#build-tag", Input).value = "valid-tag:1.0"
        editor._do_build()
        await pilot.pause()
        assert app.screen != editor


@pytest.mark.asyncio
async def test_images_tab_pull_and_tag_validation():
    """Verify images tab pull parsing and tag validation."""
    tab = ImagesTab()
    mock_docker = AsyncMock()
    tab._docker = mock_docker
    tab.refresh_data = AsyncMock()

    notifications = []
    tab.notify = lambda msg, **kwargs: notifications.append((msg, kwargs.get("severity")))

    # 1. Pull with empty spec
    await tab._do_pull("   ")
    assert any("required" in msg.lower() for msg, sev in notifications if sev == "error")

    # 2. Pull with private registry with port
    mock_docker.pull_image.reset_mock()
    await tab._do_pull("registry.example.com:5000/my-org/my-app:v1.2")
    mock_docker.pull_image.assert_awaited_once_with(
        "registry.example.com:5000/my-org/my-app", "v1.2"
    )

    # 3. Pull with private registry with port, no tag -> default latest
    mock_docker.pull_image.reset_mock()
    await tab._do_pull("registry.example.com:5000/my-org/my-app")
    mock_docker.pull_image.assert_awaited_once_with(
        "registry.example.com:5000/my-org/my-app", "latest"
    )

    # 4. Tag with spaces in repo
    mock_docker.tag_image.reset_mock()
    notifications.clear()
    await tab._do_tag("img-123", "bad repo", "latest")
    mock_docker.tag_image.assert_not_called()
    assert any("spaces not allowed" in msg.lower() for msg, sev in notifications)

    # 5. Tag with spaces in tag
    mock_docker.tag_image.reset_mock()
    notifications.clear()
    await tab._do_tag("img-123", "validrepo", "v1 .0")
    mock_docker.tag_image.assert_not_called()
    assert any("spaces not allowed" in msg.lower() for msg, sev in notifications)


@pytest.mark.asyncio
async def test_network_and_volume_empty_name_handling():
    """Verify networks and volumes do_create guard against empty inputs."""
    # Networks
    net_tab = NetworksTab()
    mock_net_docker = AsyncMock()
    net_tab._docker = mock_net_docker
    net_notifications = []
    net_tab.notify = lambda msg, **kwargs: net_notifications.append(
        (msg, kwargs.get("severity"))
    )

    await net_tab._do_create("   ", "bridge")
    mock_net_docker.create_network.assert_not_called()
    assert any("required" in msg.lower() for msg, sev in net_notifications if sev == "error")

    # Volumes
    vol_tab = VolumesTab()
    mock_vol_docker = AsyncMock()
    vol_tab._docker = mock_vol_docker
    vol_notifications = []
    vol_tab.notify = lambda msg, **kwargs: vol_notifications.append(
        (msg, kwargs.get("severity"))
    )

    await vol_tab._do_create("   ", "local")
    mock_vol_docker.create_volume.assert_not_called()
    assert any("required" in msg.lower() for msg, sev in vol_notifications if sev == "error")


@pytest.mark.asyncio
async def test_container_rename_empty_name_handling():
    """Verify containers do_rename guards against empty new name."""
    con_tab = ContainersTab()
    mock_docker = AsyncMock()
    con_tab._docker = mock_docker
    notifications = []
    con_tab.notify = lambda msg, **kwargs: notifications.append(
        (msg, kwargs.get("severity"))
    )

    await con_tab._do_rename("cid-123", "   ")
    mock_docker.rename_container.assert_not_called()
    assert any("cannot be empty" in msg.lower() for msg, sev in notifications if sev == "error")
