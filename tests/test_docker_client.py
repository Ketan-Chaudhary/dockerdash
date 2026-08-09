"""Unit tests for DockerClient formatting and utilities."""

import pytest
from dockdash.docker_client import DockerClient, DockerClientError


def test_format_bytes():
    assert DockerClient.format_bytes(500) == "500.0 B"
    assert DockerClient.format_bytes(1024) == "1.0 KB"
    assert DockerClient.format_bytes(1048576) == "1.0 MB"
    assert DockerClient.format_bytes(1073741824) == "1.0 GB"


def test_format_status():
    text, css = DockerClient.format_status("running")
    assert text == "▸ RUNNING"
    assert css == "status-running"

    text, css = DockerClient.format_status("exited")
    assert text == "■ EXITED"
    assert css == "status-exited"

    text, css = DockerClient.format_status("paused")
    assert text == "‖ PAUSED"
    assert css == "status-paused"

    text, css = DockerClient.format_status("created")
    assert text == "◆ CREATED"
    assert css == "status-created"

    text, css = DockerClient.format_status("unknown_state")
    assert "UNKNOWN_STATE" in text
    assert css == "status-unknown"


def test_docker_client_error():
    err = DockerClientError("Test message")
    assert str(err) == "Test message"
    assert err.original is None
