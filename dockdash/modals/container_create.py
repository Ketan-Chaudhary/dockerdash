"""Full-screen Container Creation Form — responsive 2-column layout."""

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
    """Full-screen responsive container creation form."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "create", "Create Container"),
    ]

    DEFAULT_CSS = """
    ContainerCreateDialog {
        align: center middle;
        background: #0d1117;
    }
    ContainerCreateDialog .form-container {
        width: 100%;
        height: 100%;
        background: #0d1117;
    }
    ContainerCreateDialog .form-header {
        dock: top;
        height: 1;
        background: #161b22;
        color: #79c0ff;
        text-style: bold;
        padding: 0 1;
        border-bottom: solid #30363d;
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
        color: #3fb9a0;
        text-style: bold;
        margin: 1 0 0 0;
    }
    ContainerCreateDialog Label {
        color: #8b949e;
        padding: 0;
        margin: 0;
    }
    ContainerCreateDialog Input {
        margin: 0 0 1 0;
        height: 3;
    }
    ContainerCreateDialog Select {
        margin: 0 0 1 0;
        height: 3;
    }
    ContainerCreateDialog Checkbox {
        margin: 1 2 0 0;
        padding: 0;
    }
    ContainerCreateDialog .form-footer {
        dock: bottom;
        height: 3;
        background: #161b22;
        padding: 0 2;
        border-top: solid #30363d;
        layout: horizontal;
        align: right middle;
    }
    """

    def __init__(self, default_image: str = "") -> None:
        super().__init__()
        self._default_image = default_image

    def compose(self) -> ComposeResult:
        with Vertical(classes="form-container"):
            yield Static(
                "⟨ CREATE CONTAINER ⟩  "
                "[#8b949e]Keys:[/] [#79c0ff bold]Ctrl+S[/] create  "
                "[#79c0ff bold]Esc[/] cancel",
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
        elif event.button.id == "create-btn":
            self.action_create()

    def action_create(self) -> None:
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
