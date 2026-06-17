"""FCPI Six-Dimension Gauge widget — Rich-based hexad gauges."""

from __future__ import annotations

from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text


class FCPIGauges:
    """Render six FCPI dimension gauges as a Rich table with progress bars."""

    DIMENSIONS = [
        ("coding", 0.25, "green"),
        ("coordination", 0.25, "blue"),
        ("safety", 0.15, "red"),
        ("decision", 0.15, "yellow"),
        ("emergence", 0.10, "magenta"),
        ("performance", 0.10, "cyan"),
    ]

    def __init__(self) -> None:
        self._scores: dict[str, float] = {d: 0.0 for d, _, _ in self.DIMENSIONS}
        self._fcpi_total: float = 0.0

    def update(self, scores: dict[str, float]) -> None:
        """Update gauge values from a scores dict."""
        for dim, _, _ in self.DIMENSIONS:
            self._scores[dim] = max(0.0, min(1.0, scores.get(dim, 0.0)))
        total = sum(
            self._scores[d] * w for (d, w, _), (d2, _, _) in zip(self.DIMENSIONS, self.DIMENSIONS)
        )
        self._fcpi_total = round(total, 4)

    def render(self) -> Panel:
        """Render gauges as a Rich Panel."""
        table = Table.grid(padding=(0, 2))
        table.add_column("dim", width=14, style="bold")
        table.add_column("bar", width=40)
        table.add_column("val", width=6, justify="right")

        for dim, weight, color in self.DIMENSIONS:
            score = self._scores[dim]
            bar_chars = "█" * int(score * 20) + "░" * (20 - int(score * 20))
            bar = Text(bar_chars, style=color)
            label = Text(f"{dim:<12}", style=color)
            value = Text(f"{score:.2f}", style=f"{color} bold")
            table.add_row(label, bar, value)

        title = Text(f"FCPI Dashboard — Total: {self._fcpi_total:.3f}", style="bold white")
        return Panel(table, title=title, border_style="bright_black")


class FCPIProgress(Progress):
    """Textual-compatible FCPI progress display."""

    @classmethod
    def for_fcpi(cls, scores: dict[str, float]) -> "FCPIProgress":
        """Create a progress bar set from FCPI scores."""
        progress = cls(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
        )
        for dim, _, _ in cls.DIMENSIONS if hasattr(cls, "DIMENSIONS") else []:
            pass  # Placeholder for Textual integration
        return progress
