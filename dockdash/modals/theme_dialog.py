"""Theme selection and settings modal dialog."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, OptionList, Static
from textual.widgets.option_list import Option

from dockdash.themes import AVAILABLE_THEMES, save_theme


class ThemeDialog(ModalScreen[str | None]):
    """Modal dialog allowing users to choose and live-preview color templates."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._initial_theme: str = "cyber-slate"

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog theme-dialog"):
            yield Static("⟨ COLOR TEMPLATES & SETTINGS ⟩", classes="modal-title")
            with Vertical(classes="modal-body theme-body"):
                yield Static(
                    "Navigate with [bold]↑ ↓[/] to preview themes in real time. "
                    "Press [bold]Enter[/] or click [bold]Apply & Save[/] to save.",
                    classes="theme-help-text text-muted",
                )
                yield OptionList(id="theme-option-list", classes="theme-option-list")

            with Horizontal(classes="modal-footer theme-footer"):
                yield Button("Cancel [Esc]", id="cancel-btn", variant="default")
                yield Button(
                    "Apply & Save [Enter]",
                    id="save-btn",
                    variant="primary",
                )

    def on_mount(self) -> None:
        """Populate option list and highlight the active theme."""
        self._initial_theme = getattr(self.app, "theme", "cyber-slate")
        option_list = self.query_one("#theme-option-list", OptionList)

        active_idx = 0
        for idx, theme in enumerate(AVAILABLE_THEMES):
            is_active = theme.id == self._initial_theme
            active_badge = "  [#34d399 bold]✓ ACTIVE[/]" if is_active else ""
            label = (
                f"[{theme.primary_color}]●[/] [bold]{theme.name:<18}[/] "
                f"[dim]{theme.description}[/]{active_badge}"
            )
            option_list.add_option(Option(prompt=label, id=theme.id))
            if is_active:
                active_idx = idx

        option_list.highlighted = active_idx
        option_list.focus()

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        """Preview theme in real-time as user scrolls through options."""
        if event.option_id and event.option_id in self.app.available_themes:
            try:
                self.app.theme = event.option_id
            except Exception:
                pass

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        """User pressed Enter directly on an option."""
        if event.option_id:
            self._apply_and_close(event.option_id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            option_list = self.query_one("#theme-option-list", OptionList)
            if option_list.highlighted is not None:
                option = option_list.get_option_at_index(option_list.highlighted)
                theme_id = getattr(option, "id", None) or self._initial_theme
                self._apply_and_close(theme_id)
            else:
                self._apply_and_close(self._initial_theme)
        else:
            self.action_cancel()

    def _apply_and_close(self, theme_id: str) -> None:
        """Save selected theme, notify user, and dismiss."""
        save_theme(theme_id)
        if theme_id in self.app.available_themes:
            self.app.theme = theme_id

        theme_name = next(
            (t.name for t in AVAILABLE_THEMES if t.id == theme_id), theme_id
        )
        self.app.notify(
            f"Color template saved: {theme_name}",
            title="Theme Updated",
            severity="information",
        )
        self.dismiss(theme_id)

    def action_cancel(self) -> None:
        """Revert theme back to what it was before opening the dialog."""
        if self._initial_theme in self.app.available_themes:
            try:
                self.app.theme = self._initial_theme
            except Exception:
                pass
        self.dismiss(None)
