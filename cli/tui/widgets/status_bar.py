"""Status Bar — Claude Code-style footer with token/cost/turn info.

Uses Textual's proper render() override pattern (not direct renderable mutation).
"""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static


class SclerotiumStatusBar(Static):
    """Bottom status bar with real-time session metrics."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__("", *args, **kwargs)
        self._tokens: int = 0
        self._turns: int = 0
        self._model: str = "deepseek-v4-pro"
        self._provider: str = "deepseek"
        self._cost: float = 0.0

    def render(self) -> Text:
        """Textual's render hook — called by the framework on every refresh."""
        cost_str = f"${self._cost:.4f}" if self._cost > 0 else "$0"
        return Text(
            f" Tokens: {self._tokens:,} | "
            f"Turns: {self._turns} | "
            f"Cost: {cost_str} | "
            f"Model: {self._model}@{self._provider} | "
            f"Sclerotium OS v0.3.0",
            style="dim",
        )

    def update_metrics(
        self,
        tokens: int = 0,
        turns: int = 0,
        model: str = "",
        provider: str = "",
    ) -> None:
        """Update status bar metrics and trigger re-render."""
        if tokens:
            self._tokens += tokens
        if turns:
            self._turns += turns
        if model:
            self._model = model
        if provider:
            self._provider = provider
        self._cost = self._tokens * 0.00000014
        self.refresh()
