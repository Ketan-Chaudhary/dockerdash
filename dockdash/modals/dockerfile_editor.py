"""Dockerfile editor — full-screen modal with syntax highlighting and build support."""

from __future__ import annotations

import os
import re
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
        background: #0a0e17ee;
    }
    DockerfileEditorDialog .editor-container {
        width: 100%;
        height: 100%;
        background: #0a0e17;
        border: solid #2b384e;
        padding: 0;
    }
    DockerfileEditorDialog .editor-header {
        height: 1;
        background: #121824;
        color: #38bdf8;
        text-style: bold;
        padding: 0 1;
        border-bottom: solid #2b384e;
    }
    DockerfileEditorDialog .editor-top-bar {
        height: 3;
        background: #121824;
        padding: 0 1;
        border-bottom: solid #2b384e;
        layout: horizontal;
    }
    DockerfileEditorDialog .editor-top-bar Label {
        padding: 1 1 0 0;
        width: auto;
        color: #cbd5e1;
    }
    DockerfileEditorDialog .editor-top-bar Input {
        width: 1fr;
    }
    DockerfileEditorDialog TextArea {
        height: 1fr;
        width: 100%;
    }
    DockerfileEditorDialog .editor-bottom-bar {
        height: auto;
        min-height: 4;
        background: #121824;
        padding: 0 1;
        border-top: solid #2b384e;
        layout: horizontal;
        align: right middle;
    }
    DockerfileEditorDialog .editor-bottom-bar Input {
        width: 1fr;
    }
    DockerfileEditorDialog .editor-bottom-bar Label {
        padding: 1 1 0 0;
        width: auto;
        color: #cbd5e1;
    }
    DockerfileEditorDialog .editor-bottom-bar Button {
        margin: 0 0 0 1;
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
                "[#38bdf8 bold]Ctrl+S[/][#cbd5e1]=save  [/]"
                "[#38bdf8 bold]Esc[/][#cbd5e1]=close[/]",
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
        if os.path.isdir(path):
            self.notify("Specified path is a directory, not a Dockerfile", severity="error")
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
        if os.path.isdir(path):
            self.notify("Specified path is a directory, not a Dockerfile", severity="error")
            return
        if not content.strip():
            self.notify("Dockerfile content cannot be empty", severity="error")
            return
        if tag and (re.search(r"\s", tag) or tag.count(":") > 1):
            self.notify("Invalid tag format (spaces not allowed)", severity="error")
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
