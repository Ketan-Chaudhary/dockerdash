"""Container and stack live log viewer screen with real-time streaming, search, and filtering."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, RichLog, Static
from textual.worker import get_current_worker

if TYPE_CHECKING:
    from dockdash.docker_client import DockerClient


class LogViewerScreen(ModalScreen[None]):
    """Full-screen live log viewer screen with search, auto-scroll, and controls.

    Keybindings:
        Escape / q: Close modal (or dismiss search filter)
        f: Toggle live log follow (tail -f)
        a: Toggle auto-scroll to bottom
        /: Open search and live filter bar
        t: Toggle timestamp display
        w: Toggle line wrapping
        c: Clear displayed log output
        s: Save / export logs to a text file
    """

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
        ("f", "toggle_follow", "Live Follow"),
        ("a", "toggle_auto_scroll", "Auto-Scroll"),
        ("slash", "open_filter", "Filter"),
        ("t", "toggle_timestamps", "Timestamps"),
        ("w", "toggle_wrap", "Wrap"),
        ("c", "clear_log", "Clear"),
        ("s", "save_log", "Save"),
    ]

    DEFAULT_CSS = """
    LogViewerScreen {
        align: center middle;
        background: $background;
    }
    LogViewerScreen .log-container {
        width: 100%;
        height: 100%;
        background: $background;
    }
    LogViewerScreen .log-header {
        height: 1;
        background: $surface;
        color: $foreground;
        padding: 0 1;
        border-bottom: solid $border;
    }
    LogViewerScreen RichLog {
        height: 1fr;
        background: $background;
        padding: 0 1;
    }
    LogViewerScreen .log-search-bar {
        height: 3;
        background: $surface;
        padding: 0 1;
        layout: horizontal;
        display: none;
        border-bottom: solid $border;
    }
    LogViewerScreen .log-search-bar.visible {
        display: block;
    }
    LogViewerScreen .log-search-label {
        width: auto;
        height: 3;
        content-align: center middle;
        color: $primary;
        text-style: bold;
    }
    LogViewerScreen .log-search-input {
        width: 1fr;
        height: 3;
        border: solid $primary;
        background: $surface;
        color: $foreground;
    }
    LogViewerScreen .log-search-matches {
        width: auto;
        height: 3;
        content-align: center middle;
        color: $text;
        padding-left: 1;
    }
    LogViewerScreen .log-footer {
        height: 1;
        background: $surface;
        color: $text;
        padding: 0 1;
        border-top: solid $border;
    }
    """

    MAX_BUFFER_LINES = 5000
    TIMESTAMP_REGEX = re.compile(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?\s*"
    )

    def __init__(
        self,
        title: str = "Logs",
        content: str = "",
        container_id: str | None = None,
        docker_client: DockerClient | None = None,
        is_compose: bool = False,
        compose_params: dict | None = None,
        tail: int = 200,
    ) -> None:
        super().__init__()
        self._title = title
        self._initial_content = content
        self._container_id = container_id
        self._docker = docker_client
        self._is_compose = is_compose
        self._compose_params = compose_params or {}
        self._tail = tail

        self._all_lines: list[str] = []
        self._is_live = bool(container_id or is_compose)
        self._auto_scroll = True
        self._wrap = True
        self._show_timestamps = True
        self._filter_query = ""
        self._match_count = 0

        self._active_stream: Any = None
        self._compose_process: asyncio.subprocess.Process | None = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="log-container"):
            yield Static(id="log-header", classes="log-header")
            yield RichLog(
                highlight=False,
                markup=False,
                wrap=True,
                id="log-output",
            )
            with Horizontal(id="log-search-bar", classes="log-search-bar"):
                yield Static("[bold cyan]FILTER:[/] ", classes="log-search-label")
                yield Input(
                    placeholder="Filter logs... (Enter: focus logs, Esc: clear filter)",
                    id="log-search-input",
                    classes="log-search-input",
                )
                yield Static("0 matches", id="log-search-matches", classes="log-search-matches")
            yield Static(
                "[#38bdf8 bold]Esc[/]/[#38bdf8 bold]q[/][#cbd5e1] Close  "
                "[#38bdf8 bold]f[/][#cbd5e1] Follow  "
                "[#38bdf8 bold]a[/][#cbd5e1] Auto-Scroll  "
                "[#38bdf8 bold]/[/][#cbd5e1] Filter  "
                "[#38bdf8 bold]t[/][#cbd5e1] Timestamps  "
                "[#38bdf8 bold]w[/][#cbd5e1] Wrap  "
                "[#38bdf8 bold]c[/][#cbd5e1] Clear  "
                "[#38bdf8 bold]s[/][#cbd5e1] Save",
                classes="log-footer",
            )

    def on_mount(self) -> None:
        """Initialize log content and start streaming if configured."""
        self._update_header()

        # Load initial content if provided
        if self._initial_content and self._initial_content.strip():
            for line in self._initial_content.splitlines():
                self._all_lines.append(line.rstrip("\r\n"))
            self._render_all_lines()
        elif not self._is_live:
            log = self.query_one("#log-output", RichLog)
            log.write(Text("No log output recorded.", style="dim italic #8b949e"))

        # Start live stream
        if self._is_live:
            self._start_streaming()

        self.query_one("#log-output", RichLog).focus()

    def on_unmount(self) -> None:
        """Clean up active processes and streams when dismissing modal."""
        self._cleanup()

    def _cleanup(self) -> None:
        """Stop background streaming tasks."""
        if self._active_stream:
            try:
                self._active_stream.close()
            except Exception:
                pass
            self._active_stream = None

        if self._compose_process:
            try:
                self._compose_process.terminate()
            except ProcessLookupError:
                pass
            self._compose_process = None

    def _update_header(self) -> None:
        header = self.query_one("#log-header", Static)

        # Live status badge
        if self._is_live:
            stream_badge = "[bold green]● LIVE[/]"
        elif self._container_id or self._is_compose:
            stream_badge = "[bold yellow]❚❚ PAUSED[/]"
        else:
            stream_badge = "[dim]OFFLINE[/]"

        # Auto-scroll badge
        autoscroll_badge = "[bold cyan]AUTO-SCROLL: ON[/]" if self._auto_scroll else "[dim]AUTO-SCROLL: OFF[/]"

        # Wrap badge
        wrap_badge = "[#388bfd]WRAP: ON[/]" if self._wrap else "[dim]WRAP: OFF[/]"

        # Timestamps badge
        time_badge = "[#a371f7]TIME: ON[/]" if self._show_timestamps else "[dim]TIME: OFF[/]"

        # Line count / Filter badge
        if self._filter_query:
            filter_badge = f"[bold #f0883e]FILTER: '{self._filter_query}' ({self._match_count}/{len(self._all_lines)})[/]"
        else:
            filter_badge = f"[#8b949e]{len(self._all_lines)} lines[/]"

        header.update(
            f"[bold cyan]⟨ {self._title} ⟩[/]   "
            f"{stream_badge}   "
            f"{autoscroll_badge}   "
            f"{wrap_badge}   "
            f"{time_badge}   "
            f"{filter_badge}"
        )

    def _format_line_for_render(self, line: str) -> Text:
        """Format a single log line into a Rich Text instance."""
        if not self._show_timestamps:
            clean_str = self.TIMESTAMP_REGEX.sub("", line)
        else:
            clean_str = line

        t = Text.from_ansi(clean_str)

        if self._show_timestamps:
            t.highlight_regex(
                r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?\s*",
                style="dim #6e7681",
            )

        if self._filter_query:
            t.highlight_regex(
                re.escape(self._filter_query),
                style="bold #0d1117 on #f0883e",
            )

        return t

    def _render_all_lines(self) -> None:
        """Re-render all lines from memory buffer into RichLog."""
        log = self.query_one("#log-output", RichLog)
        log.clear()

        self._match_count = 0
        matching = []

        query = self._filter_query.lower()
        for line in self._all_lines:
            if not query or query in line.lower():
                self._match_count += 1
                matching.append(self._format_line_for_render(line))

        if matching:
            for item in matching:
                log.write(item)
            if self._auto_scroll:
                log.scroll_end(animate=False)
        else:
            if self._filter_query:
                log.write(
                    Text(
                        f"No log lines matched '{self._filter_query}'",
                        style="dim italic #8b949e",
                    )
                )
            elif not self._all_lines:
                log.write(Text("Waiting for log output...", style="dim italic #8b949e"))

        self._update_header()
        self._update_search_matches()

    def _update_search_matches(self) -> None:
        """Update match counter in the filter bar."""
        matches_widget = self.query_one("#log-search-matches", Static)
        if self._filter_query:
            matches_widget.update(f"{self._match_count}/{len(self._all_lines)} matches")
        else:
            matches_widget.update(f"{len(self._all_lines)} lines")

    def _handle_incoming_line(self, raw_line: str) -> None:
        """Thread-safe append for a newly streamed line."""
        line = raw_line.rstrip("\r\n")
        self._all_lines.append(line)
        if len(self._all_lines) > self.MAX_BUFFER_LINES:
            self._all_lines.pop(0)

        # Check match
        matches = True
        if self._filter_query:
            matches = self._filter_query.lower() in line.lower()

        if matches:
            self._match_count += 1
            log = self.query_one("#log-output", RichLog)
            rendered = self._format_line_for_render(line)
            log.write(rendered)
            if self._auto_scroll:
                log.scroll_end(animate=False)

        self._update_header()
        self._update_search_matches()

    # ── Live Stream Workers ───────────────────────────────────────────

    def _start_streaming(self) -> None:
        """Dispatch appropriate streaming worker."""
        if self._container_id and self._docker:
            self._stream_container_worker()
        elif self._is_compose and self._docker:
            self._stream_compose_worker()

    @work(thread=True, exclusive=True, name="container_log_streamer")
    def _stream_container_worker(self) -> None:
        """Stream container logs chunk-by-chunk in a dedicated background thread."""
        worker = get_current_worker()
        if not self._container_id or not self._docker:
            return

        try:
            gen = self._docker.stream_container_logs(
                self._container_id, tail=self._tail, timestamps=True
            )
            self._active_stream = gen

            buffer = ""
            for chunk in gen:
                if worker.is_cancelled or not self._is_live:
                    break
                text = (
                    chunk.decode("utf-8", errors="replace")
                    if isinstance(chunk, bytes)
                    else str(chunk)
                )
                buffer += text
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    self.app.call_from_thread(self._handle_incoming_line, line)

            if buffer and not worker.is_cancelled and self._is_live:
                self.app.call_from_thread(self._handle_incoming_line, buffer)
        except Exception as e:
            if not worker.is_cancelled:
                self.app.call_from_thread(
                    self.notify, f"Log stream stopped: {e}", severity="warning"
                )
        finally:
            if self._active_stream:
                try:
                    self._active_stream.close()
                except Exception:
                    pass
                self._active_stream = None

    @work(exclusive=True, name="compose_log_streamer")
    async def _stream_compose_worker(self) -> None:
        """Stream compose logs line-by-line via subprocess."""
        if not self._docker:
            return

        try:
            self._compose_process = await self._docker.stream_compose_logs(
                project_name=self._compose_params.get("name", ""),
                config_file=self._compose_params.get("config_file", ""),
                working_dir=self._compose_params.get("working_dir", ""),
                tail=self._tail,
            )

            stdout = self._compose_process.stdout
            if stdout:
                while self._is_live:
                    line_bytes = await stdout.readline()
                    if not line_bytes:
                        break
                    line_str = line_bytes.decode("utf-8", errors="replace")
                    self._handle_incoming_line(line_str)
        except Exception as e:
            self.notify(f"Compose stream stopped: {e}", severity="warning")
        finally:
            if self._compose_process:
                try:
                    self._compose_process.terminate()
                except ProcessLookupError:
                    pass
                self._compose_process = None

    # ── Search & Filter Events ────────────────────────────────────────

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter logs live as the user types."""
        if event.input.id == "log-search-input":
            self._filter_query = event.value.strip()
            self._render_all_lines()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Return focus to log viewer on Enter so arrow keys navigate lines."""
        if event.input.id == "log-search-input":
            self.query_one("#log-output", RichLog).focus()

    # ── Actions ───────────────────────────────────────────────────────

    def action_open_filter(self) -> None:
        """Open and focus the search/filter input bar."""
        search_bar = self.query_one("#log-search-bar")
        search_bar.add_class("visible")
        input_widget = self.query_one("#log-search-input", Input)
        input_widget.focus()

    def action_toggle_follow(self) -> None:
        """Toggle live stream following on and off."""
        if not (self._container_id or self._is_compose):
            self.notify("Live stream is only available for active containers", severity="warning")
            return

        self._is_live = not self._is_live
        if self._is_live:
            self._start_streaming()
            self.notify("Live follow resumed", severity="information")
        else:
            self._cleanup()
            self.notify("Live follow paused", severity="information")
        self._update_header()

    def action_toggle_auto_scroll(self) -> None:
        """Toggle auto-scrolling to bottom on new lines."""
        self._auto_scroll = not self._auto_scroll
        if self._auto_scroll:
            log = self.query_one("#log-output", RichLog)
            log.scroll_end(animate=False)
            self.notify("Auto-scroll enabled", severity="information")
        else:
            self.notify("Auto-scroll disabled", severity="information")
        self._update_header()

    def action_toggle_timestamps(self) -> None:
        """Toggle timestamp prefix visibility."""
        self._show_timestamps = not self._show_timestamps
        status = "enabled" if self._show_timestamps else "disabled"
        self.notify(f"Timestamps {status}", severity="information")
        self._render_all_lines()

    def action_toggle_wrap(self) -> None:
        """Toggle text line wrapping."""
        self._wrap = not self._wrap
        log = self.query_one("#log-output", RichLog)
        log.wrap = self._wrap
        status = "enabled" if self._wrap else "disabled"
        self.notify(f"Line wrap {status}", severity="information")
        self._render_all_lines()

    def action_clear_log(self) -> None:
        """Clear memory buffer and log display."""
        self._all_lines.clear()
        self._match_count = 0
        log = self.query_one("#log-output", RichLog)
        log.clear()
        log.write(Text("Log display cleared.", style="dim italic #8b949e"))
        self._update_header()
        self._update_search_matches()
        self.notify("Logs cleared", severity="information")

    def action_save_log(self) -> None:
        """Export buffered log lines to a local timestamped text file."""
        if not self._all_lines:
            self.notify("No logs to export", severity="warning")
            return

        safe_name = re.sub(r"[^\w\-_\.]", "_", self._title.lower())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}.log"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                for line in self._all_lines:
                    f.write(line + "\n")
            self.notify(
                f"Exported {len(self._all_lines)} lines to {filename}",
                severity="information",
            )
        except OSError as e:
            self.notify(f"Failed to save log: {e}", severity="error")

    def action_close(self) -> None:
        """Close the search bar if focused, otherwise dismiss screen."""
        search_input = self.query_one("#log-search-input", Input)
        search_bar = self.query_one("#log-search-bar")

        # If search input is focused or active filter exists, clear it first
        if search_input.has_focus or self._filter_query:
            search_bar.remove_class("visible")
            search_input.value = ""
            self._filter_query = ""
            self._render_all_lines()
            self.query_one("#log-output", RichLog).focus()
            return

        self._cleanup()
        self.dismiss(None)
