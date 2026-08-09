"""System information, disk usage, and cleanup tab."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Static

from dockdash.docker_client import DockerClient, DockerClientError
from dockdash.modals.confirm_dialog import ConfirmDialog


def _kv(label: str, value: str, label_width: int = 22) -> str:
    return f"  [#8b949e bold]{label:<{label_width}}[/] [#f0f6fc]{value}[/]"


class SystemTab(Vertical):
    """System info, disk usage, and prune actions with arrow-key button traversal."""

    BINDINGS = [
        Binding("left", "focus_prev_button", "Previous", show=False),
        Binding("right", "focus_next_button", "Next", show=False),
        Binding("up", "focus_prev_button", "Previous", show=False),
        Binding("down", "focus_next_button", "Next", show=False),
        Binding("c", "prune_containers", "Prune Containers", show=False),
        Binding("i", "prune_images", "Prune Images", show=False),
        Binding("v", "prune_volumes", "Prune Volumes", show=False),
        Binding("n", "prune_networks", "Prune Networks", show=False),
        Binding("x", "prune_system", "Full Prune", show=False),
    ]

    DEFAULT_CSS = """
    SystemTab {
        height: 1fr;
        background: #0d1117;
    }
    SystemTab .system-scroll {
        height: 1fr;
        padding: 0 1;
    }
    SystemTab .info-section {
        background: #161b22;
        border: solid #30363d;
        padding: 1 2;
        margin: 0 0 1 0;
    }
    SystemTab .cleanup-section {
        background: #161b22;
        border: solid #d29922;
        padding: 1 2;
        margin: 1 0;
        height: auto;
    }
    SystemTab .cleanup-title {
        color: #d29922;
        text-style: bold;
        padding: 0 0 1 0;
    }
    SystemTab .cleanup-grid {
        layout: horizontal;
        height: auto;
        padding: 0;
        margin: 1 0 0 0;
    }
    SystemTab .cleanup-grid Button {
        margin: 0 1 0 0;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._docker = DockerClient()

    def compose(self) -> ComposeResult:
        yield Static(
            "[#79c0ff bold]SYSTEM[/]  [#79c0ff bold]←→↑↓[/]=navigate buttons  "
            "[#79c0ff bold]Enter[/]=run action  "
            "[#484f58]c/i/v/n/x[/]=shortcuts",
            classes="actions-bar",
        )
        with VerticalScroll(classes="system-scroll"):
            # System Info & Disk Usage panel
            with Vertical(classes="info-section"):
                yield Static("", id="system-info")
                yield Static("", id="disk-usage")

            # Prominent Cleanup Actions Panel
            with Vertical(classes="cleanup-section"):
                yield Static(
                    "⟨ CLEANUP ACTIONS ⟩  [#8b949e]Use Arrow Keys or Tab to traverse buttons — Enter to select[/]",
                    classes="cleanup-title",
                )
                with Horizontal(classes="cleanup-grid"):
                    yield Button(
                        "Prune Containers [c]",
                        id="btn-prune-containers",
                        variant="warning",
                    )
                    yield Button(
                        "Prune Images [i]",
                        id="btn-prune-images",
                        variant="warning",
                    )
                    yield Button(
                        "Prune Volumes [v]",
                        id="btn-prune-volumes",
                        variant="warning",
                    )
                    yield Button(
                        "Prune Networks [n]",
                        id="btn-prune-networks",
                        variant="warning",
                    )
                    yield Button(
                        "⚠ Full Prune [x]",
                        id="btn-prune-system",
                        variant="error",
                    )

    def on_show(self) -> None:
        """Focus the first prune button when tab is displayed."""
        try:
            self.query_one("#btn-prune-containers", Button).focus()
        except Exception:
            pass

    async def refresh_data(self) -> None:
        try:
            info = await self._docker.system_info()
            self._render_info(info)
        except DockerClientError as e:
            self.query_one("#system-info", Static).update(
                f"[#f85149]Error loading system info: {e}[/]"
            )

        try:
            usage = await self._docker.disk_usage()
            self._render_usage(usage)
        except DockerClientError as e:
            self.query_one("#disk-usage", Static).update(
                f"[#f85149]Error loading disk usage: {e}[/]"
            )

    def _render_info(self, info: dict) -> None:
        fmt = DockerClient.format_bytes

        lines = [
            "[#3fb9a0 bold]━━ Docker Engine ━━[/]\n",
            _kv("Server Version", info.get("ServerVersion", "N/A")),
            _kv("API Version", info.get("ApiVersion", "N/A") if "ApiVersion" in info else "N/A"),
            _kv("OS / Architecture", f"{info.get('OperatingSystem', 'N/A')} / {info.get('Architecture', 'N/A')}"),
            _kv("Kernel", info.get("KernelVersion", "N/A")),
            _kv("Storage Driver", info.get("Driver", "N/A")),
            _kv("Logging Driver", info.get("LoggingDriver", "N/A")),
            _kv("Cgroup Driver", info.get("CgroupDriver", "N/A")),
            "",
            "[#3fb9a0 bold]━━ Resources ━━[/]\n",
            _kv("CPUs", str(info.get("NCPU", "N/A"))),
            _kv("Total Memory", fmt(info.get("MemTotal", 0))),
            _kv("Containers", f"{info.get('ContainersRunning', 0)} running / "
                             f"{info.get('ContainersPaused', 0)} paused / "
                             f"{info.get('ContainersStopped', 0)} stopped"),
            _kv("Images Total", str(info.get("Images", 0))),
            "",
            "[#3fb9a0 bold]━━ Runtime ━━[/]\n",
            _kv("Docker Root Dir", info.get("DockerRootDir", "N/A")),
            _kv("Daemon Name", info.get("Name", "N/A")),
        ]

        self.query_one("#system-info", Static).update("\n".join(lines))

    def _render_usage(self, usage: dict) -> None:
        fmt = DockerClient.format_bytes
        lines = ["\n[#3fb9a0 bold]━━ Disk Usage Breakdown ━━[/]\n"]

        # Images
        images = usage.get("Images", []) or []
        total_image_size = sum(i.get("Size", 0) for i in images)
        shared = sum(i.get("SharedSize", 0) for i in images)
        lines.append(_kv("Images", f"{len(images)} total, {fmt(total_image_size)} disk ({fmt(shared)} shared)"))

        # Containers
        containers = usage.get("Containers", []) or []
        total_container_size = sum(c.get("SizeRw", 0) for c in containers)
        lines.append(_kv("Containers", f"{len(containers)} total, {fmt(total_container_size)} writable"))

        # Volumes
        volumes = usage.get("Volumes", []) or []
        total_volume_size = sum(v.get("UsageData", {}).get("Size", 0) for v in volumes)
        lines.append(_kv("Volumes", f"{len(volumes)} total, {fmt(total_volume_size)} disk"))

        # Build cache
        cache = usage.get("BuildCache", []) or []
        total_cache = sum(c.get("Size", 0) for c in cache)
        lines.append(_kv("Build Cache", f"{len(cache)} entries, {fmt(total_cache)} disk"))

        # Total
        total = total_image_size + total_container_size + total_volume_size + total_cache
        lines.append(f"\n  [#79c0ff bold]{'TOTAL DISK USAGE':<22}[/] [#f0f6fc bold]{fmt(total)}[/]")

        self.query_one("#disk-usage", Static).update("\n".join(lines))

    # ── Arrow Key Focus Navigation ────────────────────────────────────

    def action_focus_next_button(self) -> None:
        """Traverse to next prune button via Right/Down arrow key."""
        buttons = list(self.query("Button"))
        if not buttons:
            return
        focused = self.app.focused
        if focused in buttons:
            idx = buttons.index(focused)
            next_btn = buttons[(idx + 1) % len(buttons)]
            next_btn.focus()
        else:
            buttons[0].focus()

    def action_focus_prev_button(self) -> None:
        """Traverse to previous prune button via Left/Up arrow key."""
        buttons = list(self.query("Button"))
        if not buttons:
            return
        focused = self.app.focused
        if focused in buttons:
            idx = buttons.index(focused)
            prev_btn = buttons[(idx - 1) % len(buttons)]
            prev_btn.focus()
        else:
            buttons[-1].focus()

    # ── Button Handlers ───────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        actions = {
            "btn-prune-containers": self.action_prune_containers,
            "btn-prune-images": self.action_prune_images,
            "btn-prune-volumes": self.action_prune_volumes,
            "btn-prune-networks": self.action_prune_networks,
            "btn-prune-system": self.action_prune_system,
        }
        action = actions.get(event.button.id)
        if action:
            self.app.call_later(action)

    # ── Prune Actions ─────────────────────────────────────────────────

    async def action_prune_containers(self) -> None:
        def on_confirm(result: bool) -> None:
            if result:
                self.app.call_later(self._do_prune_containers)

        self.app.push_screen(
            ConfirmDialog(
                title="⟨ PRUNE CONTAINERS ⟩",
                message="Remove all stopped containers?",
                confirm_label="Prune Containers",
                danger=True,
            ),
            on_confirm,
        )

    async def _do_prune_containers(self) -> None:
        try:
            result = await self._docker.prune_containers()
            deleted = result.get("ContainersDeleted") or []
            space = result.get("SpaceReclaimed", 0)
            self.notify(
                f"Pruned {len(deleted)} container(s), reclaimed {DockerClient.format_bytes(space)}",
                severity="information",
            )
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_prune_images(self) -> None:
        def on_confirm(result: bool) -> None:
            if result:
                self.app.call_later(self._do_prune_images)

        self.app.push_screen(
            ConfirmDialog(
                title="⟨ PRUNE IMAGES ⟩",
                message="Remove all dangling images?",
                confirm_label="Prune Images",
                danger=True,
            ),
            on_confirm,
        )

    async def _do_prune_images(self) -> None:
        try:
            result = await self._docker.prune_images()
            deleted = result.get("ImagesDeleted") or []
            space = result.get("SpaceReclaimed", 0)
            self.notify(
                f"Pruned {len(deleted)} image(s), reclaimed {DockerClient.format_bytes(space)}",
                severity="information",
            )
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_prune_volumes(self) -> None:
        def on_confirm(result: bool) -> None:
            if result:
                self.app.call_later(self._do_prune_volumes)

        self.app.push_screen(
            ConfirmDialog(
                title="⟨ PRUNE VOLUMES ⟩",
                message="Remove all unused volumes? This cannot be undone!",
                confirm_label="Prune Volumes",
                danger=True,
            ),
            on_confirm,
        )

    async def _do_prune_volumes(self) -> None:
        try:
            result = await self._docker.prune_volumes()
            deleted = result.get("VolumesDeleted") or []
            space = result.get("SpaceReclaimed", 0)
            self.notify(
                f"Pruned {len(deleted)} volume(s), reclaimed {DockerClient.format_bytes(space)}",
                severity="information",
            )
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_prune_networks(self) -> None:
        def on_confirm(result: bool) -> None:
            if result:
                self.app.call_later(self._do_prune_networks)

        self.app.push_screen(
            ConfirmDialog(
                title="⟨ PRUNE NETWORKS ⟩",
                message="Remove all unused networks?",
                confirm_label="Prune Networks",
                danger=True,
            ),
            on_confirm,
        )

    async def _do_prune_networks(self) -> None:
        try:
            result = await self._docker.prune_networks()
            deleted = result.get("NetworksDeleted") or []
            self.notify(
                f"Pruned {len(deleted)} network(s)",
                severity="information",
            )
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")

    async def action_prune_system(self) -> None:
        def on_confirm(result: bool) -> None:
            if result:
                self.app.call_later(self._do_prune_system)

        self.app.push_screen(
            ConfirmDialog(
                title="⟨ FULL SYSTEM PRUNE ⟩",
                message=(
                    "This will remove:\n"
                    "  • All stopped containers\n"
                    "  • All unused images\n"
                    "  • All unused volumes\n"
                    "  • All unused networks\n\n"
                    "This action CANNOT be undone!"
                ),
                confirm_label="Prune Everything",
                danger=True,
            ),
            on_confirm,
        )

    async def _do_prune_system(self) -> None:
        try:
            await self._docker.prune_system()
            self.notify("System pruned successfully", severity="information")
            await self.refresh_data()
        except DockerClientError as e:
            self.notify(str(e), severity="error")
