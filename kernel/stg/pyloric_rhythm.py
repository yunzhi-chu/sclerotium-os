"""STG Pyloric Rhythm — high-frequency metabolic cycles.

The pyloric rhythm in lobsters controls rapid peristaltic movements
(1-2 Hz). In Sclerotium OS, this maps to high-frequency system tasks:
  - Code scanning (every 30 min)
  - Memory consolidation check (every 6 hours)
  - Evolution status poll (every 5 min)
  - IM message check (every 30 sec)

These run autonomously without requiring user input — the system's
"heartbeat" and "breathing."
"""

from __future__ import annotations

import asyncio
from typing import Any

from kernel.stg.pattern_generator import CentralPatternGenerator


class PyloricRhythm:
    """High-frequency system rhythms — heartbeat and breathing.

    Named after the lobster pyloric rhythm that controls food peristalsis.
    These are the fastest autonomous cycles in the system.
    """

    def __init__(self, cpg: CentralPatternGenerator | None = None) -> None:
        self.cpg = cpg or CentralPatternGenerator()
        self._scan_handler = None
        self._memory_handler = None
        self._evolution_handler = None
        self._im_handler = None

    def set_handlers(
        self,
        scan: Any = None,
        memory: Any = None,
        evolution: Any = None,
        im_check: Any = None,
    ) -> None:
        """Wire up handler callbacks to MCP tools / bridges."""
        self._scan_handler = scan
        self._memory_handler = memory
        self._evolution_handler = evolution
        self._im_handler = im_check

    def register_all(self) -> None:
        """Register all pyloric rhythms with the CPG."""
        # Code scan — every 30 minutes
        self.cpg.register(
            name="pyloric.scan",
            interval_seconds=30 * 60,
            handler=self._scan_tick,
            phase_duration=0.3,
        )

        # Evolution status check — every 5 minutes
        self.cpg.register(
            name="pyloric.evolution",
            interval_seconds=5 * 60,
            handler=self._evolution_tick,
            phase_duration=0.1,
        )

        # Memory consolidation — every 6 hours
        self.cpg.register(
            name="pyloric.memory",
            interval_seconds=6 * 3600,
            handler=self._memory_tick,
            phase_duration=0.5,
        )

        # IM message poll — every 30 seconds
        self.cpg.register(
            name="pyloric.im_poll",
            interval_seconds=30,
            handler=self._im_tick,
            phase_duration=0.05,
        )

    async def _scan_tick(self) -> None:
        """Periodic code quality scan."""
        if self._scan_handler:
            await self._scan_handler()
        # Placeholder: emit event
        # await event_bus.publish("pyloric.scan.tick", {})

    async def _evolution_tick(self) -> None:
        """Periodic evolution status poll."""
        if self._evolution_handler:
            await self._evolution_handler()

    async def _memory_tick(self) -> None:
        """Periodic memory consolidation trigger."""
        if self._memory_handler:
            await self._memory_handler()

    async def _im_tick(self) -> None:
        """Poll IM platforms for new messages."""
        if self._im_handler:
            await self._im_handler()

    async def start(self) -> None:
        """Start all pyloric rhythms."""
        self.register_all()
        await self.cpg.start()

    async def stop(self) -> None:
        await self.cpg.stop()

    def get_status(self) -> dict:
        return self.cpg.get_status()
