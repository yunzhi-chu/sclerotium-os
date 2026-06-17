"""Memory browser screen — search, navigate by level, view entries."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class MemoryScreen:
    """Browser for Hexis 5-layer memory system."""

    LEVEL_COLORS: dict[str, str] = {
        "working": "yellow",
        "episodic": "blue",
        "semantic": "green",
        "procedural": "magenta",
        "strategic": "red",
    }

    def render_search_results(
        self, query: str, results: list[dict[str, Any]], console: Console | None = None
    ) -> None:
        """Render memory search results."""
        if console is None:
            console = Console()

        if not results:
            console.print(Panel(f"No results for: {query}", border_style="yellow"))
            return

        table = Table(title=f"Memory Search: {query}", border_style="cyan")
        table.add_column("Score", width=8, justify="right")
        table.add_column("Level", width=12)
        table.add_column("Content", width=50)
        table.add_column("ID", width=10)

        for r in results[:20]:
            level = r.get("memory_level", "unknown")
            color = self.LEVEL_COLORS.get(level, "white")
            table.add_row(
                Text(f"{r.get('score', 0):.2f}"),
                Text(level, style=color),
                Text(r.get("content", "")[:48]),
                Text(r.get("id", "")[:8], style="dim"),
            )

        console.print(table)

    def render_levels_overview(self, stats: dict[str, int], console: Console | None = None) -> None:
        """Render overview of all five memory levels."""
        if console is None:
            console = Console()

        table = Table(title="Memory Levels", border_style="cyan")
        table.add_column("Level", width=14)
        table.add_column("Count", width=8, justify="right")
        table.add_column("Status")

        expected_order = ["working", "episodic", "semantic", "procedural", "strategic"]
        for level in expected_order:
            count = stats.get(level, 0)
            color = self.LEVEL_COLORS.get(level, "white")
            status = "● active" if count > 0 else "○ empty"
            table.add_row(
                Text(level, style=color),
                Text(str(count)),
                Text(status, style="green" if count > 0 else "dim"),
            )

        total = sum(stats.values())
        table.add_section()
        table.add_row(
            Text("Total", style="bold"),
            Text(str(total), style="bold"),
            Text(""),
        )

        console.print(Panel(table, border_style="bright_black"))
