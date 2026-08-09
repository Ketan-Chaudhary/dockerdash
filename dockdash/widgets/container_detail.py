"""Container detail panel widget."""

from __future__ import annotations

import json

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static

from dockdash.docker_client import DockerClient


def _kv(label: str, value: str) -> str:
    """Format a key-value pair with Rich markup."""
    return f"  [#8b949e bold]{label:<16}[/] [#e6edf3]{value}[/]"


class ContainerDetail(VerticalScroll):
    """Displays detailed information about a container."""

    DEFAULT_CSS = """
    ContainerDetail {
        height: 1fr;
        border: solid #30363d;
        background: #161b22;
        padding: 1 1;
    }
    ContainerDetail .detail-section {
        padding: 0 0 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="detail-content")

    def update_detail(self, attrs: dict) -> None:
        """Update the detail view with container attributes."""
        config = attrs.get("Config", {})
        state = attrs.get("State", {})
        network_settings = attrs.get("NetworkSettings", {})
        host_config = attrs.get("HostConfig", {})

        name = attrs.get("Name", "").lstrip("/")
        image = config.get("Image", "")
        status_text, _ = DockerClient.format_status(state.get("Status", "unknown"))

        # Ports
        ports = network_settings.get("Ports", {}) or {}
        port_lines = []
        for cp, bindings in ports.items():
            if bindings:
                for b in bindings:
                    port_lines.append(f"{b.get('HostPort', '?')}->{cp}")
            else:
                port_lines.append(cp)
        port_str = ", ".join(port_lines) if port_lines else "none"

        # Environment
        env = config.get("Env", []) or []
        env_lines = "\n".join(f"    [#8b949e]{e}[/]" for e in env[:20])
        if len(env) > 20:
            env_lines += f"\n    [dim]... and {len(env) - 20} more[/]"

        # Mounts
        mounts = attrs.get("Mounts", []) or []
        mount_lines = "\n".join(
            f"    [#8b949e]{m.get('Source', '?')} → {m.get('Destination', '?')} ({m.get('Mode', 'rw')})[/]"
            for m in mounts
        )

        # Network
        networks = network_settings.get("Networks", {}) or {}
        net_lines = "\n".join(
            f"    [#8b949e]{net_name}: {info.get('IPAddress', 'N/A')}[/]"
            for net_name, info in networks.items()
        )

        # Command
        cmd = config.get("Cmd")
        cmd_str = " ".join(cmd) if cmd else config.get("Entrypoint", [""])[0] if config.get("Entrypoint") else "—"

        # Restart policy
        restart = host_config.get("RestartPolicy", {})
        restart_str = restart.get("Name", "no")
        if restart.get("MaximumRetryCount", 0) > 0:
            restart_str += f" (max {restart['MaximumRetryCount']})"

        content = "\n".join([
            f"[#3fb9a0 bold]━━ Overview ━━[/]",
            _kv("Name", name),
            _kv("ID", attrs.get("Id", "")[:12]),
            _kv("Image", image),
            _kv("Status", status_text),
            _kv("Created", attrs.get("Created", "")[:19]),
            _kv("Started", state.get("StartedAt", "—")[:19]),
            _kv("Command", cmd_str),
            _kv("Restart", restart_str),
            "",
            f"[#3fb9a0 bold]━━ Networking ━━[/]",
            _kv("Ports", port_str),
            f"  [#8b949e bold]Networks[/]",
            net_lines or "    [dim]none[/]",
            "",
            f"[#3fb9a0 bold]━━ Mounts ━━[/]",
            mount_lines or "    [dim]none[/]",
            "",
            f"[#3fb9a0 bold]━━ Environment ━━[/]",
            env_lines or "    [dim]none[/]",
        ])

        self.query_one("#detail-content", Static).update(content)

    def clear(self) -> None:
        self.query_one("#detail-content", Static).update(
            "[dim]Select a container and press Enter to view details[/]"
        )
