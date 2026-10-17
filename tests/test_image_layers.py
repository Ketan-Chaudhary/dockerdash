"""Unit tests for ImageLayersDialog and layer inspection."""

from __future__ import annotations

import pytest

from dockdash.app import DockerDashApp
from dockdash.modals.image_layers import (
    ImageLayersDialog,
    clean_command,
    format_size,
    make_proportion_bar,
)
from dockdash.screens.images import ImagesTab


def test_clean_command_variations():
    """Verify various Dockerfile commands are cleaned and formatted properly."""
    assert clean_command("") == "—"
    assert clean_command(None) == "—"

    # Nop removal
    assert clean_command("/bin/sh -c #(nop)  ENV NGINX_VERSION=1.27.2") == "ENV NGINX_VERSION=1.27.2"
    assert clean_command("/bin/sh -c #(nop)  CMD [\"nginx\" \"-g\" \"daemon off;\"]") == "CMD [\"nginx\" \"-g\" \"daemon off;\"]"
    assert clean_command("/bin/sh -c #(nop)  EXPOSE 80") == "EXPOSE 80"

    # RUN command prefix
    assert clean_command("/bin/sh -c set -x && apk add nginx") == "RUN set -x && apk add nginx"
    assert clean_command("/bin/sh -c set -x && apk add nginx # buildkit") == "RUN set -x && apk add nginx"

    # Buildkit comment strip
    assert clean_command("ADD file:abc in / # buildkit") == "ADD file:abc in /"


def test_format_size():
    """Verify human readable byte size formatting."""
    assert format_size(0) == "0 B"
    assert format_size(-10) == "0 B"
    assert format_size(1024) == "1.00 KB"
    assert format_size(1024 * 1024) == "1.00 MB"
    assert format_size(52428800) == "50.00 MB"


def test_make_proportion_bar():
    """Verify visual proportion bar generation."""
    empty_bar = make_proportion_bar(0, 100)
    assert "0.0%" in empty_bar.plain

    half_bar = make_proportion_bar(50, 100, width=10)
    assert "50.0%" in half_bar.plain
    assert "█████" in half_bar.plain


@pytest.mark.asyncio
async def test_image_layers_dialog_interactions():
    """Test ImageLayersDialog table population, navigation, order toggling, and copy."""
    dummy_layers = [
        {
            "Id": "sha256:toplayer123456789",
            "Created": 1700000000,
            "CreatedBy": "/bin/sh -c apt-get update && apt-get install -y curl",
            "Size": 60 * 1024 * 1024,
            "Comment": "buildkit",
        },
        {
            "Id": "<missing>",
            "Created": 1700000000,
            "CreatedBy": "/bin/sh -c #(nop)  ENV APP_ENV=production",
            "Size": 0,
            "Comment": "",
        },
        {
            "Id": "sha256:baselayer987654321",
            "Created": 1699999000,
            "CreatedBy": "ADD alpine.tar.gz /",
            "Size": 10 * 1024 * 1024,
            "Comment": "",
        },
    ]

    app = DockerDashApp()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        dialog = ImageLayersDialog(image_name="test-image:latest", raw_layers=dummy_layers)
        app.push_screen(dialog)
        await pilot.pause(0.2)

        assert app.screen.__class__.__name__ == "ImageLayersDialog"

        # Check that parsed layers exist and default to base_first
        assert len(dialog._parsed_layers) == 3
        # In base-first order, the last item in dummy_layers (base layer) is #1
        assert dialog._parsed_layers[0]["command"] == "ADD alpine.tar.gz /"
        assert dialog._parsed_layers[0]["step"] == 1

        # Test toggle order
        await pilot.press("o")
        await pilot.pause(0.1)
        # Now top layer is #1
        assert "apt-get" in dialog._parsed_layers[0]["command"]

        # Test navigation
        await pilot.press("down")
        await pilot.pause(0.1)

        # Test copy command
        await pilot.press("c")
        await pilot.pause(0.1)

        # Test close on escape
        await pilot.press("escape")
        await pilot.pause(0.1)
        assert app.screen.__class__.__name__ != "ImageLayersDialog"


@pytest.mark.asyncio
async def test_images_tab_l_key_triggers_layers_modal(monkeypatch):
    """Verify pressing 'l' on ImagesTab queries image_history and opens ImageLayersDialog."""
    app = DockerDashApp()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        # Switch to images tab
        app.action_tab_2()
        await pilot.pause(0.2)

        images_tab = app.query_one("#images-tab", ImagesTab)
        # Mock _get_selected_image and image_history
        monkeypatch.setattr(
            images_tab,
            "_get_selected_image",
            lambda: {"id": "123456", "full_id": "sha256:123456", "repository": "demo", "tag": "latest"},
        )
        async def fake_history(full_id):
            return [
                {"Id": "123", "Created": 1700000000, "CreatedBy": "CMD [\"sh\"]", "Size": 0, "Comment": ""}
            ]

        monkeypatch.setattr(images_tab._docker, "image_history", fake_history)

        # Trigger layers action via 'l'
        await pilot.press("l")
        await pilot.pause(0.2)

        assert app.screen.__class__.__name__ == "ImageLayersDialog"
        await pilot.press("escape")
        await pilot.pause(0.1)
        assert app.screen.__class__.__name__ != "ImageLayersDialog"
