"""Sclerotium OS Daemon Service.

Runs as a Windows service or foreground process. Manages the organism's
lifecycle — boot, run, sleep, shutdown.

Usage:
    # As foreground process (debug mode)
    python -m daemon.service --debug

    # As Windows service
    python -m daemon.service --install
    python -m daemon.service --start
    python -m daemon.service --stop
"""

from __future__ import annotations

import os
import sys
import time
import threading
import logging
from pathlib import Path
from typing import Any

from orchestrator.lifecycle import (
    LifecycleManager,
    LifecyclePhase,
    LifecycleState,
)

logger = logging.getLogger("sclerotium.daemon")

# Windows service support (optional)
try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    HAS_WIN32_SERVICE = True
except ImportError:
    HAS_WIN32_SERVICE = False


# ═══════════════════════════════════════════════════════════════
# Organism Daemon
# ═══════════════════════════════════════════════════════════════

class SclerotiumDaemon:
    """The organism's body — keeps it alive across sessions.

    Manages:
      - Lifecycle (boot → run → sleep → shutdown)
      - System tray (optional, non-headless mode)
      - Pulse thread (periodic health checks)
      - Signal handling
    """

    PULSE_INTERVAL = 30.0  # seconds between health pulses

    def __init__(
        self,
        home_dir: str | Path = "~/.sclerotium",
        project_root: str | Path | None = None,
        headless: bool = False,
        mode: str = "work",
    ) -> None:
        if project_root is None:
            project_root = Path(__file__).resolve().parent.parent
        self._lifecycle = LifecycleManager(
            home_dir=home_dir,
            project_root=Path(project_root),
            headless=headless,
        )
        self._headless = headless
        self._initial_mode = mode
        self._pulse_thread: threading.Thread | None = None
        self._tray: Any = None  # System tray (set by launcher)

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def start(self) -> LifecycleState:
        """Start the organism. Blocks until shutdown in foreground mode."""
        state = self._lifecycle.boot()
        logger.info(
            "Organism alive — %d organs, phase=%s, uptime=%.1fs",
            self._lifecycle.organ_count,
            state.phase.value,
            state.uptime_seconds,
        )
        self._start_pulse()
        return state

    def stop(self) -> LifecycleState:
        """Stop the organism gracefully."""
        logger.info("Shutting down organism...")
        self._stop_pulse()
        state = self._lifecycle.shutdown()
        logger.info("Organism offline.")
        return state

    def status(self) -> LifecycleState:
        """Get current organism state."""
        return self._lifecycle.status()

    def sleep(self) -> LifecycleState:
        """Put the organism to sleep."""
        self._stop_pulse()
        return self._lifecycle.sleep()

    def wake(self) -> LifecycleState:
        """Wake the organism from sleep."""
        state = self._lifecycle.wake()
        if state.phase == LifecyclePhase.RUNNING:
            self._start_pulse()
        return state

    def set_mode(self, mode: str) -> LifecycleState:
        """Switch the organism's operating mode."""
        valid_modes = {"work", "sleep", "game", "meeting", "creative"}
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode: {mode}. Must be one of {valid_modes}")
        if mode == "sleep":
            return self.sleep()
        if self._lifecycle.phase == LifecyclePhase.SLEEPING:
            self.wake()
        # Mode is stored in lifecycle state — will be read by rhythm engine
        return self._lifecycle.status()

    def run_forever(self) -> None:
        """Run the organism in the foreground. Blocks until shutdown signal."""
        try:
            state = self.start()
            logger.info("Organism running. Press Ctrl+C to stop.")
            # Main loop: just sleep and pulse
            while self._lifecycle.is_running:
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received.")
        finally:
            self.stop()

    # ═══════════════════════════════════════════════════════
    # Pulse (heartbeat)
    # ═══════════════════════════════════════════════════════

    def _start_pulse(self) -> None:
        """Start the periodic health pulse thread."""
        if self._pulse_thread and self._pulse_thread.is_alive():
            return
        self._pulse_thread = threading.Thread(
            target=self._pulse_loop,
            name="sclerotium-pulse",
            daemon=True,
        )
        self._pulse_thread.start()

    def _stop_pulse(self) -> None:
        """Stop the pulse thread."""
        if self._pulse_thread and self._pulse_thread.is_alive():
            self._pulse_thread.join(timeout=5.0)
            self._pulse_thread = None

    def _pulse_loop(self) -> None:
        """Periodic health check loop."""
        while self._lifecycle.is_running:
            time.sleep(self.PULSE_INTERVAL)
            if not self._lifecycle.is_running:
                break
            try:
                self._on_pulse()
            except Exception as e:
                logger.warning("Pulse check error: %s", e)

    def _on_pulse(self) -> None:
        """Called every PULSE_INTERVAL seconds while running.

        Override or extend this to add periodic tasks:
          - Update tray icon
          - Check organ health
          - Report status to EventBus
        """
        state = self._lifecycle.status()
        unhealthy = self._lifecycle.unhealthy_count
        if unhealthy > 0:
            logger.warning(
                "Pulse: %d/%d organs unhealthy — %s",
                unhealthy,
                self._lifecycle.organ_count,
                [o.name for o in self._lifecycle.get_unhealthy_organs()],
            )
        else:
            logger.debug(
                "Pulse: all %d organs healthy, uptime=%.0fs, mode=%s",
                self._lifecycle.organ_count,
                state.uptime_seconds,
                state.mode,
            )

    # ═══════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════

    @property
    def lifecycle(self) -> LifecycleManager:
        return self._lifecycle

    @property
    def is_running(self) -> bool:
        return self._lifecycle.is_running

    @property
    def tray(self) -> Any:
        return self._tray

    @tray.setter
    def tray(self, tray: Any) -> None:
        self._tray = tray


# ═══════════════════════════════════════════════════════════════
# Windows Service Adapter
# ═══════════════════════════════════════════════════════════════

if HAS_WIN32_SERVICE:

    class SclerotiumWindowsService(win32serviceutil.ServiceFramework):
        """Windows Service wrapper for Sclerotium OS daemon."""

        _svc_name_ = "SclerotiumOS"
        _svc_display_name_ = "Sclerotium OS — Electronic Lifeform"
        _svc_description_ = (
            "Sclerotium OS daemon — an electronic organism that lives in "
            "your Windows system, perceives your work patterns, and evolves."
        )

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
            self._daemon: SclerotiumDaemon | None = None

        @classmethod
        def run_as_service(cls):
            """Run as Windows service (called by SCM or --service flag)."""
            win32serviceutil.HandleCommandLine(cls)

        def SvcStop(self):
            """Called when the service is requested to stop."""
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            if self._daemon:
                self._daemon.stop()
            win32event.SetEvent(self.hWaitStop)

        def SvcDoRun(self):
            """Main service entry point."""
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ''),
            )
            try:
                self._daemon = SclerotiumDaemon(headless=True)
                self._daemon.start()
                # Wait for stop signal
                win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
            except Exception as e:
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_ERROR_TYPE,
                    servicemanager.PYS_SERVICE_STOPPED,
                    (self._svc_name_, str(e)),
                )
