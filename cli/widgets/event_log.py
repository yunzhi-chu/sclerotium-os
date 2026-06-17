"""Event Log widget — Rich-based real-time event stream."""

from __future__ import annotations

import time
from collections import deque
from typing import Any

from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class EventLog:
    """Scrollable real-time event log with timestamp and coloring."""

    EVENT_COLORS: dict[str, str] = {
        "evolution.tick": "green",
        "evolution.phase_change": "yellow",
        "memory.stored": "blue",
        "memory.consolidated": "cyan",
        "sandbox.executed": "magenta",
        "skill.crystallized": "bright_green",
        "genome.mutated": "red",
        "system.error": "bold red",
        "system.warning": "bold yellow",
    }

    def __init__(self, max_entries: int = 200) -> None:
        self._entries: deque[tuple[str, str, str]] = deque(maxlen=max_entries)

    def push(self, event_type: str, message: str) -> None:
        """Add an event to the log."""
        ts = time.strftime("%H:%M:%S")
        self._entries.append((ts, event_type, message))

    def render(self, max_rows: int = 10) -> Panel:
        """Render recent events as a Rich Panel."""
        table = Table.grid(padding=(0, 1))
        table.add_column("time", width=10, style="dim")
        table.add_column("event", width=24, style="bold")
        table.add_column("message", width=50)

        for ts, evt, msg in list(self._entries)[-max_rows:]:
            color = self.EVENT_COLORS.get(evt, "white")
            table.add_row(
                Text(ts, style="dim"),
                Text(f"[{evt}]", style=color),
                Text(msg),
            )

        return Panel(table, title="Event Stream", border_style="bright_black")
