"""STG Gastric Mill Rhythm — low-frequency metabolic cycles.

The gastric mill rhythm in lobsters controls slow chewing movements
(0.1-0.2 Hz). In Sclerotium OS, this maps to low-frequency tasks:
  - Daily digest generation (every morning at 09:00)
  - Weekly analysis report (every Monday)
  - Monthly strategic review (1st of month)
  - Evolution generation summary (every 100 generations)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

from kernel.stg.pattern_generator import CentralPatternGenerator


class GastricRhythm:
    """Low-frequency strategic rhythms — daily/weekly/monthly cycles.

    Named after the lobster gastric mill rhythm that controls the
    three-tooth stomach chewing apparatus. These are the slow,
    powerful cycles that process and digest accumulated information.
    """

    def __init__(self, cpg: CentralPatternGenerator | None = None) -> None:
        self.cpg = cpg or CentralPatternGenerator()
        self._digest_handler = None
        self._weekly_handler = None
        self._monthly_handler = None
        self._last_daily: str = ""
        self._last_weekly: str = ""
        self._last_monthly: str = ""

    def set_handlers(
        self,
        daily_digest: Any = None,
        weekly_report: Any = None,
        monthly_analysis: Any = None,
    ) -> None:
        self._digest_handler = daily_digest
        self._weekly_handler = weekly_report
        self._monthly_handler = monthly_analysis

    def register_all(self) -> None:
        """Register gastric rhythms — check every 5 minutes if due."""
        self.cpg.register(
            name="gastric.daily",
            interval_seconds=5 * 60,  # Check every 5 min
            handler=self._daily_tick,
        )
        self.cpg.register(
            name="gastric.weekly",
            interval_seconds=5 * 60,
            handler=self._weekly_tick,
        )
        self.cpg.register(
            name="gastric.monthly",
            interval_seconds=5 * 60,
            handler=self._monthly_tick,
        )

    async def _daily_tick(self) -> None:
        """Check if daily digest is due (target time from config, default 09:00)."""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        if today == self._last_daily:
            return

        # Trigger at configured hour (09:00 by default)
        if now.hour >= 9 and self._digest_handler:
            self._last_daily = today
            await self._digest_handler()

    async def _weekly_tick(self) -> None:
        """Check if weekly report is due (Monday)."""
        now = datetime.now()
        week_id = now.strftime("%Y-W%W")

        if week_id == self._last_weekly:
            return

        if now.weekday() == 0 and now.hour >= 9 and self._weekly_handler:
            self._last_weekly = week_id
            await self._weekly_handler()

    async def _monthly_tick(self) -> None:
        """Check if monthly analysis is due (1st of month)."""
        now = datetime.now()
        month_id = now.strftime("%Y-%m")

        if month_id == self._last_monthly:
            return

        if now.day == 1 and now.hour >= 9 and self._monthly_handler:
            self._last_monthly = month_id
            await self._monthly_handler()

    async def start(self) -> None:
        self.register_all()
        await self.cpg.start()

    async def stop(self) -> None:
        await self.cpg.stop()

    def get_status(self) -> dict:
        return {
            "last_daily": self._last_daily,
            "last_weekly": self._last_weekly,
            "last_monthly": self._last_monthly,
            "rhythms": self.cpg.get_status(),
        }
