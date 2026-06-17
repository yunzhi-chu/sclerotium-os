"""Dashboard Screen — System health, FCPI gauges, event log, genome tree.

Claude Code equivalent: Doctor.tsx (system diagnostics screen).
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


class DashboardScreen(Screen):
    """System overview dashboard — Claude Code's Doctor.tsx equivalent."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("🧬 SCLEROTIUM OS — System Dashboard", id="dash-title"),
            Horizontal(
                Vertical(
                    Static("FCPI Gauges", id="fcpi-panel"),
                    Static("Loading...", id="fcpi-content"),
                    id="fcpi-container",
                ),
                Vertical(
                    Static("System Health", id="health-panel"),
                    Static("MCP: checking...\nMemory: checking...\nSTG: checking...", id="health-content"),
                    id="health-container",
                ),
            ),
            Horizontal(
                Vertical(
                    Static("Event Log", id="event-panel"),
                    Static("Waiting for events...", id="event-content"),
                    id="event-container",
                ),
                Vertical(
                    Static("Genome Tree", id="genome-panel"),
                    Static("No genomes loaded", id="genome-content"),
                    id="genome-container",
                ),
            ),
            id="dashboard-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Load dashboard data."""
        self._refresh_data()

    def _refresh_data(self) -> None:
        """Refresh all dashboard panels."""
        # This would be wired to real data sources in production
        pass
