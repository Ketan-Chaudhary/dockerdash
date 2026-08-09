"""Container creation wizard modal with full configuration options."""

from __future__ import annotations

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


RESTART_POLICIES = [
    ("No restart", "no"),
    ("Always", "always"),
    ("Unless stopped", "unless-stopped"),
    ("On failure", "on-failure"),
]


class ContainerCreateDialog(ModalScreen[dict | None]):
    """Multi-field container creation form.

    Returns a config dict ready for DockerClient.create_container(),
    or None if cancelled.
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, default_image: str = "") -> None:
        super().__init__()
        self._default_image = default_image

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog") as dialog:
            dialog.styles.width = "90%"
            dialog.styles.height = "90%"
            yield Static("⟨ CREATE CONTAINER ⟩", classes="modal-title")

            with VerticalScroll(classes="modal-body"):
                # ── Required ──
                yield Static("[#3fb9a0 bold]━━ Image & Name ━━[/]")
                yield Label("Image [bold](required)[/]")
                yield Input(
                    value=self._default_image,
                    placeholder="e.g. nginx:latest, python:3.12-slim",
                    id="field-image",
                )
                yield Label("Container name")
                yield Input(
                    placeholder="e.g. my-web-server (leave empty for auto)",
                    id="field-name",
                )
                yield Label("Command")
                yield Input(
                    placeholder='e.g. /bin/sh -c "echo hello"',
                    id="field-command",
                )

                # ── Networking ──
                yield Static("")
                yield Static("[#3fb9a0 bold]━━ Networking ━━[/]")
                yield Label("Port mappings  (comma-separated, host:container)")
                yield Input(
                    placeholder="e.g. 8080:80, 3000:3000",
                    id="field-ports",
                )
                yield Label("Network")
                yield Input(
                    placeholder="e.g. bridge, host, my-network (default: bridge)",
                    id="field-network",
                )

                # ── Volumes ──
                yield Static("")
                yield Static("[#3fb9a0 bold]━━ Storage ━━[/]")
                yield Label("Volume mounts  (comma-separated, host:container[:mode])")
                yield Input(
                    placeholder="e.g. /data:/app/data, myvolume:/var/lib/db:ro",
                    id="field-volumes",
                )

                # ── Environment ──
                yield Static("")
                yield Static("[#3fb9a0 bold]━━ Environment ━━[/]")
                yield Label("Environment variables  (comma-separated, KEY=VALUE)")
                yield Input(
                    placeholder="e.g. NODE_ENV=production, DB_HOST=localhost",
                    id="field-env",
                )

                # ── Resources ──
                yield Static("")
                yield Static("[#3fb9a0 bold]━━ Resources & Policy ━━[/]")
                yield Label("Memory limit")
                yield Input(
                    placeholder="e.g. 512m, 1g (leave empty for unlimited)",
                    id="field-memory",
                )
                yield Label("CPU count")
                yield Input(
                    placeholder="e.g. 2 (leave empty for unlimited)",
                    id="field-cpus",
                )
                yield Label("Restart policy")
                yield Select(
                    [(text, value) for text, value in RESTART_POLICIES],
                    value="no",
                    id="field-restart",
                )

                # ── Flags ──
                yield Static("")
                yield Static("[#3fb9a0 bold]━━ Options ━━[/]")
                yield Checkbox("Privileged mode", id="field-privileged")
                yield Checkbox("Auto-remove on exit", id="field-autoremove")

            with Horizontal(classes="modal-footer"):
                yield Button("Cancel", id="cancel-btn")
                yield Button("Create", id="create-btn", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#field-image", Input).focus()

    def _parse_ports(self, raw: str) -> dict | None:
        """Parse '8080:80, 3000:3000' into docker-py port dict."""
        if not raw.strip():
            return None
        ports = {}
        for mapping in raw.split(","):
            mapping = mapping.strip()
            if ":" in mapping:
                parts = mapping.split(":")
                host_port = parts[0].strip()
                container_port = parts[1].strip()
                if "/" not in container_port:
                    container_port += "/tcp"
                ports[container_port] = int(host_port)
            else:
                port = mapping.strip()
                if "/" not in port:
                    port += "/tcp"
                ports[port] = None
        return ports if ports else None

    def _parse_volumes(self, raw: str) -> dict | None:
        """Parse '/data:/app/data, vol:/db:ro' into docker-py volume dict."""
        if not raw.strip():
            return None
        volumes = {}
        for mapping in raw.split(","):
            mapping = mapping.strip()
            parts = mapping.split(":")
            if len(parts) >= 2:
                host = parts[0].strip()
                container = parts[1].strip()
                mode = parts[2].strip() if len(parts) > 2 else "rw"
                volumes[host] = {"bind": container, "mode": mode}
        return volumes if volumes else None

    def _parse_env(self, raw: str) -> list | None:
        """Parse 'KEY=VAL, KEY2=VAL2' into list of strings."""
        if not raw.strip():
            return None
        env = []
        for item in raw.split(","):
            item = item.strip()
            if "=" in item:
                env.append(item)
        return env if env else None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
            return

        image = self.query_one("#field-image", Input).value.strip()
        if not image:
            self.query_one("#field-image", Input).add_class("-invalid")
            self.notify("Image is required", severity="error")
            return

        name = self.query_one("#field-name", Input).value.strip()
        command = self.query_one("#field-command", Input).value.strip()
        ports_raw = self.query_one("#field-ports", Input).value
        volumes_raw = self.query_one("#field-volumes", Input).value
        env_raw = self.query_one("#field-env", Input).value
        network = self.query_one("#field-network", Input).value.strip()
        memory = self.query_one("#field-memory", Input).value.strip()
        cpus = self.query_one("#field-cpus", Input).value.strip()
        restart_sel = self.query_one("#field-restart", Select)
        restart = restart_sel.value if restart_sel.value != Select.BLANK else "no"
        privileged = self.query_one("#field-privileged", Checkbox).value
        auto_remove = self.query_one("#field-autoremove", Checkbox).value

        config: dict = {"image": image}
        if name:
            config["name"] = name
        if command:
            config["command"] = command

        ports = self._parse_ports(ports_raw)
        if ports:
            config["ports"] = ports

        volumes = self._parse_volumes(volumes_raw)
        if volumes:
            config["volumes"] = volumes

        env = self._parse_env(env_raw)
        if env:
            config["environment"] = env

        if network:
            config["network"] = network

        if memory:
            config["mem_limit"] = memory

        if cpus:
            try:
                config["cpu_count"] = int(cpus)
            except ValueError:
                pass

        if restart and restart != "no":
            config["restart_policy"] = {"Name": restart}

        if privileged:
            config["privileged"] = True

        if auto_remove:
            config["auto_remove"] = True

        self.dismiss(config)

    def action_cancel(self) -> None:
        self.dismiss(None)
