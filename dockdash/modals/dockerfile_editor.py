"""Dockerfile editor — full-screen modal with syntax highlighting and build support."""

from __future__ import annotations

import os
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static, TextArea

DEFAULT_DOCKERFILE = """\
# ─── Dockerfile ───────────────────────────────────────────────
# Build your container image
# ──────────────────────────────────────────────────────────────

FROM ubuntu:22.04

# Set metadata
LABEL maintainer="you@example.com"

# Install dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application files
COPY . .

# Expose port
EXPOSE 8080

# Default command
CMD ["bash"]
"""


class DockerfileEditorDialog(ModalScreen[dict | None]):
    """Full-screen Dockerfile editor with syntax highlighting, save, and build.

    Returns:
        dict with keys: action ("save"|"build"), path, content, tag
        or None if cancelled.
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "save", "Save"),
    ]

    DEFAULT_CSS = """
    DockerfileEditorDialog {
        align: center middle;
        background: #0d1117ee;
    }
    DockerfileEditorDialog .editor-container {
        width: 100%;
        height: 100%;
        background: #0d1117;
        border: solid #30363d;
        padding: 0;
    }
    DockerfileEditorDialog .editor-header {
        dock: top;
        height: 1;
        background: #161b22;
        color: #79c0ff;
        text-style: bold;
        padding: 0 1;
        border-bottom: solid #30363d;
    }
    DockerfileEditorDialog .editor-top-bar {
        dock: top;
        height: 3;
        background: #161b22;
        padding: 0 1;
        border-bottom: solid #30363d;
        layout: horizontal;
    }
    DockerfileEditorDialog .editor-top-bar Label {
        padding: 1 1 0 0;
        width: auto;
    }
    DockerfileEditorDialog .editor-top-bar Input {
        width: 1fr;
    }
    DockerfileEditorDialog .editor-bottom-bar {
        dock: bottom;
        height: 3;
        background: #161b22;
        padding: 0 1;
        border-top: solid #30363d;
        layout: horizontal;
        align: right middle;
    }
    DockerfileEditorDialog .editor-bottom-bar Input {
        width: 1fr;
    }
    DockerfileEditorDialog .editor-bottom-bar Label {
        padding: 1 1 0 0;
        width: auto;
    }
    DockerfileEditorDialog .editor-bottom-bar Button {
        margin: 0 0 0 1;
    }
    DockerfileEditorDialog TextArea {
        height: 1fr;
        width: 100%;
    }
    """

    def __init__(
        self,
        file_path: str = "",
        content: str = "",
    ) -> None:
        super().__init__()
        self._file_path = file_path
        self._initial_content = content or DEFAULT_DOCKERFILE

        if file_path and os.path.isfile(file_path):
            with open(file_path) as f:
                self._initial_content = f.read()

    def compose(self) -> ComposeResult:
        with Vertical(classes="editor-container"):
            yield Static(
                "⟨ DOCKERFILE EDITOR ⟩  "
                "[#484f58]Ctrl+S[/][#8b949e]=save  [/]"
                "[#484f58]Esc[/][#8b949e]=close[/]",
                classes="editor-header",
            )

            # File path bar
            with Horizontal(classes="editor-top-bar"):
                yield Label("Path:")
                yield Input(
                    value=self._file_path or str(Path.home() / "Dockerfile"),
                    placeholder="/path/to/Dockerfile",
                    id="file-path",
                )

            # Editor — takes all remaining space
            try:
                yield TextArea.code_editor(
                    self._initial_content,
                    language="dockerfile",
                    id="dockerfile-editor",
                )
            except Exception:
                yield TextArea(
                    self._initial_content,
                    id="dockerfile-editor",
                )

            # Bottom bar with tag + buttons
            with Horizontal(classes="editor-bottom-bar"):
                yield Label("Tag:")
                yield Input(
                    placeholder="e.g. myapp:latest",
                    id="build-tag",
                )
                yield Button("Cancel", id="cancel-btn")
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Build Image", id="build-btn", variant="success")

    def on_mount(self) -> None:
        self.query_one("#dockerfile-editor", TextArea).focus()

    def _get_content(self) -> str:
        return self.query_one("#dockerfile-editor", TextArea).text

    def _get_path(self) -> str:
        return self.query_one("#file-path", Input).value.strip()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "save-btn":
            self.action_save()
        elif event.button.id == "build-btn":
            self._do_build()

    def action_save(self) -> None:
        path = self._get_path()
        content = self._get_content()
        if not path:
            self.notify("File path is required", severity="error")
            return

        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            self.notify(f"Saved to {path}", severity="information")
        except OSError as e:
            self.notify(f"Save failed: {e}", severity="error")

    def _do_build(self) -> None:
        path = self._get_path()
        content = self._get_content()
        tag = self.query_one("#build-tag", Input).value.strip()

        if not path:
            self.notify("File path is required", severity="error")
            return

        # Save first
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
        except OSError as e:
            self.notify(f"Save failed: {e}", severity="error")
            return

        self.dismiss({
            "action": "build",
            "path": os.path.dirname(path) or ".",
            "dockerfile": os.path.basename(path),
            "content": content,
            "tag": tag or None,
        })

    def action_cancel(self) -> None:
        self.dismiss(None)
