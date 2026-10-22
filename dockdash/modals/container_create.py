"""Full-screen Container Creation Form — responsive 2-column layout."""

from __future__ import annotations

import errno
import re
import socket

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    Label,
    Select,
    Static,
)

from dockdash.docker_client import DockerClient

RESTART_POLICIES = [
    ("No restart", "no"),
    ("Always", "always"),
    ("Unless stopped", "unless-stopped"),
    ("On failure", "on-failure"),
]


def is_host_port_in_use(ip: str, port: int, proto: str = "tcp") -> bool:
    """Check if (ip, port) is already bound by an active process on the host."""
    sock_type = socket.SOCK_STREAM if proto.lower() == "tcp" else socket.SOCK_DGRAM
    ips_to_test = [ip] if ip and ip != "0.0.0.0" else ["0.0.0.0", "127.0.0.1"]
    for test_ip in ips_to_test:
        try:
            with socket.socket(socket.AF_INET, sock_type) as s:
                s.bind((test_ip, port))
        except OSError as e:
            if e.errno == errno.EADDRINUSE:
                return True
            elif e.errno == errno.EACCES and proto.lower() == "tcp":
                # Fall back to connect probe for privileged ports (< 1024)
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                        probe.settimeout(0.2)
                        target = test_ip if test_ip != "0.0.0.0" else "127.0.0.1"
                        if probe.connect_ex((target, port)) == 0:
                            return True
                except OSError:
                    pass
    return False


def check_port_conflicts(ports: dict, docker_client: DockerClient | None = None) -> str | None:
    """Pre-flight check for host port conflicts against running containers and local host sockets.

    Args:
        ports: Docker SDK ports dict mapping container_port/proto -> host_spec.
        docker_client: Optional DockerClient instance to query running containers.

    Returns:
        A human-readable conflict description if a conflict is detected, otherwise None.
    """
    if not ports:
        return None

    # 1. Check for duplicate host ports within user's entered mappings
    seen_host_ports: set[tuple[str, int, str]] = set()
    parsed_bindings: list[tuple[str, int, str, str]] = []

    for c_spec, h_spec in ports.items():
        if h_spec is None:
            continue
        c_port, proto = c_spec.split("/") if "/" in c_spec else (c_spec, "tcp")
        proto = proto.lower()

        h_list = h_spec if isinstance(h_spec, list) else [h_spec]
        for item in h_list:
            if isinstance(item, tuple):
                h_ip, h_port = item[0] or "0.0.0.0", int(item[1])
            else:
                h_ip, h_port = "0.0.0.0", int(item)

            key = (h_ip, h_port, proto)
            wildcard_key = ("0.0.0.0", h_port, proto)
            if (
                key in seen_host_ports
                or wildcard_key in seen_host_ports
                or (h_ip == "0.0.0.0" and any(k[1] == h_port and k[2] == proto for k in seen_host_ports))
            ):
                return f"Duplicate host port {h_port}/{proto} specified in port mappings."
            seen_host_ports.add(key)
            parsed_bindings.append((h_ip, h_port, proto, c_port))

    # 2. Check against already running Docker containers
    if docker_client is not None:
        try:
            running_containers = docker_client.client.containers.list(filters={"status": "running"})
            for c in running_containers:
                net_ports = c.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
                for bound_c_spec, bindings in net_ports.items():
                    if not bindings:
                        continue
                    bound_proto = bound_c_spec.split("/")[1].lower() if "/" in bound_c_spec else "tcp"
                    for b in bindings:
                        try:
                            b_port = int(b.get("HostPort", 0))
                        except (ValueError, TypeError):
                            continue
                        b_ip = b.get("HostIp", "0.0.0.0") or "0.0.0.0"

                        for h_ip, h_port, proto, _ in parsed_bindings:
                            if b_port == h_port and bound_proto == proto:
                                if b_ip == "0.0.0.0" or h_ip == "0.0.0.0" or b_ip == h_ip:
                                    c_name = getattr(c, "name", "unknown")
                                    c_short = getattr(c, "short_id", getattr(c, "id", "")[:12])
                                    return (
                                        f"Port {h_port}/{proto} is already in use by running container "
                                        f"'{c_name}' ({c_short})."
                                    )
        except Exception:
            pass

    # 3. Check against local host sockets (socket.bind probe)
    for h_ip, h_port, proto, _ in parsed_bindings:
        if is_host_port_in_use(h_ip, h_port, proto):
            return f"Host port {h_port}/{proto} is already in use by another local process."

    return None



class ContainerCreateDialog(ModalScreen[dict | None]):
    """Full-screen responsive container creation form."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "create", "Create Container"),
    ]

    DEFAULT_CSS = """
    ContainerCreateDialog {
        align: center middle;
        background: #0a0e17;
    }
    ContainerCreateDialog .form-container {
        width: 100%;
        height: 100%;
        background: #0a0e17;
    }
    ContainerCreateDialog .form-header {
        height: 1;
        background: #121824;
        color: #38bdf8;
        text-style: bold;
        padding: 0 1;
        border-bottom: solid #2b384e;
    }
    ContainerCreateDialog .form-body {
        height: 1fr;
        padding: 0 1;
    }
    ContainerCreateDialog .form-columns {
        layout: horizontal;
        height: auto;
    }
    ContainerCreateDialog .form-column {
        width: 1fr;
        min-width: 36;
        padding: 0 1;
    }
    ContainerCreateDialog .form-section-title {
        color: #38bdf8;
        text-style: bold;
        margin: 1 0 0 0;
    }
    ContainerCreateDialog Label {
        color: #cbd5e1;
        padding: 0;
        margin: 0;
    }
    ContainerCreateDialog Input {
        margin: 0 0 1 0;
        height: 3;
    }
    ContainerCreateDialog Select {
        margin: 0 0 1 0;
        height: auto;
        border: none;
        background: transparent;
        padding: 0;
    }
    ContainerCreateDialog SelectCurrent {
        background: #121824;
        border: solid #2b384e;
        color: #f8fafc;
        height: 3;
        padding: 0 1;
    }
    ContainerCreateDialog Select:focus > SelectCurrent,
    ContainerCreateDialog Select.-expanded > SelectCurrent {
        border: solid #38bdf8;
    }
    ContainerCreateDialog SelectOverlay {
        background: #121824;
        border: solid #38bdf8;
        max-height: 8;
    }
    ContainerCreateDialog Checkbox {
        margin: 1 2 0 0;
        padding: 0;
    }
    ContainerCreateDialog .form-footer {
        height: auto;
        min-height: 4;
        background: #121824;
        padding: 0 2;
        border-top: solid #2b384e;
        layout: horizontal;
        align: right middle;
    }
    ContainerCreateDialog .form-footer Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        default_image: str = "",
        docker_client: DockerClient | None = None,
    ) -> None:
        super().__init__()
        self._default_image = default_image
        self._docker = docker_client if docker_client is not None else DockerClient()

    def _check_port_conflicts(self, ports: dict) -> str | None:
        """Run pre-flight check against running containers and host socket bindings."""
        return check_port_conflicts(ports, self._docker)

    def compose(self) -> ComposeResult:
        with Vertical(classes="form-container"):
            yield Static(
                "⟨ CREATE CONTAINER ⟩  "
                "[#cbd5e1]Keys:[/] [#38bdf8 bold]Ctrl+S[/] create  "
                "[#38bdf8 bold]Esc[/] cancel",
                classes="form-header",
            )

            with VerticalScroll(classes="form-body"):
                with Horizontal(classes="form-columns"):
                    # ── Left Column: Basic Info & Environment ──
                    with Vertical(classes="form-column"):
                        yield Static("━━ Basic Configuration ━━", classes="form-section-title")
                        yield Label("Image [bold cyan](required)[/]")
                        yield Input(
                            value=self._default_image,
                            placeholder="e.g. nginx:latest, python:3.12-slim",
                            id="field-image",
                        )

                        yield Label("Container Name")
                        yield Input(
                            placeholder="e.g. my-web-server (optional)",
                            id="field-name",
                        )

                        yield Label("Command")
                        yield Input(
                            placeholder='e.g. bash or /bin/sh -c "echo hi"',
                            id="field-command",
                        )

                        yield Static("━━ Environment & Flags ━━", classes="form-section-title")
                        yield Label("Environment Variables (KEY=VALUE, ...)")
                        yield Input(
                            placeholder="e.g. NODE_ENV=production, PORT=8080",
                            id="field-env",
                        )

                        with Horizontal():
                            yield Checkbox("Privileged Mode", id="field-privileged")
                            yield Checkbox("Auto-Remove on Exit", id="field-autoremove")

                    # ── Right Column: Policy, Resources & Storage ──
                    with Vertical(classes="form-column"):
                        yield Static("━━ Policy & Limits ━━", classes="form-section-title")
                        yield Label("Restart Policy")
                        yield Select(
                            [(text, value) for text, value in RESTART_POLICIES],
                            value="no",
                            allow_blank=False,
                            id="field-restart",
                        )

                        with Horizontal():
                            with Vertical(classes="form-column"):
                                yield Label("Memory Limit")
                                yield Input(
                                    placeholder="e.g. 512m, 1g",
                                    id="field-memory",
                                )
                            with Vertical(classes="form-column"):
                                yield Label("CPU Count")
                                yield Input(
                                    placeholder="e.g. 2",
                                    id="field-cpus",
                                )

                        yield Static("━━ Network & Storage ━━", classes="form-section-title")
                        yield Label("Port Mappings (host:container, ...)")
                        yield Input(
                            placeholder="e.g. 8080:80, 3000:3000",
                            id="field-ports",
                        )

                        yield Label("Volume Mounts (host:container[:mode], ...)")
                        yield Input(
                            placeholder="e.g. /data:/app/data, vol:/db:ro",
                            id="field-volumes",
                        )

                        yield Label("Network")
                        yield Input(
                            placeholder="e.g. bridge, host, my-net (default: bridge)",
                            id="field-network",
                        )

            # ── Docked Bottom Footer ──
            with Horizontal(classes="form-footer"):
                yield Button("Cancel [Esc]", id="cancel-btn")
                yield Button("Create Container [Ctrl+S]", id="create-btn", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#field-image", Input).focus()

    def _parse_ports(self, raw: str) -> dict | None:
        """Parse port mappings string into Docker SDK ports dict.

        Supported formats (comma-separated):
          - "8080:80"                  -> {'80/tcp': 8080}
          - "8080:80/udp"              -> {'80/udp': 8080}
          - "127.0.0.1:8080:80"        -> {'80/tcp': ('127.0.0.1', 8080)}
          - "127.0.0.1:8080:80/udp"    -> {'80/udp': ('127.0.0.1', 8080)}
          - "80"                       -> {'80/tcp': None}
          - "80/udp"                   -> {'80/udp': None}

        Raises ValueError on malformed syntax or out-of-range port numbers.
        """
        if not raw.strip():
            return None

        def _validate_port(port_str: str) -> int:
            try:
                port_num = int(port_str)
            except ValueError:
                raise ValueError(f"Port '{port_str}' must be an integer.") from None
            if not (1 <= port_num <= 65535):
                raise ValueError(f"Port {port_num} must be between 1 and 65535.")
            return port_num

        def _split_container_port_proto(spec: str) -> tuple[int, str]:
            if "/" in spec:
                p_str, proto = spec.split("/", 1)
                proto = proto.lower().strip()
                if proto not in ("tcp", "udp", "sctp"):
                    raise ValueError(f"Invalid protocol '{proto}'. Must be tcp, udp, or sctp.")
            else:
                p_str, proto = spec, "tcp"
            return _validate_port(p_str.strip()), proto

        ports: dict = {}
        for mapping in raw.split(","):
            mapping = mapping.strip()
            if not mapping:
                continue

            parts = [p.strip() for p in mapping.split(":")]
            if len(parts) == 1:
                c_port, proto = _split_container_port_proto(parts[0])
                ports[f"{c_port}/{proto}"] = None
            elif len(parts) == 2:
                if not parts[0] or not parts[1]:
                    raise ValueError(f"Invalid port mapping '{mapping}'.")
                h_port = _validate_port(parts[0])
                c_port, proto = _split_container_port_proto(parts[1])
                ports[f"{c_port}/{proto}"] = h_port
            elif len(parts) == 3:
                host_ip, h_str, c_spec = parts
                if not host_ip or not h_str or not c_spec:
                    raise ValueError(f"Invalid port mapping '{mapping}'.")
                h_port = _validate_port(h_str)
                c_port, proto = _split_container_port_proto(c_spec)
                ports[f"{c_port}/{proto}"] = (host_ip, h_port)
            else:
                raise ValueError(
                    f"Invalid port mapping '{mapping}'. Expected 'host:container' or 'ip:host:container'."
                )

        return ports if ports else None

    def _parse_volumes(self, raw: str) -> dict | None:
        """Parse volume mappings string into Docker SDK volumes dict.

        Supported formats (comma-separated):
          - "/host/path:/container/path"
          - "/host/path:/container/path:ro"
          - "volume_name:/container/path:rw"

        Raises ValueError on malformed syntax, empty paths, or invalid modes.
        """
        if not raw.strip():
            return None
        volumes = {}
        for mapping in raw.split(","):
            mapping = mapping.strip()
            if not mapping:
                continue
            parts = [p.strip() for p in mapping.split(":")]
            if len(parts) < 2 or len(parts) > 3:
                raise ValueError(
                    f"Invalid volume mapping '{mapping}'. Expected 'host:container' or 'host:container:ro|rw'."
                )
            host, container = parts[0], parts[1]
            if not host or not container:
                raise ValueError(
                    f"Invalid volume mapping '{mapping}'. Host and container paths cannot be empty."
                )
            mode = parts[2].lower() if len(parts) == 3 else "rw"
            if mode not in ("rw", "ro", "z", "Z"):
                raise ValueError(
                    f"Invalid volume mode '{parts[2]}'. Must be 'ro' or 'rw'."
                )
            volumes[host] = {"bind": container, "mode": mode}
        return volumes if volumes else None

    def _parse_env(self, raw: str) -> list | None:
        """Parse environment variables into a list of 'KEY=value' strings.

        Raises ValueError if an entry has an empty key (e.g. '=value').
        """
        if not raw.strip():
            return None
        env = []
        for item in raw.split(","):
            item = item.strip()
            if not item:
                continue
            if "=" in item:
                k, _ = item.split("=", 1)
                if not k.strip():
                    raise ValueError(f"Invalid environment variable '{item}'. Key cannot be empty.")
                env.append(item)
            else:
                if not item.strip():
                    raise ValueError(f"Invalid environment variable '{item}'. Key cannot be empty.")
                env.append(item)
        return env if env else None

    def on_input_changed(self, event: Input.Changed) -> None:
        event.input.remove_class("-invalid")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
            return
        elif event.button.id == "create-btn":
            self.action_create()

    def action_create(self) -> None:
        image_input = self.query_one("#field-image", Input)
        image = image_input.value.strip()
        if not image:
            image_input.add_class("-invalid")
            self.notify("Image is required", severity="error")
            return
        image_input.remove_class("-invalid")

        name = self.query_one("#field-name", Input).value.strip()
        command = self.query_one("#field-command", Input).value.strip()

        ports_input = self.query_one("#field-ports", Input)
        try:
            ports = self._parse_ports(ports_input.value)
            ports_input.remove_class("-invalid")
        except ValueError as e:
            ports_input.add_class("-invalid")
            self.notify(str(e), severity="error")
            return

        if ports:
            conflict = self._check_port_conflicts(ports)
            if conflict:
                ports_input.add_class("-invalid")
                self.notify(f"Port conflict: {conflict}", severity="error")
                return

        volumes_input = self.query_one("#field-volumes", Input)
        try:
            volumes = self._parse_volumes(volumes_input.value)
            volumes_input.remove_class("-invalid")
        except ValueError as e:
            volumes_input.add_class("-invalid")
            self.notify(str(e), severity="error")
            return

        env_input = self.query_one("#field-env", Input)
        try:
            env = self._parse_env(env_input.value)
            env_input.remove_class("-invalid")
        except ValueError as e:
            env_input.add_class("-invalid")
            self.notify(str(e), severity="error")
            return

        network = self.query_one("#field-network", Input).value.strip()

        memory_input = self.query_one("#field-memory", Input)
        memory = memory_input.value.strip()
        if memory:
            if not re.match(r"^\d+([bkmgBKMG](?:b|B)?)?$", memory):
                memory_input.add_class("-invalid")
                self.notify(f"Invalid memory limit '{memory}'. Example: 512m, 1g, 2gb", severity="error")
                return
            memory_input.remove_class("-invalid")

        cpus_input = self.query_one("#field-cpus", Input)
        cpus = cpus_input.value.strip()
        if cpus:
            try:
                cpu_val = int(cpus)
                if cpu_val <= 0:
                    raise ValueError
                cpus_input.remove_class("-invalid")
            except ValueError:
                cpus_input.add_class("-invalid")
                self.notify(f"CPUs must be a positive integer, got '{cpus}'.", severity="error")
                return

        restart_sel = self.query_one("#field-restart", Select)
        restart = restart_sel.value if restart_sel.value != Select.BLANK else "no"
        privileged = self.query_one("#field-privileged", Checkbox).value
        auto_remove = self.query_one("#field-autoremove", Checkbox).value

        config: dict = {"image": image}
        if name:
            config["name"] = name
        if command:
            config["command"] = command
        if ports:
            config["ports"] = ports
        if volumes:
            config["volumes"] = volumes
        if env:
            config["environment"] = env
        if network:
            config["network"] = network
        if memory:
            config["mem_limit"] = memory
        if cpus:
            config["cpu_count"] = int(cpus)
        if restart and restart != "no":
            config["restart_policy"] = {"Name": restart}
        if privileged:
            config["privileged"] = True
        if auto_remove:
            config["auto_remove"] = True

        self.dismiss(config)

    def action_cancel(self) -> None:
        self.dismiss(None)

