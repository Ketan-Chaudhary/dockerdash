"""Modal dialog for visual representation and inspection of Docker image layers."""

from __future__ import annotations

import datetime
from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import DataTable, Static


def clean_command(cmd: str | None) -> str:
    """Clean and reformat Dockerfile instruction from Docker layer history."""
    if not cmd:
        return "—"
    cmd = cmd.strip()
    if "#(nop)" in cmd:
        cmd = cmd.split("#(nop)", 1)[1].strip()
    elif cmd.startswith("/bin/sh -c "):
        cmd = "RUN " + cmd[len("/bin/sh -c ") :].strip()
    if cmd.endswith(" # buildkit"):
        cmd = cmd[:-len(" # buildkit")].strip()
    return cmd


def format_size(bytes_val: int) -> str:
    """Format bytes into readable string."""
    if bytes_val <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    val = float(bytes_val)
    idx = 0
    while val >= 1024.0 and idx < len(units) - 1:
        val /= 1024.0
        idx += 1
    return f"{val:.2f} {units[idx]}"


def make_proportion_bar(size: int, total_size: int, width: int = 12) -> Text:
    """Generate a visual proportion bar for layer size."""
    if total_size <= 0 or size <= 0:
        bar = "░" * width
        return Text(f"[{bar}]  0.0%", style="dim")

    ratio = min(max(size / total_size, 0.0), 1.0)
    filled = int(round(ratio * width))
    bar = "█" * filled + "░" * (width - filled)
    pct = ratio * 100

    # Colorize bar based on layer weight
    if size >= 50 * 1024 * 1024:
        style = "#f87171 bold"  # Red / Heavy
    elif size >= 20 * 1024 * 1024:
        style = "#fbbf24 bold"  # Yellow / Medium-Heavy
    elif size >= 1024 * 1024:
        style = "#34d399"  # Green / Normal
    else:
        style = "#38bdf8"  # Cyan / Lightweight

    return Text(f"[{bar}] {pct:>5.1f}%", style=style)


class ImageLayersDialog(ModalScreen[None]):
    """Visual inspector for Docker image layers with size breakdown and commands."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("q", "dismiss", "Close", show=False),
        Binding("c", "copy_command", "Copy Command", show=True),
        Binding("o", "toggle_order", "Toggle Order", show=True),
    ]

    DEFAULT_CSS = """
    ImageLayersDialog {
        align: center middle;
        background: #000000aa;
    }

    ImageLayersDialog .layers-container {
        width: 95%;
        max-width: 130;
        height: 90%;
        max-height: 42;
        background: $surface;
        border: solid $primary;
        padding: 0 1;
    }

    ImageLayersDialog .layers-header {
        height: 1;
        background: $panel;
        color: $primary;
        text-style: bold;
        padding: 0 1;
        margin-top: 1;
    }

    ImageLayersDialog .layers-summary {
        height: 2;
        padding: 0 1;
        color: $text;
        border-bottom: solid $border;
    }

    ImageLayersDialog .layers-table-container {
        height: 1fr;
        min-height: 10;
        border-bottom: solid $border;
    }

    ImageLayersDialog DataTable {
        height: 100%;
        width: 100%;
        background: transparent;
    }

    ImageLayersDialog .detail-panel {
        height: 9;
        background: $panel;
        padding: 0 1;
        margin-top: 0;
    }

    ImageLayersDialog .detail-title {
        height: 1;
        color: $secondary;
        text-style: bold;
    }

    ImageLayersDialog .detail-scroll {
        height: 5;
        overflow-y: scroll;
        background: transparent;
    }

    ImageLayersDialog .detail-command {
        color: $foreground;
    }

    ImageLayersDialog .layers-footer {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, image_name: str, raw_layers: list[dict[str, Any]]) -> None:
        super().__init__()
        self.image_name = image_name
        self._raw_layers = raw_layers or []
        self._base_first = True  # True: Base layer first (step 1 -> N), False: Top layer first
        self._parsed_layers: list[dict[str, Any]] = []
        self._parse_layers()

    def _parse_layers(self) -> None:
        """Parse raw layer data from Docker API into structured records."""
        # docker history returns layers latest-first (top layer at index 0)
        # For base_first, we reverse it so base layer is #1
        raw_list = list(reversed(self._raw_layers)) if self._base_first else list(self._raw_layers)

        total_size = sum(h.get("Size", 0) for h in self._raw_layers)
        self.total_size = total_size

        self._parsed_layers = []
        for idx, h in enumerate(raw_list, start=1):
            raw_id = h.get("Id") or ""
            if raw_id.startswith("sha256:"):
                short_id = raw_id.replace("sha256:", "")[:12]
            elif raw_id == "<missing>":
                short_id = "<metadata>"
            else:
                short_id = raw_id[:12] or "<metadata>"

            size = h.get("Size", 0)
            created_ts = h.get("Created", 0)
            if created_ts:
                try:
                    dt = datetime.datetime.fromtimestamp(created_ts, tz=datetime.timezone.utc)
                    created_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                except Exception:
                    created_str = str(created_ts)
            else:
                created_str = "—"

            raw_cmd = h.get("CreatedBy", "") or ""
            clean_cmd = clean_command(raw_cmd)

            self._parsed_layers.append({
                "step": idx,
                "short_id": short_id,
                "full_id": raw_id,
                "size": size,
                "size_str": format_size(size),
                "created": created_str,
                "command": clean_cmd,
                "raw_command": raw_cmd,
                "comment": h.get("Comment", "") or "",
            })

    def compose(self) -> ComposeResult:
        with Vertical(classes="layers-container"):
            yield Static(
                f"⟨ IMAGE LAYERS ⟩  [#f8fafc bold]{self.image_name}[/]  "
                f"[#cbd5e1]•  Total Size: [#38bdf8 bold]{format_size(self.total_size)}[/]  "
                f"•  Layers: [#38bdf8 bold]{len(self._parsed_layers)}[/][/]",
                classes="layers-header",
            )
            order_label = "Base layer first (1 → N)" if self._base_first else "Top layer first (N → 1)"
            largest = max((layer["size"] for layer in self._parsed_layers), default=0)
            yield Static(
                f"[#94a3b8]Order:[/] [#38bdf8]{order_label}[/]   "
                f"[#94a3b8]Largest Layer:[/] [#fbbf24 bold]{format_size(largest)}[/]   "
                f"[#94a3b8]Navigate:[/] [#f8fafc]↑/↓ or j/k[/] to inspect full command",
                classes="layers-summary",
            )

            with Vertical(classes="layers-table-container"):
                yield DataTable(id="layers-table", cursor_type="row")

            with Vertical(classes="detail-panel"):
                yield Static(
                    "⟨ SELECTED LAYER INSTRUCTION ⟩  [#94a3b8][c] Copy Command[/]",
                    classes="detail-title",
                )
                with VerticalScroll(classes="detail-scroll"):
                    yield Static(id="layer-detail-text", classes="detail-command")

            with Horizontal(classes="layers-footer"):
                yield Static(
                    "[#38bdf8 bold]Esc[/][#cbd5e1]=Close  "
                    "[#38bdf8 bold]c[/][#cbd5e1]=Copy  "
                    "[#38bdf8 bold]o[/][#cbd5e1]=Toggle Order  "
                    "[#38bdf8 bold]↑/↓[/][#cbd5e1]=Navigate",
                )

    def on_mount(self) -> None:
        table = self.query_one("#layers-table", DataTable)
        table.add_columns("#", "LAYER ID", "SIZE", "PROPORTION", "INSTRUCTION")
        self._populate_table()

    def _populate_table(self) -> None:
        table = self.query_one("#layers-table", DataTable)
        table.clear()

        for layer in self._parsed_layers:
            step_str = f"#{layer['step']}"
            id_str = layer["short_id"]

            # Style size cell
            sz = layer["size"]
            if sz == 0:
                sz_text = Text("0 B", style="dim")
            elif sz >= 50 * 1024 * 1024:
                sz_text = Text(layer["size_str"], style="#f87171 bold")
            elif sz >= 20 * 1024 * 1024:
                sz_text = Text(layer["size_str"], style="#fbbf24 bold")
            else:
                sz_text = Text(layer["size_str"], style="#34d399")

            prop_bar = make_proportion_bar(sz, self.total_size, width=12)

            # Truncated command for row
            cmd_preview = layer["command"].replace("\n", " ")
            if len(cmd_preview) > 65:
                cmd_preview = cmd_preview[:62] + "..."

            # Keyword highlight on preview
            cmd_text = self._highlight_keywords(cmd_preview)

            table.add_row(
                step_str,
                id_str,
                sz_text,
                prop_bar,
                cmd_text,
                key=str(layer["step"]),
            )

        if self._parsed_layers:
            self._update_detail(self._parsed_layers[0])
            table.focus()

    def _highlight_keywords(self, text: str) -> Text:
        """Syntax-color standard Dockerfile instruction keywords."""
        keywords = {
            "RUN": "#ec4899 bold",
            "COPY": "#38bdf8 bold",
            "ADD": "#38bdf8 bold",
            "ENV": "#a78bfa bold",
            "CMD": "#fbbf24 bold",
            "ENTRYPOINT": "#fbbf24 bold",
            "EXPOSE": "#34d399 bold",
            "WORKDIR": "#818cf8 bold",
            "USER": "#f472b6 bold",
            "LABEL": "#94a3b8",
            "ARG": "#a78bfa",
            "VOLUME": "#2dd4bf bold",
            "STOPSIGNAL": "#f87171",
            "HEALTHCHECK": "#2dd4bf bold",
        }

        parts = text.split(" ", 1)
        first_word = parts[0]
        if first_word in keywords:
            colored = Text()
            colored.append(first_word, style=keywords[first_word])
            if len(parts) > 1:
                colored.append(" " + parts[1], style="#f8fafc")
            return colored
        return Text(text, style="#f8fafc")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._on_row_active(event.row_key.value)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            self._on_row_active(event.row_key.value)

    def _on_row_active(self, step_key: str | None) -> None:
        if not step_key:
            return
        try:
            step_num = int(step_key)
            for layer in self._parsed_layers:
                if layer["step"] == step_num:
                    self._update_detail(layer)
                    break
        except Exception:
            pass

    def _update_detail(self, layer: dict[str, Any]) -> None:
        detail = self.query_one("#layer-detail-text", Static)
        cmd_rich = self._highlight_keywords(layer["command"])
        text = Text()
        text.append(f"Layer #{layer['step']}  |  ID: {layer['short_id']}  |  Size: {layer['size_str']}  |  Created: {layer['created']}\n", style="#94a3b8")
        text.append_text(cmd_rich)
        if layer["comment"]:
            text.append(f"\nComment: {layer['comment']}", style="dim")
        detail.update(text)

    def _get_current_layer(self) -> dict[str, Any] | None:
        table = self.query_one("#layers-table", DataTable)
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            step_num = int(row_key.value)
            for layer in self._parsed_layers:
                if layer["step"] == step_num:
                    return layer
        except Exception:
            pass
        return self._parsed_layers[0] if self._parsed_layers else None

    def action_copy_command(self) -> None:
        """Copy the full command of the selected layer."""
        layer = self._get_current_layer()
        if not layer:
            return
        cmd = layer["command"]
        try:
            self.app.copy_to_clipboard(cmd)
            self.notify("Command copied to clipboard!", severity="information")
        except Exception:
            self.notify("Unable to access clipboard", severity="warning")

    def action_toggle_order(self) -> None:
        """Toggle between Base-first and Top-first order."""
        self._base_first = not self._base_first
        self._parse_layers()
        self._populate_table()
        order_name = "Base layer first" if self._base_first else "Top layer first"
        self.notify(f"Layer order: {order_name}", severity="information")
