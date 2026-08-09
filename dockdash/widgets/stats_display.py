"""Live container stats display widget."""

from __future__ import annotations

from rich.text import Text

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from dockdash.docker_client import DockerClient


def _bar(percent: float, width: int = 30, color: str = "#58a6ff") -> str:
    """Create a horizontal bar visualization."""
    filled = int(width * percent / 100)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    return f"[{color}]{bar}[/] {percent:.1f}%"


def _format_bytes(b: int) -> str:
    return DockerClient.format_bytes(b)


class StatsDisplay(Vertical):
    """Displays live container resource stats."""

    DEFAULT_CSS = """
    StatsDisplay {
        height: auto;
        min-height: 12;
        border: solid #30363d;
        background: #161b22;
        padding: 1 2;
    }
    StatsDisplay .stats-title {
        color: #79c0ff;
        text-style: bold;
        padding: 0 0 1 0;
    }
    StatsDisplay .stats-row {
        height: 1;
        padding: 0;
    }
    """

    def __init__(self, container_name: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._container_name = container_name

    def compose(self) -> ComposeResult:
        yield Static(
            f"[bold]⟨ STATS ⟩[/]  {self._container_name}",
            classes="stats-title",
        )
        yield Static("", id="stat-cpu", classes="stats-row")
        yield Static("", id="stat-mem", classes="stats-row")
        yield Static("", id="stat-net", classes="stats-row")
        yield Static("", id="stat-block", classes="stats-row")
        yield Static("", id="stat-pids", classes="stats-row")

    def update_stats(self, stats: dict) -> None:
        """Update the display with parsed stats data."""
        cpu = stats.get("cpu_percent", 0.0)
        cpu_color = "#3fb950" if cpu < 50 else "#d29922" if cpu < 80 else "#f85149"
        self.query_one("#stat-cpu", Static).update(
            f"  [#79c0ff bold]CPU    [/]  {_bar(cpu, 30, cpu_color)}"
        )

        mem_pct = stats.get("mem_percent", 0.0)
        mem_used = _format_bytes(stats.get("mem_usage", 0))
        mem_limit = _format_bytes(stats.get("mem_limit", 0))
        mem_color = "#3fb950" if mem_pct < 50 else "#d29922" if mem_pct < 80 else "#f85149"
        self.query_one("#stat-mem", Static).update(
            f"  [#79c0ff bold]MEMORY [/]  {_bar(mem_pct, 30, mem_color)}  ({mem_used} / {mem_limit})"
        )

        net_rx = _format_bytes(stats.get("net_rx", 0))
        net_tx = _format_bytes(stats.get("net_tx", 0))
        self.query_one("#stat-net", Static).update(
            f"  [#79c0ff bold]NET I/O[/]  [#3fb9a0]▼ {net_rx}[/]  [#d29922]▲ {net_tx}[/]"
        )

        blk_r = _format_bytes(stats.get("block_read", 0))
        blk_w = _format_bytes(stats.get("block_write", 0))
        self.query_one("#stat-block", Static).update(
            f"  [#79c0ff bold]DISK   [/]  [#3fb9a0]R {blk_r}[/]  [#d29922]W {blk_w}[/]"
        )

        pids = stats.get("pids", 0)
        self.query_one("#stat-pids", Static).update(
            f"  [#79c0ff bold]PIDS   [/]  [#e6edf3]{pids}[/]"
        )

    def show_error(self, message: str) -> None:
        """Show an error message in place of stats."""
        self.query_one("#stat-cpu", Static).update(
            f"  [#f85149]{message}[/]"
        )
        for sid in ["#stat-mem", "#stat-net", "#stat-block", "#stat-pids"]:
            self.query_one(sid, Static).update("")
