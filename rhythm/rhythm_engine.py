"""Rhythm Engine — the organism's hierarchical biological clock.

Lobster STG-inspired architecture:
  ┌─────────────────────────────────────────────┐
  │  PYLORIC (high-freq, ~seconds-minutes)      │
  │  • Pulse health checks                      │
  │  • Window/activity polling                  │
  │  • Clipboard monitoring                     │
  ├─────────────────────────────────────────────┤
  │  GASTRIC (low-freq, ~hours-days)            │
  │  • Hourly event rollup                      │
  │  • Daily digest generation                  │
  │  • Weekly strategic analysis                │
  │  • Memory consolidation                     │
  ├─────────────────────────────────────────────┤
  │  NEUROMODULATOR (mode-based reconfiguration)│
  │  • work / sleep / game / meeting / creative │
  │  • Modifies notification frequency          │
  │  • Modifies evolution activity              │
  │  • Modifies scan/poll intervals             │
  └─────────────────────────────────────────────┘
"""

from __future__ import annotations

import threading
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from kernel.event_bus import EventBus
from kernel.stg.neuromodulator import Neuromodulator, Profile, ModulationState

logger = logging.getLogger("sclerotium.rhythm")


# ═══════════════════════════════════════════════════════════════
# Rhythm Ticks
# ═══════════════════════════════════════════════════════════════

class RhythmLayer(Enum):
    """The three rhythm layers."""
    PYLORIC = "pyloric"      # High frequency
    GASTRIC = "gastric"      # Low frequency
    METABOLIC = "metabolic"  # Consolidation / sleep-time only


@dataclass(frozen=True)
class RhythmTick:
    """Immutable record of a rhythm pulse."""
    layer: RhythmLayer
    tick_number: int
    timestamp: float = field(default_factory=time.time)
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RhythmState:
    """Immutable snapshot of rhythm engine state."""
    active_profile: str
    pyloric_ticks: int
    gastric_ticks: int
    metabolic_ticks: int
    total_ticks: int
    uptime_seconds: float
    pyloric_interval: float
    gastric_interval: float


# ═══════════════════════════════════════════════════════════════
# Rhythm Engine
# ═══════════════════════════════════════════════════════════════

class RhythmEngine:
    """Hierarchical rhythm generator.

    Usage:
        bus = EventBus()
        engine = RhythmEngine(event_bus=bus)
        engine.start()
        # ... organism runs with STG rhythms ...
        engine.stop()
    """

    TOPIC_PYLORIC = "rhythm.pyloric"
    TOPIC_GASTRIC = "rhythm.gastric"
    TOPIC_METABOLIC = "rhythm.metabolic"
    TOPIC_MODE_CHANGE = "rhythm.mode_change"

    # Default intervals (seconds)
    DEFAULT_PYLORIC_INTERVAL = 30.0    # 30 seconds
    DEFAULT_GASTRIC_INTERVAL = 3600.0  # 1 hour
    DEFAULT_METABOLIC_INTERVAL = 21600.0  # 6 hours

    def __init__(
        self,
        event_bus: EventBus,
        neuromodulator: Neuromodulator | None = None,
        pyloric_interval: float = DEFAULT_PYLORIC_INTERVAL,
        gastric_interval: float = DEFAULT_GASTRIC_INTERVAL,
    ) -> None:
        self._bus = event_bus
        self._neuro = neuromodulator or Neuromodulator()

        self._pyloric_interval = pyloric_interval
        self._gastric_interval = gastric_interval

        # Tick counters
        self._pyloric_ticks: int = 0
        self._gastric_ticks: int = 0
        self._metabolic_ticks: int = 0

        # Threads (P1-3: SafeThread wrapper for exception safety)
        self._pyloric_thread: threading.Thread | None = None
        self._gastric_thread: threading.Thread | None = None
        self._running: bool = False
        self._stop_event = threading.Event()
        self._started_at: float = 0.0

        # Callbacks for each layer
        self._on_pyloric: list[Callable[[RhythmTick], None]] = []
        self._on_gastric: list[Callable[[RhythmTick], None]] = []
        self._on_mode_change: list[Callable[[str, str], None]] = []  # (old, new)

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def start(self) -> None:
        """Start all rhythm threads. P1-3: SafeThread-style stop event."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._started_at = time.time()

        self._pyloric_thread = threading.Thread(
            target=self._pyloric_loop,
            name="sclerotium-pyloric",
            daemon=True,
        )
        self._pyloric_thread.start()

        self._gastric_thread = threading.Thread(
            target=self._gastric_loop,
            name="sclerotium-gastric",
            daemon=True,
        )
        self._gastric_thread.start()

        logger.info(
            "Rhythm engine started — pyloric=%.1fs, gastric=%.1fs, profile=%s",
            self._pyloric_interval, self._gastric_interval,
            self._neuro.active_profile.value,
        )

    def stop(self) -> None:
        """Stop all rhythm threads. P1-3: uses stop_event for clean shutdown."""
        import traceback
        self._running = False
        self._stop_event.set()
        timeout = max(self._pyloric_interval, self._gastric_interval) * 2
        for t_name, t in [
            ("pyloric", self._pyloric_thread),
            ("gastric", self._gastric_thread),
        ]:
            if t and t.is_alive():
                t.join(timeout=timeout)
                if t.is_alive():
                    logger.warning("Rhythm %s thread did not stop within %.1fs", t_name, timeout)
        logger.info("Rhythm engine stopped — total ticks: pyloric=%d, gastric=%d",
                     self._pyloric_ticks, self._gastric_ticks)

    def switch_mode(self, profile_name: str) -> dict[str, Any]:
        """Switch to a new neuromodulator profile."""
        old = self._neuro.active_profile.value
        result = self._neuro.switch(profile_name)
        if "error" not in result:
            new = result["active_profile"]
            # Update intervals based on profile
            state = self._neuro.state
            if hasattr(state, 'pyloric_scan_interval'):
                self._pyloric_interval = state.pyloric_scan_interval

            # Notify callbacks
            for cb in self._on_mode_change:
                try:
                    cb(old, new)
                except Exception:
                    pass

            self._bus.publish(
                self.TOPIC_MODE_CHANGE,
                data={"old": old, "new": new, "changes": result.get("changes", {})},
                source="RhythmEngine",
            )
        return result

    def get_state(self) -> RhythmState:
        """Get current rhythm state snapshot."""
        return RhythmState(
            active_profile=self._neuro.active_profile.value,
            pyloric_ticks=self._pyloric_ticks,
            gastric_ticks=self._gastric_ticks,
            metabolic_ticks=self._metabolic_ticks,
            total_ticks=self._pyloric_ticks + self._gastric_ticks + self._metabolic_ticks,
            uptime_seconds=time.time() - self._started_at if self._started_at > 0 else 0.0,
            pyloric_interval=self._pyloric_interval,
            gastric_interval=self._gastric_interval,
        )

    def trigger_gastric_manually(self) -> RhythmTick:
        """Manually trigger a gastric tick (for testing or immediate digest)."""
        return self._gastric_tick()

    def trigger_pyloric_manually(self) -> RhythmTick:
        """Manually trigger a pyloric tick (for testing)."""
        return self._pyloric_tick()

    # ═══════════════════════════════════════════════════════════
    # Callbacks
    # ═══════════════════════════════════════════════════════════

    def on_pyloric(self, cb: Callable[[RhythmTick], None]) -> None:
        """Register a pyloric tick callback."""
        self._on_pyloric.append(cb)

    def on_gastric(self, cb: Callable[[RhythmTick], None]) -> None:
        """Register a gastric tick callback."""
        self._on_gastric.append(cb)

    def on_mode_change(self, cb: Callable[[str, str], None]) -> None:
        """Register a mode change callback: cb(old_profile, new_profile)."""
        self._on_mode_change.append(cb)

    # ═══════════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════════

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def profile(self) -> str:
        return self._neuro.active_profile.value

    @property
    def neuromodulator(self) -> Neuromodulator:
        return self._neuro

    @property
    def pyloric_interval(self) -> float:
        return self._pyloric_interval

    # ═══════════════════════════════════════════════════════════
    # Internal Rhythm Loops
    # ═══════════════════════════════════════════════════════════

    def _pyloric_loop(self) -> None:
        """High-frequency loop — pulse every pyloric_interval seconds."""
        while self._running:
            try:
                self._pyloric_tick()
            except Exception as e:
                logger.warning("Pyloric tick error: %s", e)
            # Sleep in small chunks for responsive shutdown
            self._sleep_interruptible(self._pyloric_interval)

    def _gastric_loop(self) -> None:
        """Low-frequency loop — pulse every gastric_interval seconds."""
        while self._running:
            # Check if we should run gastric based on current profile
            if self._should_run_gastric():
                try:
                    self._gastric_tick()
                except Exception as e:
                    logger.warning("Gastric tick error: %s", e)
            self._sleep_interruptible(self._gastric_interval)

    def _pyloric_tick(self) -> RhythmTick:
        """Single pyloric pulse."""
        self._pyloric_ticks += 1
        tick = RhythmTick(
            layer=RhythmLayer.PYLORIC,
            tick_number=self._pyloric_ticks,
            payload={
                "profile": self._neuro.active_profile.value,
                "notification_level": self._neuro.state.notification_level,
            },
        )

        # Publish to EventBus
        self._bus.publish(
            self.TOPIC_PYLORIC,
            data={"tick": tick.tick_number, "timestamp": tick.timestamp},
            source="RhythmEngine",
        )

        # Notify callbacks
        for cb in self._on_pyloric:
            try:
                cb(tick)
            except Exception:
                pass

        return tick

    def _gastric_tick(self) -> RhythmTick:
        """Single gastric pulse — triggers digestion and consolidation."""
        self._gastric_ticks += 1
        tick = RhythmTick(
            layer=RhythmLayer.GASTRIC,
            tick_number=self._gastric_ticks,
            payload={
                "profile": self._neuro.active_profile.value,
                "hour": int(time.strftime("%H", time.localtime())),
                "weekday": int(time.strftime("%w", time.localtime())),
            },
        )

        # Publish to EventBus
        self._bus.publish(
            self.TOPIC_GASTRIC,
            data={
                "tick": tick.tick_number,
                "hour": tick.payload["hour"],
                "weekday": tick.payload["weekday"],
                "timestamp": tick.timestamp,
            },
            source="RhythmEngine",
        )

        # Notify callbacks
        for cb in self._on_gastric:
            try:
                cb(tick)
            except Exception:
                pass

        return tick

    def _should_run_gastric(self) -> bool:
        """Check if gastric tick should run based on current profile."""
        state = self._neuro.state
        # In sleep mode, only run gastric every 6 hours
        if self._neuro.active_profile == Profile.SLEEP:
            return self._gastric_ticks % 6 == 0
        # In game mode, run less frequently
        if self._neuro.active_profile == Profile.GAME:
            return self._gastric_ticks % 3 == 0
        return True

    def _sleep_interruptible(self, seconds: float, chunk: float = 1.0) -> None:
        """Sleep in small chunks for responsive shutdown. P1-3: checks stop_event."""
        elapsed = 0.0
        while elapsed < seconds and not self._stop_event.is_set():
            time.sleep(min(chunk, seconds - elapsed))
            elapsed += chunk
