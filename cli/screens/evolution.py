"""Evolution monitor screen — Panarchy phase, generation progress, population stats."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text


class EvolutionScreen:
    """Real-time evolution progress monitor."""

    def __init__(self) -> None:
        self._gen_current: int = 0
        self._gen_total: int = 0
        self._phase: str = "IDLE"
        self._fcpi_total: float = 0.0
        self._fcpi_vector: dict[str, float] = {}
        self._panarchy: str = "r"
        self._population: int = 0
        self._elite: int = 0
        self._connectedness: float = 0.0
        self._resilience: float = 1.0
        self._history: list[tuple[int, float]] = []  # (gen, fcpi)

    def update(self, status: dict[str, Any]) -> None:
        """Update from evolution_status() response."""
        self._gen_current = status.get("current_generation", 0)
        self._gen_total = status.get("total_generations", 0)
        self._phase = status.get("phase", "IDLE")
        self._fcpi_total = status.get("fcpi_total", 0.0)
        self._fcpi_vector = status.get("fcpi_vector", {})
        self._panarchy = status.get("panarchy_phase", "r")
        self._population = status.get("population_size", 0)
        self._elite = status.get("elite_count", 0)
        self._connectedness = status.get("panarchy_connectedness", 0.0)
        self._resilience = status.get("panarchy_resilience", 1.0)

        if self._gen_current > 0 and self._fcpi_total > 0:
            self._history.append((self._gen_current, self._fcpi_total))
            if len(self._history) > 50:
                self._history = self._history[-50:]

    def render(self, console: Console | None = None) -> None:
        """Render evolution status."""
        if console is None:
            console = Console()

        phase_colors: dict[str, str] = {
            "PENDING": "dim", "INITIALIZING": "yellow", "RUNNING_ARENAS": "cyan",
            "AGGREGATING_FITNESS": "blue", "SELECTING": "magenta",
            "MUTATING": "red", "CRYSTALLIZING": "green", "COMPLETE": "bold green",
        }
        panarchy_colors: dict[str, str] = {
            "r": "green", "K": "yellow", "OMEGA": "red", "ALPHA": "blue",
        }

        phase_color = phase_colors.get(self._phase, "white")
        pan_color = panarchy_colors.get(self._panarchy, "white")

        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold", width=18)
        table.add_column()

        table.add_row("Phase:", Text(self._phase, style=phase_color))
        table.add_row(
            "Generation:",
            Text(f"{self._gen_current}/{self._gen_total}", style="bold"),
        )
        table.add_row("FCPI Total:", Text(f"{self._fcpi_total:.4f}", style="bold green"))
        table.add_row(
            "Panarchy:",
            Text(f"{self._panarchy} (C:{self._connectedness:.2f} R:{self._resilience:.2f})", style=pan_color),
        )
        table.add_row(
            "Population:",
            Text(f"{self._population} ({self._elite} elite)", style="bold"),
        )

        # Mini FCPI bars
        for dim, score in sorted(self._fcpi_vector.items()):
            bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
            table.add_row(f"  {dim}:", Text(f"{bar} {score:.2f}"))

        console.print(Panel(table, title="Evolution Status", border_style="cyan"))

        # Trend sparkline
        if len(self._history) > 1:
            self._render_trend(console)

    def _render_trend(self, console: Console) -> None:
        """Render a simple ASCII sparkline of FCPI trend."""
        values = [fcpi for _, fcpi in self._history[-20:]]
        if not values:
            return

        mn, mx = min(values), max(values)
        rng = max(mx - mn, 0.01)
        chars = "▁▂▃▄▅▆▇█"
        spark = ""
        for v in values:
            idx = min(int((v - mn) / rng * (len(chars) - 1)), len(chars) - 1)
            spark += chars[idx]

        start_fcpi = self._history[0][1]
        end_fcpi = self._history[-1][1]
        delta = end_fcpi - start_fcpi
        sign = "+" if delta > 0 else ""

        console.print(
            Text(f"  FCPI trend: {spark}  ({sign}{delta:.4f})", style="dim")
        )
