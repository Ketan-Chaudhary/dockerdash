"""Color templates and theme management for DockDash.

Provides curated visual themes, persistent configuration, and theme registration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from textual.theme import Theme

if TYPE_CHECKING:
    from textual.app import App

CONFIG_DIR = Path.home() / ".config" / "dockdash"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_THEME = "cyber-slate"


@dataclass(frozen=True)
class ThemeMeta:
    """Metadata describing a selectable theme."""

    id: str
    name: str
    description: str
    primary_color: str
    bg_color: str
    accent_color: str


# Curated theme definitions with rich terminal aesthetics
CUSTOM_THEMES: list[Theme] = [
    Theme(
        name="cyber-slate",
        primary="#38bdf8",
        secondary="#60a5fa",
        warning="#fbbf24",
        error="#f87171",
        success="#34d399",
        accent="#a78bfa",
        foreground="#f8fafc",
        background="#0a0e17",
        surface="#121824",
        panel="#1a2234",
        dark=True,
    ),
    Theme(
        name="synthwave",
        primary="#00f0ff",
        secondary="#ff007f",
        warning="#ffe600",
        error="#ff3864",
        success="#05ffa1",
        accent="#b967ff",
        foreground="#f8f8f2",
        background="#12072b",
        surface="#1c0b3f",
        panel="#291254",
        dark=True,
    ),
]

# Themes shown in the UI theme selector
AVAILABLE_THEMES: list[ThemeMeta] = [
    ThemeMeta(
        id="cyber-slate",
        name="Cyber Slate",
        description="Default • Electric Cyan & Deep Obsidian Void",
        primary_color="#38bdf8",
        bg_color="#0a0e17",
        accent_color="#a78bfa",
    ),
    ThemeMeta(
        id="tokyo-night",
        name="Tokyo Night",
        description="Cyberpunk Neon Violet & Deep Indigo",
        primary_color="#bb9af7",
        bg_color="#1a1b26",
        accent_color="#7aa2f7",
    ),
    ThemeMeta(
        id="dracula",
        name="Dracula",
        description="Classic Vampire Purple & Fluorescent Pink",
        primary_color="#bd93f9",
        bg_color="#282a36",
        accent_color="#ff79c6",
    ),
    ThemeMeta(
        id="nord",
        name="Nord",
        description="Arctic Frost Cyan & Polar Night",
        primary_color="#88c0d0",
        bg_color="#2e3440",
        accent_color="#81a1c1",
    ),
    ThemeMeta(
        id="catppuccin-mocha",
        name="Catppuccin Mocha",
        description="Soothing Pastel Mauve & Dark Charcoal",
        primary_color="#f5c2e7",
        bg_color="#181825",
        accent_color="#cba6f7",
    ),
    ThemeMeta(
        id="monokai",
        name="Monokai Pro",
        description="Vivid Purple, Neon Yellow & Dark Olive",
        primary_color="#ae81ff",
        bg_color="#272822",
        accent_color="#66d9ef",
    ),
    ThemeMeta(
        id="gruvbox",
        name="Gruvbox Dark",
        description="Retro Warm Aqua, Gold & Deep Bark",
        primary_color="#85a598",
        bg_color="#282828",
        accent_color="#fabd2f",
    ),
    ThemeMeta(
        id="synthwave",
        name="Synthwave '84",
        description="Retro Synth Neon Cyan, Magenta & Purple",
        primary_color="#00f0ff",
        bg_color="#12072b",
        accent_color="#ff007f",
    ),
    ThemeMeta(
        id="solarized-dark",
        name="Solarized Dark",
        description="Precision Blue & Deep Marine Navy",
        primary_color="#268bd2",
        bg_color="#002b36",
        accent_color="#2aa198",
    ),
]


def load_config() -> dict[str, Any]:
    """Load configuration dictionary from disk."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_config(config: dict[str, Any]) -> bool:
    """Save configuration dictionary to disk."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False


def get_saved_theme() -> str:
    """Get the saved theme name or return the default theme."""
    config = load_config()
    theme_name = config.get("theme", DEFAULT_THEME)
    valid_ids = {t.id for t in AVAILABLE_THEMES}
    return theme_name if theme_name in valid_ids else DEFAULT_THEME


def save_theme(theme_name: str) -> bool:
    """Persist theme selection to user config."""
    config = load_config()
    config["theme"] = theme_name
    return save_config(config)


def register_themes(app: App) -> None:
    """Register all custom themes on the Textual application instance."""
    for theme in CUSTOM_THEMES:
        try:
            app.register_theme(theme)
        except Exception:
            pass


def apply_theme(app: App, theme_name: str) -> None:
    """Safely apply a theme to the app instance."""
    if theme_name in app.available_themes:
        app.theme = theme_name
