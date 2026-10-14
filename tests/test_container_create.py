"""Unit tests for ContainerCreateDialog port, volume, and environment parsing."""

import pytest

from dockdash.modals.container_create import ContainerCreateDialog


def test_parse_ports_empty():
    dialog = ContainerCreateDialog()
    assert dialog._parse_ports("") is None
    assert dialog._parse_ports("   ") is None


def test_parse_ports_standard():
    dialog = ContainerCreateDialog()
    result = dialog._parse_ports("8080:80")
    assert result == {"80/tcp": 8080}


def test_parse_ports_with_protocol():
    dialog = ContainerCreateDialog()
    result = dialog._parse_ports("5353:53/udp")
    assert result == {"53/udp": 5353}


def test_parse_ports_ip_binding():
    dialog = ContainerCreateDialog()
    result = dialog._parse_ports("127.0.0.1:8080:80")
    assert result == {"80/tcp": ("127.0.0.1", 8080)}

    result_udp = dialog._parse_ports("0.0.0.0:5353:53/udp")
    assert result_udp == {"53/udp": ("0.0.0.0", 5353)}


def test_parse_ports_container_only():
    dialog = ContainerCreateDialog()
    assert dialog._parse_ports("80") == {"80/tcp": None}
    assert dialog._parse_ports("80/tcp") == {"80/tcp": None}
    assert dialog._parse_ports("53/udp") == {"53/udp": None}


def test_parse_ports_multiple_and_trailing_commas():
    dialog = ContainerCreateDialog()
    result = dialog._parse_ports("8080:80, 127.0.0.1:3000:3000, 53/udp, ")
    assert result == {
        "80/tcp": 8080,
        "3000/tcp": ("127.0.0.1", 3000),
        "53/udp": None,
    }


def test_parse_ports_invalid_integers():
    dialog = ContainerCreateDialog()
    with pytest.raises(ValueError, match="must be an integer"):
        dialog._parse_ports("abc:80")

    with pytest.raises(ValueError, match="must be an integer"):
        dialog._parse_ports("8080:xyz")


def test_parse_ports_out_of_range():
    dialog = ContainerCreateDialog()
    with pytest.raises(ValueError, match="between 1 and 65535"):
        dialog._parse_ports("70000:80")

    with pytest.raises(ValueError, match="between 1 and 65535"):
        dialog._parse_ports("8080:0")


def test_parse_ports_invalid_protocol():
    dialog = ContainerCreateDialog()
    with pytest.raises(ValueError, match="Invalid protocol"):
        dialog._parse_ports("8080:80/ftp")


def test_parse_ports_malformed_syntax():
    dialog = ContainerCreateDialog()
    with pytest.raises(ValueError, match="Invalid port mapping"):
        dialog._parse_ports("1:2:3:4")

    with pytest.raises(ValueError, match="Invalid port mapping"):
        dialog._parse_ports("8080:")

    with pytest.raises(ValueError, match="Invalid port mapping"):
        dialog._parse_ports(":80")


def test_parse_volumes():
    dialog = ContainerCreateDialog()
    assert dialog._parse_volumes("") is None
    assert dialog._parse_volumes("/data:/app/data") == {
        "/data": {"bind": "/app/data", "mode": "rw"}
    }
    assert dialog._parse_volumes("/data:/app/data:ro, ") == {
        "/data": {"bind": "/app/data", "mode": "ro"}
    }


def test_parse_env():
    dialog = ContainerCreateDialog()
    assert dialog._parse_env("") is None
    assert dialog._parse_env("NODE_ENV=production, PORT=8080, ") == [
        "NODE_ENV=production",
        "PORT=8080",
    ]
