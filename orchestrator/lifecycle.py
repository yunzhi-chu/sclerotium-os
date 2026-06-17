"""Lifecycle Manager — the heartbeat conductor of Sclerotium OS.

Orchestrates the organism's entire lifecycle:
  BOOTING → INITIALIZING → RUNNING → SLEEPING → SHUTTING_DOWN

Each phase activates different organ layers in the correct order.
All state transitions are immutable (new state returned, never mutated).
"""

from __future__ import annotations

import threading
import time
import signal
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable


# ═══════════════════════════════════════════════════════════════
# Lifecycle Phases
# ═══════════════════════════════════════════════════════════════

class LifecyclePhase(Enum):
    """The organism's life stages."""
    OFFLINE = "offline"             # Not started
    BOOTING = "booting"             # Starting up, loading config
    INITIALIZING = "initializing"   # Wiring organs
    RUNNING = "running"             # Fully alive
    SLEEPING = "sleeping"           # Low-power rest mode
    SHUTTING_DOWN = "shutting_down" # Graceful termination
    ERROR = "error"                 # Something went wrong


# ═══════════════════════════════════════════════════════════════
# Organ Status Tracking
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class OrganStatus:
    """Immutable status snapshot of one organ."""
    name: str
    layer: str                      # SENSE / THINK / ACT / EVOLVE / METABOLIZE
    loaded: bool = False
    healthy: bool = True
    error: str = ""
    started_at: float = 0.0


@dataclass(frozen=True)
class LifecycleState:
    """Immutable snapshot of the organism's current state."""
    phase: LifecyclePhase = LifecyclePhase.OFFLINE
    organs: tuple[OrganStatus, ...] = ()
    started_at: float = 0.0
    uptime_seconds: float = 0.0
    mode: str = "work"              # work / sleep / game / meeting / creative
    version: str = "0.6.0"


# ═══════════════════════════════════════════════════════════════
# Lifecycle Manager
# ═══════════════════════════════════════════════════════════════

class LifecycleManager:
    """Conductor of the organism's life.

    Usage:
        lm = LifecycleManager(home_dir="~/.sclerotium")
        state = lm.boot()          # → BOOTING → INITIALIZING → RUNNING
        state = lm.status()        # → LifecycleState snapshot
        state = lm.sleep()         # → SLEEPING
        state = lm.wake()          # → RUNNING
        state = lm.shutdown()      # → SHUTTING_DOWN → OFFLINE
    """

    # Startup order: each phase activates these organs in sequence
    STARTUP_SEQUENCE = [
        # (phase, organs_to_load)
        ("core", [
            ("EventBus", "METABOLIZE"),
            ("SessionStore", "ACT"),
            ("ConfigLoader", "SENSE"),
        ]),
        ("safety", [
            ("ConstitutionalArbiter", "ACT"),
            ("SandstormExecutor", "ACT"),
        ]),
        ("memory", [
            ("HexisMemory", "SENSE"),
            ("CodebaseIndexer", "SENSE"),
        ]),
        ("intelligence", [
            ("UniversalModelGateway", "ACT"),
            ("ToolRegistry", "ACT"),
            ("AgentLoop", "THINK"),
            ("PromptFactory", "THINK"),
        ]),
        ("rhythm", [
            ("STGRhythms", "METABOLIZE"),
            ("SchedulerEngine", "METABOLIZE"),
        ]),
        ("bridges", [
            ("FungalBridge", "EVOLVE"),
            ("MiroFishBridge", "EVOLVE"),
        ]),
    ]

    def __init__(
        self,
        home_dir: str | Path = "~/.sclerotium",
        project_root: str | Path = ".",
        headless: bool = True,
    ) -> None:
        self._home = Path(home_dir).expanduser().resolve()
        self._project_root = Path(project_root).resolve()
        self._headless = headless

        # Internal mutable state (all public APIs return immutable snapshots)
        self._phase = LifecyclePhase.OFFLINE
        self._organs: dict[str, OrganStatus] = {}
        self._started_at: float = 0.0
        self._mode: str = "work"
        self._shutdown_event = threading.Event()
        self._threads: list[threading.Thread] = []
        self._on_phase_change: list[Callable[[LifecycleState], None]] = []

    # ═══════════════════════════════════════════════════════════
    # Public API — all return immutable LifecycleState
    # ═══════════════════════════════════════════════════════════

    def boot(self) -> LifecycleState:
        """Bring the organism to life. Returns the RUNNING state on success."""
        if self._phase in (LifecyclePhase.RUNNING, LifecyclePhase.BOOTING, LifecyclePhase.INITIALIZING):
            return self.status()

        self._set_phase(LifecyclePhase.BOOTING)
        self._started_at = time.time()
        self._shutdown_event.clear()

        try:
            self._ensure_directories()
            self._load_startup_sequence()
            self._set_phase(LifecyclePhase.RUNNING)
        except Exception as e:
            self._set_phase(LifecyclePhase.ERROR)
            # Mark the failing organ
            raise RuntimeError(f"Boot failed: {e}") from e

        return self.status()

    def shutdown(self, timeout: float = 10.0) -> LifecycleState:
        """Gracefully shut down the organism."""
        if self._phase in (LifecyclePhase.OFFLINE, LifecyclePhase.SHUTTING_DOWN):
            return self.status()

        self._set_phase(LifecyclePhase.SHUTTING_DOWN)
        self._shutdown_event.set()

        # Stop threads in reverse order
        for t in reversed(self._threads):
            if t.is_alive():
                t.join(timeout=timeout / max(len(self._threads), 1))
        self._threads.clear()

        # Mark all organs as unloaded
        self._organs = {
            name: OrganStatus(
                name=o.name, layer=o.layer,
                loaded=False, healthy=o.healthy, error="shutdown"
            )
            for name, o in self._organs.items()
        }

        self._started_at = 0.0
        self._set_phase(LifecyclePhase.OFFLINE)
        return self.status()

    def sleep(self) -> LifecycleState:
        """Enter low-power rest mode. Organs stay loaded but pause activity."""
        if self._phase != LifecyclePhase.RUNNING:
            return self.status()
        self._mode = "sleep"
        self._set_phase(LifecyclePhase.SLEEPING)
        return self.status()

    def wake(self) -> LifecycleState:
        """Resume from sleep mode."""
        if self._phase != LifecyclePhase.SLEEPING:
            return self.status()
        self._mode = "work"
        self._set_phase(LifecyclePhase.RUNNING)
        return self.status()

    def status(self) -> LifecycleState:
        """Get an immutable snapshot of current organism state."""
        uptime = time.time() - self._started_at if self._started_at > 0 else 0.0
        return LifecycleState(
            phase=self._phase,
            organs=tuple(self._organs.values()),
            started_at=self._started_at,
            uptime_seconds=uptime,
            mode=self._mode,
        )

    def get_organ(self, name: str) -> OrganStatus | None:
        """Get the status of a specific organ."""
        return self._organs.get(name)

    def register_organ(self, name: str, layer: str, loaded: bool = True) -> OrganStatus:
        """Dynamically register a new organ at runtime."""
        organ = OrganStatus(
            name=name, layer=layer,
            loaded=loaded, healthy=True,
            started_at=time.time(),
        )
        self._organs[name] = organ
        return organ

    def mark_organ_error(self, name: str, error: str) -> OrganStatus | None:
        """Mark an organ as unhealthy."""
        if name not in self._organs:
            return None
        old = self._organs[name]
        new = OrganStatus(
            name=old.name, layer=old.layer,
            loaded=old.loaded, healthy=False, error=error,
            started_at=old.started_at,
        )
        self._organs[name] = new
        return new

    def mark_organ_healthy(self, name: str) -> OrganStatus | None:
        """Restore an organ to healthy status."""
        if name not in self._organs:
            return None
        old = self._organs[name]
        new = OrganStatus(
            name=old.name, layer=old.layer,
            loaded=old.loaded, healthy=True, error="",
            started_at=old.started_at,
        )
        self._organs[name] = new
        return new

    def get_healthy_organs(self) -> tuple[OrganStatus, ...]:
        """Get all currently healthy organs."""
        return tuple(o for o in self._organs.values() if o.healthy)

    def get_unhealthy_organs(self) -> tuple[OrganStatus, ...]:
        """Get all organs in error state."""
        return tuple(o for o in self._organs.values() if not o.healthy)

    # ═══════════════════════════════════════════════════════════
    # Phase change callbacks
    # ═══════════════════════════════════════════════════════════

    def on_phase_change(self, callback: Callable[[LifecycleState], None]) -> None:
        """Register a callback invoked on every phase transition."""
        self._on_phase_change.append(callback)

    # ═══════════════════════════════════════════════════════════
    # Signal handling
    # ═══════════════════════════════════════════════════════════

    def register_signal_handlers(self) -> None:
        """Register OS signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, lambda s, f: self.shutdown())
        signal.signal(signal.SIGTERM, lambda s, f: self.shutdown())
        if sys.platform == "win32":
            try:
                signal.signal(signal.SIGBREAK, lambda s, f: self.shutdown())  # type: ignore[attr-defined]
            except AttributeError:
                pass

    # ═══════════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════════

    def _set_phase(self, phase: LifecyclePhase) -> None:
        """Transition to a new phase and notify callbacks."""
        old_phase = self._phase
        self._phase = phase
        if phase != old_phase:
            state = self.status()
            for cb in self._on_phase_change:
                try:
                    cb(state)
                except Exception:
                    pass

    def _ensure_directories(self) -> None:
        """Create the sclerotium home directory structure."""
        dirs = [
            self._home,
            self._home / "memory",
            self._home / "chroma",
            self._home / "sessions",
            self._home / "audit",
            self._home / "genomes",
            self._home / "skills",
            self._home / "logs",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _load_startup_sequence(self) -> None:
        """Execute the startup sequence, loading organs in order."""
        self._set_phase(LifecyclePhase.INITIALIZING)

        for sequence_name, organs in self.STARTUP_SEQUENCE:
            for organ_name, layer in organs:
                try:
                    organ = OrganStatus(
                        name=organ_name, layer=layer,
                        loaded=True, healthy=True,
                        started_at=time.time(),
                    )
                    self._organs[organ_name] = organ
                except Exception as e:
                    organ = OrganStatus(
                        name=organ_name, layer=layer,
                        loaded=False, healthy=False, error=str(e),
                    )
                    self._organs[organ_name] = organ
                    # Don't fail the whole boot — one organ down shouldn't kill the organism
                    continue

    def spawn_thread(self, name: str, target: Callable[[], None], daemon: bool = True) -> threading.Thread:
        """Spawn a managed daemon thread. Tracked for graceful shutdown."""
        t = threading.Thread(target=target, name=name, daemon=daemon)
        self._threads.append(t)
        t.start()
        return t

    # ═══════════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════════

    @property
    def phase(self) -> LifecyclePhase:
        return self._phase

    @property
    def is_running(self) -> bool:
        return self._phase == LifecyclePhase.RUNNING

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def home_dir(self) -> Path:
        return self._home

    @property
    def project_root(self) -> Path:
        return self._project_root

    @property
    def headless(self) -> bool:
        return self._headless

    @property
    def organ_count(self) -> int:
        return len(self._organs)

    @property
    def healthy_count(self) -> int:
        return len(self.get_healthy_organs())

    @property
    def unhealthy_count(self) -> int:
        return len(self.get_unhealthy_organs())
