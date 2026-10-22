import socket
from unittest.mock import MagicMock

import pytest

from dockdash.modals.container_create import (
    ContainerCreateDialog,
    check_port_conflicts,
    is_host_port_in_use,
)


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


def test_parse_volumes_invalid():
    dialog = ContainerCreateDialog()
    with pytest.raises(ValueError, match="Invalid volume mapping"):
        dialog._parse_volumes("/data")

    with pytest.raises(ValueError, match="cannot be empty"):
        dialog._parse_volumes(":/app/data")

    with pytest.raises(ValueError, match="cannot be empty"):
        dialog._parse_volumes("/data:")

    with pytest.raises(ValueError, match="Invalid volume mode"):
        dialog._parse_volumes("/data:/app/data:invalid_mode")

    with pytest.raises(ValueError, match="Invalid volume mapping"):
        dialog._parse_volumes("/data:/app/data:ro:extra")


def test_parse_env_invalid():
    dialog = ContainerCreateDialog()
    with pytest.raises(ValueError, match="Key cannot be empty"):
        dialog._parse_env("=value")


def test_is_host_port_in_use():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
        assert is_host_port_in_use("127.0.0.1", port, "tcp") is True

    # High ephemeral port that is not in use
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        free_port = probe.getsockname()[1]
    assert is_host_port_in_use("127.0.0.1", free_port, "tcp") is False


def test_check_port_conflicts_duplicate_mappings():
    # Duplicate host port 8080
    ports = {"80/tcp": 8080, "8080/tcp": 8080}
    conflict = check_port_conflicts(ports)
    assert conflict is not None
    assert "Duplicate host port 8080/tcp" in conflict

    # Wildcard vs specific IP duplicate
    ports_ip = {"80/tcp": 8080, "443/tcp": ("0.0.0.0", 8080)}
    assert "Duplicate host port 8080/tcp" in (check_port_conflicts(ports_ip) or "")


def test_check_port_conflicts_running_container():
    mock_docker = MagicMock()
    mock_container = MagicMock()
    mock_container.name = "web-prod"
    mock_container.short_id = "abcd1234efgh"
    mock_container.attrs = {
        "NetworkSettings": {
            "Ports": {
                "80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]
            }
        }
    }
    mock_docker.client.containers.list.return_value = [mock_container]

    ports = {"80/tcp": 8080}
    conflict = check_port_conflicts(ports, docker_client=mock_docker)
    assert conflict is not None
    assert "already in use by running container 'web-prod' (abcd1234efgh)" in conflict


def test_check_port_conflicts_local_host_socket(monkeypatch):
    # Mock is_host_port_in_use to return True for 8080
    monkeypatch.setattr(
        "dockdash.modals.container_create.is_host_port_in_use",
        lambda ip, port, proto: port == 8080,
    )
    ports = {"80/tcp": 8080}
    conflict = check_port_conflicts(ports)
    assert conflict is not None
    assert "Host port 8080/tcp is already in use by another local process" in conflict


