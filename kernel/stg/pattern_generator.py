"""STG Central Pattern Generator — autonomous rhythm generation.

Maps the lobster stomatogastric ganglion's central pattern generator
to software: periodic autonomous rhythms that drive system metabolic
cycles without requiring external input.

Reference: Lobster STG (Nature Rev Neurosci, 2026) — 30 neurons
produce multiple rhythmic patterns via degenerate parameter sets.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable


class RhythmPhase(Enum):
    """CPG phase — analogous to pyloric rhythm tri-phasic cycle."""
    BURST = "burst"        # Active execution
    QUIESCENT = "quiescent"  # Recovery
    MODULATED = "modulated"  # Neuromodulator-influenced


@dataclass
class RhythmConfig:
    """Configuration for one rhythm cycle."""
    name: str
    interval_seconds: float
    phase_duration: float = 0.8  # fraction of interval spent in BURST
    enabled: bool = True


@dataclass
class RhythmState:
    """Runtime state of a rhythm generator."""
    config: RhythmConfig
    last_fired: float = 0.0
    fire_count: int = 0
    current_phase: RhythmPhase = RhythmPhase.QUIESCENT
    error_count: int = 0


class CentralPatternGenerator:
    """Autonomous rhythm generator — drives periodic system tasks.

    Like the lobster STG, this generates rhythmic output without
    requiring external pacemaker input. Multiple rhythms run concurrently
    and their phases can be modulated by neuromodulator profiles.
    """

    async def adaptive_tick(self) -> int:
        """Run one adaptive tick across all rhythms.
        Self-healing: error_count > 3 doubles interval.
        Returns number of rhythms that fired.
        """
        fired = 0
        for rhythm in self.rhythms:
            if not rhythm.config.enabled:
                continue
            now = time.time()
            if now - rhythm.last_fired >= rhythm.config.interval_seconds:
                try:
                    rhythm.fire_count += 1
                    rhythm.current_phase = RhythmPhase.BURST
                    rhythm.last_fired = now
                    rhythm.error_count = 0
                    fired += 1
                except Exception:
                    rhythm.error_count += 1
                    if rhythm.error_count > 3:
                        rhythm.config.interval_seconds *= 2.0
                        rhythm.error_count = 0
        return fired

    def __init__(self) -> None:
        self._rhythms: dict[str, RhythmState] = {}
        self._handlers: dict[str, Callable[[], Awaitable[Any]]] = {}
        self._running = False
        self._tasks: list[asyncio.Task] = []

    # ── Registration ──────────────────────────────────────────────────

    def register(
        self,
        name: str,
        interval_seconds: float,
        handler: Callable[[], Awaitable[Any]],
        phase_duration: float = 0.8,
        enabled: bool = True,
    ) -> None:
        """Register a rhythm with its handler callback."""
        config = RhythmConfig(
            name=name,
            interval_seconds=interval_seconds,
            phase_duration=phase_duration,
            enabled=enabled,
        )
        self._rhythms[name] = RhythmState(config=config)
        self._handlers[name] = handler

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start all registered rhythms."""
        self._running = True
        for name in self._rhythms:
            task = asyncio.create_task(self._run_rhythm(name))
            self._tasks.append(task)

    async def stop(self) -> None:
        """Stop all rhythms gracefully."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    async def _run_rhythm(self, name: str) -> None:
        """Run a single rhythm loop."""
        state = self._rhythms[name]
        handler = self._handlers[name]

        while self._running:
            if not state.config.enabled:
                await asyncio.sleep(1)
                continue

            now = time.time()
            elapsed = now - state.last_fired

            if elapsed >= state.config.interval_seconds:
                state.current_phase = RhythmPhase.BURST
                try:
                    await handler()
                    state.fire_count += 1
                except Exception:
                    state.error_count += 1
                state.last_fired = time.time()
                state.current_phase = RhythmPhase.QUIESCENT

            # Sleep a fraction of the interval to balance responsiveness vs CPU
            sleep_time = min(1.0, state.config.interval_seconds * 0.1)
            await asyncio.sleep(sleep_time)

    # ── Neuromodulation ───────────────────────────────────────────────

    def modulate(self, name: str, interval_seconds: float | None = None) -> None:
        """Apply neuromodulation: change rhythm frequency.

        Analogous to lobster STG neuromodulators (dopamine, serotonin, etc.)
        that reconfigure the same neural circuit for different behaviors.
        """
        if name in self._rhythms and interval_seconds is not None:
            self._rhythms[name].config.interval_seconds = max(0.001, interval_seconds)

    def set_enabled(self, name: str, enabled: bool) -> None:
        """Enable/disable a rhythm."""
        if name in self._rhythms:
            self._rhythms[name].config.enabled = enabled

    # ── Status ────────────────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """Get status of all rhythms."""
        return {
            name: {
                "last_fired": state.last_fired,
                "fire_count": state.fire_count,
                "interval_seconds": state.config.interval_seconds,
                "enabled": state.config.enabled,
                "phase": state.current_phase.value,
                "errors": state.error_count,
            }
            for name, state in self._rhythms.items()
        }
