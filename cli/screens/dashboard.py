"""Dashboard screen — FCPI gauges, system health, event log, genome tree."""

from __future__ import annotations

import os
from typing import Any

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cli.widgets.fcpi_gauges import FCPIGauges
from cli.widgets.event_log import EventLog
from cli.widgets.genome_tree import GenomeTree


class DashboardScreen:
    """Main system dashboard combining all widgets."""

    def __init__(self) -> None:
        self.gauges = FCPIGauges()
        self.event_log = EventLog()
        self.genome_tree = GenomeTree()

    def update_fcpi(self, scores: dict[str, float]) -> None:
        self.gauges.update(scores)

    def push_event(self, event_type: str, message: str) -> None:
        self.event_log.push(event_type, message)

    def update_genomes(self, genomes: list[dict[str, Any]]) -> None:
        self.genome_tree.update(genomes)

    def render(self, console: Console | None = None) -> None:
        """Render the full dashboard layout."""
        if console is None:
            console = Console()

        console.clear()
        console.print()

        # Header
        header = Panel(
            Text("Sclerotium OS v0.2.0 — CLI Dashboard", style="bold cyan", justify="center"),
            border_style="cyan",
        )
        console.print(header)
        console.print()

        # FCPI Gauges
        console.print(self.gauges.render())
        console.print()

        # System health summary
        health = self._render_health()
        console.print(health)
        console.print()

        # Event log
        console.print(self.event_log.render(max_rows=8))

    def _render_health(self) -> Panel:
        """Render system health summary."""
        table = Table.grid(padding=(0, 3))
        table.add_column()
        table.add_column()
        table.add_column()
        table.add_column()

        table.add_row(
            Text("MC", style="green"),  # MCP
            Text("online", style="green"),
            Text("EV", style="cyan"),   # Evolution
            Text("idle", style="dim"),
        )
        table.add_row(
            Text("MM", style="blue"),   # Memory
            Text("healthy", style="green"),
            Text("SF", style="red"),    # Safety
            Text("active", style="green"),
        )
        table.add_row(
            Text("SB", style="magenta"), # Sandbox
            Text("ready", style="green"),
            Text("STG", style="yellow"), # STG
            Text("pending", style="dim"),
        )

        return Panel(table, title="System Health", border_style="bright_black")

    def render_compact(self) -> str:
        """Render a compact one-line status suitable for the REPL prompt."""
        fcpi = self.gauges._fcpi_total
        return f"FCPI:{fcpi:.2f} | MCP:online | EV:idle | MM:ok"
