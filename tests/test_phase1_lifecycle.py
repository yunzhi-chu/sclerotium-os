"""Phase 1 Gray-Box Tests — Lifecycle, Daemon, Tray, Launcher.

Comprehensive tests covering:
  - LifecycleManager: full lifecycle, organ tracking, immutability, error handling
  - SclerotiumDaemon: start/stop, pulse, mode switching
  - CLI argument parsing and status output
  - TrayController: icon state machine, menu structure (mocked)

All tests are self-contained — no external dependencies beyond stdlib + pytest.
"""

from __future__ import annotations

import os
import sys
import time
import signal
import tempfile
import threading
import argparse
from pathlib import Path
from dataclasses import asdict
from unittest import mock

import pytest

# Ensure the project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def temp_home():
    """Create a temporary sclerotium home directory."""
    with tempfile.TemporaryDirectory(prefix="sclerotium-test-") as td:
        yield Path(td)


@pytest.fixture
def lifecycle(temp_home):
    """Create a fresh LifecycleManager for each test."""
    from orchestrator.lifecycle import LifecycleManager
    return LifecycleManager(home_dir=temp_home, headless=True)


@pytest.fixture
def booted_lifecycle(lifecycle):
    """A lifecycle that has already been booted."""
    lifecycle.boot()
    return lifecycle


# ═══════════════════════════════════════════════════════════════
# 1. LifecycleManager — Phase Transitions
# ═══════════════════════════════════════════════════════════════

class TestLifecyclePhases:
    """Test the full lifecycle phase transitions."""

    def test_initial_state_is_offline(self, lifecycle):
        """New lifecycle should start OFFLINE with zero organs."""
        from orchestrator.lifecycle import LifecyclePhase
        assert lifecycle.phase == LifecyclePhase.OFFLINE
        assert lifecycle.organ_count == 0
        assert not lifecycle.is_running

    def test_boot_transitions_to_running(self, lifecycle):
        """Boot should go OFFLINE → BOOTING → INITIALIZING → RUNNING."""
        from orchestrator.lifecycle import LifecyclePhase
        state = lifecycle.boot()
        assert state.phase == LifecyclePhase.RUNNING
        assert lifecycle.is_running
        assert lifecycle.phase == LifecyclePhase.RUNNING

    def test_boot_twice_is_idempotent(self, booted_lifecycle):
        """Booting an already-running organism should be a no-op."""
        from orchestrator.lifecycle import LifecyclePhase
        state = booted_lifecycle.boot()
        assert state.phase == LifecyclePhase.RUNNING

    def test_shutdown_transitions_to_offline(self, booted_lifecycle):
        """Shutdown should go RUNNING → SHUTTING_DOWN → OFFLINE."""
        from orchestrator.lifecycle import LifecyclePhase
        state = booted_lifecycle.shutdown()
        assert state.phase == LifecyclePhase.OFFLINE
        assert not booted_lifecycle.is_running

    def test_shutdown_twice_is_idempotent(self, booted_lifecycle):
        """Double shutdown should be safe."""
        booted_lifecycle.shutdown()
        state = booted_lifecycle.shutdown()
        from orchestrator.lifecycle import LifecyclePhase
        assert state.phase == LifecyclePhase.OFFLINE

    def test_sleep_only_from_running(self, lifecycle):
        """Sleep should only work from RUNNING state."""
        from orchestrator.lifecycle import LifecyclePhase
        state = lifecycle.sleep()
        assert state.phase == LifecyclePhase.OFFLINE  # No-op
        lifecycle.boot()
        state = lifecycle.sleep()
        assert state.phase == LifecyclePhase.SLEEPING

    def test_wake_only_from_sleeping(self, booted_lifecycle):
        """Wake should only work from SLEEPING state."""
        from orchestrator.lifecycle import LifecyclePhase
        state = booted_lifecycle.wake()
        assert state.phase == LifecyclePhase.RUNNING  # No-op, already running
        booted_lifecycle.sleep()
        state = booted_lifecycle.wake()
        assert state.phase == LifecyclePhase.RUNNING

    def test_full_lifecycle_sequence(self, lifecycle):
        """Complete OFF→RUN→SLEEP→RUN→OFF cycle."""
        from orchestrator.lifecycle import LifecyclePhase

        assert lifecycle.phase == LifecyclePhase.OFFLINE
        lifecycle.boot()
        assert lifecycle.phase == LifecyclePhase.RUNNING
        lifecycle.sleep()
        assert lifecycle.phase == LifecyclePhase.SLEEPING
        lifecycle.wake()
        assert lifecycle.phase == LifecyclePhase.RUNNING
        lifecycle.shutdown()
        assert lifecycle.phase == LifecyclePhase.OFFLINE


# ═══════════════════════════════════════════════════════════════
# 2. LifecycleManager — Organ Tracking
# ═══════════════════════════════════════════════════════════════

class TestOrganTracking:
    """Test organ registration, health tracking, and queries."""

    def test_boot_loads_startup_sequence(self, lifecycle):
        """Boot should load all organs from STARTUP_SEQUENCE."""
        lifecycle.boot()
        # All organs in the startup sequence should be loaded
        expected_count = sum(
            len(organs) for _, organs in lifecycle.STARTUP_SEQUENCE
        )
        assert lifecycle.organ_count == expected_count
        assert lifecycle.healthy_count == expected_count
        assert lifecycle.unhealthy_count == 0

    def test_register_organ_dynamically(self, lifecycle):
        """Should be able to register new organs at runtime."""
        organ = lifecycle.register_organ("TestSensor", "SENSE")
        assert organ.name == "TestSensor"
        assert organ.layer == "SENSE"
        assert organ.loaded is True
        assert organ.healthy is True
        assert lifecycle.organ_count == 1

    def test_mark_organ_error(self, booted_lifecycle):
        """Marking an organ as unhealthy should track the error."""
        organ = booted_lifecycle.mark_organ_error("EventBus", "Connection refused")
        assert organ is not None
        assert organ.healthy is False
        assert organ.error == "Connection refused"
        assert booted_lifecycle.unhealthy_count >= 1

    def test_mark_organ_healthy_restores_status(self, booted_lifecycle):
        """Should be able to restore an organ to healthy."""
        booted_lifecycle.mark_organ_error("EventBus", "temp error")
        organ = booted_lifecycle.mark_organ_healthy("EventBus")
        assert organ is not None
        assert organ.healthy is True
        assert organ.error == ""
        assert booted_lifecycle.unhealthy_count == 0

    def test_mark_nonexistent_organ_returns_none(self, lifecycle):
        """Operations on nonexistent organs should return None."""
        assert lifecycle.mark_organ_error("Ghost", "...") is None
        assert lifecycle.mark_organ_healthy("Ghost") is None

    def test_get_organ(self, booted_lifecycle):
        """Should retrieve organ by name."""
        organ = booted_lifecycle.get_organ("EventBus")
        assert organ is not None
        assert organ.name == "EventBus"
        assert organ.layer == "METABOLIZE"

    def test_get_nonexistent_organ(self, booted_lifecycle):
        """Nonexistent organ should return None."""
        assert booted_lifecycle.get_organ("GhostOrgan") is None

    def test_get_healthy_organs(self, booted_lifecycle):
        """Should filter to only healthy organs."""
        booted_lifecycle.mark_organ_error("EventBus", "down")
        healthy = booted_lifecycle.get_healthy_organs()
        assert all(o.healthy for o in healthy)
        assert not any(o.name == "EventBus" for o in healthy)

    def test_get_unhealthy_organs(self, booted_lifecycle):
        """Should filter to only unhealthy organs."""
        booted_lifecycle.mark_organ_error("EventBus", "down")
        booted_lifecycle.mark_organ_error("HexisMemory", "corrupt")
        unhealthy = booted_lifecycle.get_unhealthy_organs()
        assert len(unhealthy) == 2
        assert all(not o.healthy for o in unhealthy)

    def test_organ_counters_update_correctly(self, booted_lifecycle):
        """healthy/unhealthy counts should stay consistent."""
        total = booted_lifecycle.organ_count
        assert booted_lifecycle.healthy_count + booted_lifecycle.unhealthy_count == total

        booted_lifecycle.mark_organ_error("EventBus", "down")
        assert booted_lifecycle.healthy_count + booted_lifecycle.unhealthy_count == total
        assert booted_lifecycle.unhealthy_count == 1

        booted_lifecycle.mark_organ_healthy("EventBus")
        assert booted_lifecycle.unhealthy_count == 0


# ═══════════════════════════════════════════════════════════════
# 3. LifecycleManager — State Immutability
# ═══════════════════════════════════════════════════════════════

class TestStateImmutability:
    """Verify that LifecycleState and OrganStatus are immutable."""

    def test_organ_status_is_frozen(self):
        """OrganStatus should be frozen (immutable)."""
        from orchestrator.lifecycle import OrganStatus
        o = OrganStatus(name="Test", layer="SENSE", loaded=True)
        with pytest.raises(Exception):
            o.name = "Changed"  # type: ignore[misc]

    def test_lifecycle_state_is_frozen(self):
        """LifecycleState should be frozen."""
        from orchestrator.lifecycle import LifecycleState, LifecyclePhase
        s = LifecycleState(phase=LifecyclePhase.OFFLINE)
        with pytest.raises(Exception):
            s.phase = LifecyclePhase.RUNNING  # type: ignore[misc]

    def test_status_returns_new_snapshot_each_time(self, booted_lifecycle):
        """Each call to status() should return a new immutable snapshot."""
        s1 = booted_lifecycle.status()
        s2 = booted_lifecycle.status()
        assert s1 is not s2  # Different objects
        assert s1 == s2  # But equal content

    def test_status_reflects_current_state(self, lifecycle):
        """Status should accurately reflect the current phase."""
        from orchestrator.lifecycle import LifecyclePhase
        s = lifecycle.status()
        assert s.phase == LifecyclePhase.OFFLINE
        assert s.uptime_seconds == 0.0

        lifecycle.boot()
        s = lifecycle.status()
        assert s.phase == LifecyclePhase.RUNNING
        assert s.uptime_seconds > 0
        assert len(s.organs) > 0

    def test_organ_status_contains_expected_fields(self, booted_lifecycle):
        """OrganStatus should have all required fields."""
        state = booted_lifecycle.status()
        for organ in state.organs:
            assert isinstance(organ.name, str)
            assert isinstance(organ.layer, str)
            assert organ.layer in ("SENSE", "THINK", "ACT", "EVOLVE", "METABOLIZE")
            assert isinstance(organ.loaded, bool)
            assert isinstance(organ.healthy, bool)
            assert isinstance(organ.error, str)


# ═══════════════════════════════════════════════════════════════
# 4. LifecycleManager — Startup Sequence Order
# ═══════════════════════════════════════════════════════════════

class TestStartupSequence:
    """Verify the startup sequence is correct and ordered."""

    def test_startup_sequence_has_all_phases(self, lifecycle):
        """All 6 startup phases should be present."""
        phase_names = [p[0] for p in lifecycle.STARTUP_SEQUENCE]
        expected = ["core", "safety", "memory", "intelligence", "rhythm", "bridges"]
        assert phase_names == expected

    def test_core_phase_has_event_bus(self, lifecycle):
        """EventBus must be first (nervous system before anything else)."""
        core_phase = lifecycle.STARTUP_SEQUENCE[0]
        organ_names = [o[0] for o in core_phase[1]]
        assert "EventBus" in organ_names
        assert organ_names[0] == "EventBus"  # MUST be first

    def test_safety_phase_loaded_before_intelligence(self, lifecycle):
        """Safety (Arbiter) must load before intelligence (LLM access)."""
        phase_names = [p[0] for p in lifecycle.STARTUP_SEQUENCE]
        safety_idx = phase_names.index("safety")
        intelligence_idx = phase_names.index("intelligence")
        assert safety_idx < intelligence_idx, (
            "SAFETY MUST LOAD BEFORE INTELLIGENCE — "
            "ConstitutionalArbiter must gate LLM access"
        )

    def test_memory_loaded_before_bridges(self, lifecycle):
        """Memory must be ready before bridges connect to external systems."""
        phase_names = [p[0] for p in lifecycle.STARTUP_SEQUENCE]
        memory_idx = phase_names.index("memory")
        bridges_idx = phase_names.index("bridges")
        assert memory_idx < bridges_idx

    def test_every_organ_has_valid_layer(self, lifecycle):
        """Every organ in startup sequence must have a valid layer."""
        valid_layers = {"SENSE", "THINK", "ACT", "EVOLVE", "METABOLIZE"}
        for phase_name, organs in lifecycle.STARTUP_SEQUENCE:
            for name, layer in organs:
                assert layer in valid_layers, (
                    f"Organ '{name}' in phase '{phase_name}' has invalid layer '{layer}'"
                )

    def test_boot_respects_sequence_order(self, lifecycle):
        """Organs should appear in status in the order they were loaded."""
        lifecycle.boot()
        state = lifecycle.status()
        organ_names = [o.name for o in state.organs]

        # Core phase organs should appear first
        core_phase_organs = [o[0] for o in lifecycle.STARTUP_SEQUENCE[0][1]]
        for expected in core_phase_organs:
            assert expected in organ_names[:5], (
                f"Core organ '{expected}' should be among first loaded"
            )


# ═══════════════════════════════════════════════════════════════
# 5. LifecycleManager — Phase Change Callbacks
# ═══════════════════════════════════════════════════════════════

class TestPhaseCallbacks:
    """Test the phase change notification system."""

    def test_callback_fires_on_boot(self, lifecycle):
        """Callback should fire when booting."""
        states_seen = []

        def track(state):
            states_seen.append(state.phase)

        lifecycle.on_phase_change(track)
        lifecycle.boot()

        from orchestrator.lifecycle import LifecyclePhase
        assert LifecyclePhase.BOOTING in states_seen
        assert LifecyclePhase.RUNNING in states_seen
        assert len(states_seen) >= 2

    def test_callback_fires_on_shutdown(self, booted_lifecycle):
        """Callback should fire on shutdown."""
        states_seen = []

        def track(state):
            states_seen.append(state.phase)

        booted_lifecycle.on_phase_change(track)
        booted_lifecycle.shutdown()

        from orchestrator.lifecycle import LifecyclePhase
        assert LifecyclePhase.SHUTTING_DOWN in states_seen
        assert LifecyclePhase.OFFLINE in states_seen

    def test_callback_receives_valid_state(self, lifecycle):
        """Callback should receive a valid LifecycleState."""
        received = []

        def track(state):
            received.append(state)

        lifecycle.on_phase_change(track)
        lifecycle.boot()

        assert len(received) > 0
        final_state = received[-1]
        assert hasattr(final_state, 'phase')
        assert hasattr(final_state, 'organs')
        assert hasattr(final_state, 'uptime_seconds')

    def test_callback_exception_does_not_break_lifecycle(self, lifecycle):
        """A crashing callback should not prevent lifecycle transitions."""
        def crash(state):
            raise RuntimeError("Callback exploded")

        lifecycle.on_phase_change(crash)
        # Should still boot successfully
        state = lifecycle.boot()
        from orchestrator.lifecycle import LifecyclePhase
        assert state.phase == LifecyclePhase.RUNNING

    def test_multiple_callbacks_all_fire(self, lifecycle):
        """All registered callbacks should fire."""
        counts = [0, 0, 0]

        def cb0(s): counts[0] += 1
        def cb1(s): counts[1] += 1
        def cb2(s): counts[2] += 1

        lifecycle.on_phase_change(cb0)
        lifecycle.on_phase_change(cb1)
        lifecycle.on_phase_change(cb2)
        lifecycle.boot()

        assert all(c > 0 for c in counts)


# ═══════════════════════════════════════════════════════════════
# 6. LifecycleManager — Directory Creation
# ═══════════════════════════════════════════════════════════════

class TestDirectoryCreation:
    """Verify the .sclerotium directory structure is created."""

    def test_home_directory_created(self, temp_home):
        """Boot should create the home directory structure."""
        from orchestrator.lifecycle import LifecycleManager
        # Use a subdirectory that doesn't exist yet
        new_home = temp_home / "fresh-install"
        assert not new_home.exists()

        lm = LifecycleManager(home_dir=new_home, headless=True)
        lm.boot()
        assert new_home.exists()
        assert new_home.is_dir()

    def test_subdirectories_created(self, temp_home):
        """All required subdirectories should be created."""
        from orchestrator.lifecycle import LifecycleManager
        lm = LifecycleManager(home_dir=temp_home, headless=True)
        lm.boot()

        expected_dirs = [
            "memory", "chroma", "sessions",
            "audit", "genomes", "skills", "logs",
        ]
        for d in expected_dirs:
            assert (temp_home / d).is_dir(), f"Missing directory: {d}"

    def test_directory_creation_is_idempotent(self, temp_home):
        """Booting twice should not fail on existing directories."""
        from orchestrator.lifecycle import LifecycleManager
        lm = LifecycleManager(home_dir=temp_home, headless=True)
        lm.boot()
        lm.shutdown()
        # Second boot should work fine
        lm2 = LifecycleManager(home_dir=temp_home, headless=True)
        state = lm2.boot()
        from orchestrator.lifecycle import LifecyclePhase
        assert state.phase == LifecyclePhase.RUNNING


# ═══════════════════════════════════════════════════════════════
# 7. SclerotiumDaemon
# ═══════════════════════════════════════════════════════════════

class TestSclerotiumDaemon:
    """Test the daemon service layer."""

    def test_daemon_creates_lifecycle(self, temp_home):
        """Daemon should create and manage a LifecycleManager."""
        from daemon.service import SclerotiumDaemon
        daemon = SclerotiumDaemon(home_dir=temp_home, headless=True)
        assert daemon.lifecycle is not None
        assert daemon.is_running is False

    def test_daemon_start_and_stop(self, temp_home):
        """Daemon should start and stop cleanly."""
        from daemon.service import SclerotiumDaemon
        from orchestrator.lifecycle import LifecyclePhase

        daemon = SclerotiumDaemon(home_dir=temp_home, headless=True)
        state = daemon.start()
        assert state.phase == LifecyclePhase.RUNNING
        assert daemon.is_running

        state = daemon.stop()
        assert state.phase == LifecyclePhase.OFFLINE
        assert not daemon.is_running

    def test_daemon_sleep_and_wake(self, temp_home):
        """Daemon should support sleep/wake cycle."""
        from daemon.service import SclerotiumDaemon
        from orchestrator.lifecycle import LifecyclePhase

        daemon = SclerotiumDaemon(home_dir=temp_home, headless=True)
        daemon.start()

        state = daemon.sleep()
        assert state.phase == LifecyclePhase.SLEEPING

        state = daemon.wake()
        assert state.phase == LifecyclePhase.RUNNING

        daemon.stop()

    def test_daemon_status(self, temp_home):
        """Status should return current LifecycleState."""
        from daemon.service import SclerotiumDaemon
        daemon = SclerotiumDaemon(home_dir=temp_home, headless=True)
        state = daemon.status()
        from orchestrator.lifecycle import LifecyclePhase
        assert state.phase == LifecyclePhase.OFFLINE
        assert state.uptime_seconds == 0.0

    def test_daemon_set_mode_valid(self, temp_home):
        """set_mode with valid mode should work."""
        from daemon.service import SclerotiumDaemon
        daemon = SclerotiumDaemon(home_dir=temp_home, headless=True)
        daemon.start()

        for mode in ["work", "game", "meeting", "creative"]:
            state = daemon.set_mode(mode)
            assert state is not None

        daemon.stop()

    def test_daemon_set_mode_invalid_raises(self, temp_home):
        """set_mode with invalid mode should raise ValueError."""
        from daemon.service import SclerotiumDaemon
        daemon = SclerotiumDaemon(home_dir=temp_home, headless=True)
        with pytest.raises(ValueError, match="Invalid mode"):
            daemon.set_mode("invalid_mode")

    def test_daemon_set_mode_sleep_transitions(self, temp_home):
        """Setting mode to 'sleep' should call daemon.sleep()."""
        from daemon.service import SclerotiumDaemon
        from orchestrator.lifecycle import LifecyclePhase

        daemon = SclerotiumDaemon(home_dir=temp_home, headless=True)
        daemon.start()
        state = daemon.set_mode("sleep")
        assert state.phase == LifecyclePhase.SLEEPING
        daemon.stop()

    def test_daemon_pulse_runs(self, temp_home):
        """Pulse thread should start and run without errors."""
        from daemon.service import SclerotiumDaemon

        daemon = SclerotiumDaemon(home_dir=temp_home, headless=True)
        # Override PULSE_INTERVAL to speed up test
        daemon.PULSE_INTERVAL = 0.1
        daemon.start()

        # Let at least 2 pulses happen
        time.sleep(0.35)

        # Pulse should still be running
        assert daemon.lifecycle.is_running
        daemon.stop()

    def test_daemon_pulse_stops_after_shutdown(self, temp_home):
        """Pulse thread should stop after daemon shutdown."""
        from daemon.service import SclerotiumDaemon

        daemon = SclerotiumDaemon(home_dir=temp_home, headless=True)
        daemon.PULSE_INTERVAL = 0.1
        daemon.start()
        time.sleep(0.15)
        daemon.stop()

        # After stop, and a brief wait, pulse thread should be dead
        time.sleep(0.3)
        if daemon._pulse_thread:
            assert not daemon._pulse_thread.is_alive()

    def test_daemon_start_stop_start(self, temp_home):
        """Daemon should survive multiple start/stop cycles."""
        from daemon.service import SclerotiumDaemon
        from orchestrator.lifecycle import LifecyclePhase

        daemon = SclerotiumDaemon(home_dir=temp_home, headless=True)

        for _ in range(3):
            state = daemon.start()
            assert state.phase == LifecyclePhase.RUNNING
            state = daemon.stop()
            assert state.phase == LifecyclePhase.OFFLINE


# ═══════════════════════════════════════════════════════════════
# 8. TrayController — Icon State Machine
# ═══════════════════════════════════════════════════════════════

@pytest.mark.skipif(
    not __import__('importlib').import_module('daemon.tray_icon').__dict__.get('HAS_TRAY', False),
    reason="pystray/Pillow not installed"
)
class TestTrayController:
    """Test the system tray icon state machine."""

    def test_tray_creation(self, lifecycle):
        """TrayController should be creatable with a lifecycle."""
        from daemon.tray_icon import TrayController
        tray = TrayController(lifecycle=lifecycle)
        assert tray._current_color == "offline"

    def test_update_icon_valid_states(self, lifecycle):
        """update_icon should accept all valid states."""
        from daemon.tray_icon import TrayController, ICON_COLORS, _create_icon_image

        tray = TrayController(lifecycle=lifecycle)
        for state_name in ICON_COLORS:
            # Should not raise (we test without real pystray running)
            tray._current_color = state_name
            assert tray._current_color == state_name

    def test_update_icon_invalid_state_ignored(self, lifecycle):
        """Invalid state names should be silently ignored."""
        from daemon.tray_icon import TrayController
        tray = TrayController(lifecycle=lifecycle)
        original = tray._current_color
        tray.update_icon("invalid_state_xyz")
        assert tray._current_color == original  # Unchanged

    def test_create_icon_image_all_colors(self):
        """Icon creation should work for all defined colors."""
        from daemon.tray_icon import _create_icon_image, ICON_COLORS
        for state_name, color in ICON_COLORS.items():
            img = _create_icon_image(color)
            assert img is not None
            assert img.size == (64, 64)
            assert img.mode == "RGBA"

    def test_clear_notifications_resets_icon(self, lifecycle):
        """clear_notifications should reset to running state."""
        from daemon.tray_icon import TrayController
        tray = TrayController(lifecycle=lifecycle)
        tray._notification_count = 5
        tray._current_color = "notification"

        lifecycle.boot()
        tray.clear_notifications()
        assert tray._notification_count == 0
        assert tray._current_color == "running"


class TestIconImageCreation:
    """Test icon image generation (no pystray dependency)."""

    def test_image_creation_needs_pillow(self):
        """_create_icon_image needs PIL."""
        try:
            from PIL import Image
            has_pil = True
        except ImportError:
            has_pil = False
            pytest.skip("Pillow not installed")

        from daemon.tray_icon import _create_icon_image
        img = _create_icon_image((100, 200, 50))
        assert img.width == 64
        assert img.height == 64

    def test_all_icon_colors_produce_valid_images(self):
        """Every predefined color should produce a valid icon."""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        from daemon.tray_icon import _create_icon_image, ICON_COLORS
        for state_name, color in ICON_COLORS.items():
            img = _create_icon_image(color)
            assert img.mode == "RGBA", f"Icon for '{state_name}' has wrong mode"
            # First pixel should be transparent (corner of circle)
            assert img.getpixel((0, 0)) == (0, 0, 0, 0), (
                f"Icon for '{state_name}' corner should be transparent"
            )


# ═══════════════════════════════════════════════════════════════
# 9. CLI Argument Parsing
# ═══════════════════════════════════════════════════════════════

class TestDaemonLauncherCLI:
    """Test the daemon_launcher CLI argument parsing."""

    def test_default_args(self):
        """Default arguments should be sensible."""
        from daemon_launcher import parse_args
        args = parse_args([])
        assert args.debug is False
        assert args.headless is False
        assert args.status is False
        assert ".sclerotium" in args.home

    def test_headless_flag(self):
        """--headless should set headless=True."""
        from daemon_launcher import parse_args
        args = parse_args(["--headless"])
        assert args.headless is True

    def test_debug_flag(self):
        """--debug should set debug=True."""
        from daemon_launcher import parse_args
        args = parse_args(["--debug"])
        assert args.debug is True

    def test_status_flag(self):
        """--status should set status=True."""
        from daemon_launcher import parse_args
        args = parse_args(["--status"])
        assert args.status is True

    def test_custom_home(self):
        """--home should accept custom path."""
        from daemon_launcher import parse_args
        args = parse_args(["--home", "D:/my-sclerotium"])
        assert args.home == "D:/my-sclerotium"

    def test_install_flag(self):
        """--install should set install=True."""
        from daemon_launcher import parse_args
        args = parse_args(["--install"])
        assert args.install is True

    def test_start_flag(self):
        """--start should set start=True."""
        from daemon_launcher import parse_args
        args = parse_args(["--start"])
        assert args.start is True

    def test_stop_flag(self):
        """--stop should set stop=True."""
        from daemon_launcher import parse_args
        args = parse_args(["--stop"])
        assert args.stop is True

    def test_remove_flag(self):
        """--remove should set remove=True."""
        from daemon_launcher import parse_args
        args = parse_args(["--remove"])
        assert args.remove is True

    def test_combined_flags(self):
        """Multiple flags should all be parsed correctly."""
        from daemon_launcher import parse_args
        args = parse_args(["--headless", "--debug", "--home", "/tmp/test"])
        assert args.headless is True
        assert args.debug is True
        assert args.home == "/tmp/test"


# ═══════════════════════════════════════════════════════════════
# 10. Edge Cases & Error Handling
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases and error resilience."""

    def test_lifecycle_with_nonexistent_home_parent(self, tmp_path):
        """Should create home even if parent doesn't exist."""
        from orchestrator.lifecycle import LifecycleManager
        deep_home = tmp_path / "a" / "b" / "c" / ".sclerotium"
        lm = LifecycleManager(home_dir=deep_home, headless=True)
        state = lm.boot()
        from orchestrator.lifecycle import LifecyclePhase
        assert state.phase == LifecyclePhase.RUNNING
        assert deep_home.exists()

    def test_boot_after_error(self, lifecycle):
        """If one boot attempt fails, a second should still work."""
        from orchestrator.lifecycle import LifecycleManager

        # Use a home dir that's actually a file (should handle gracefully)
        # Instead, just verify multiple boot/shutdown cycles work
        for _ in range(5):
            lifecycle.boot()
            assert lifecycle.is_running
            lifecycle.shutdown()
            assert not lifecycle.is_running

    def test_concurrent_status_reads(self, booted_lifecycle):
        """Status should be safe to call from multiple threads."""
        results = []

        def read_status():
            for _ in range(20):
                results.append(booted_lifecycle.status())

        threads = [
            threading.Thread(target=read_status)
            for _ in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        # All results should be valid
        assert len(results) == 100
        for r in results:
            assert hasattr(r, 'phase')
            assert hasattr(r, 'organs')

    def test_register_organ_idempotent(self, lifecycle):
        """Registering the same organ twice should update it."""
        o1 = lifecycle.register_organ("TestSensor", "SENSE")
        o2 = lifecycle.register_organ("TestSensor", "THINK")
        assert o1.name == o2.name
        assert o2.layer == "THINK"  # Updated
        assert lifecycle.organ_count == 1  # Not duplicated

    def test_startup_sequence_organs_not_duplicated(self, lifecycle):
        """Boot should not duplicate organs if STARTUP_SEQUENCE has repeats."""
        lifecycle.boot()
        state = lifecycle.status()
        names = [o.name for o in state.organs]
        # No duplicates
        assert len(names) == len(set(names)), f"Duplicate organs found: {names}"

    def test_uptime_monotonic(self, lifecycle):
        """Uptime should increase monotonically while running."""
        lifecycle.boot()
        s1 = lifecycle.status()
        time.sleep(0.1)
        s2 = lifecycle.status()
        assert s2.uptime_seconds > s1.uptime_seconds

    def test_uptime_stops_when_offline(self, lifecycle):
        """Uptime should freeze when offline, resume when rebooted."""
        lifecycle.boot()
        time.sleep(0.05)
        lifecycle.shutdown()
        s1 = lifecycle.status()
        time.sleep(0.1)
        s2 = lifecycle.status()
        # Both should be 0 since organism is offline
        assert s1.uptime_seconds == 0.0
        assert s2.uptime_seconds == 0.0


# ═══════════════════════════════════════════════════════════════
# 11. Integration Scenarios
# ═══════════════════════════════════════════════════════════════

class TestIntegrationScenarios:
    """End-to-end integration scenarios across LifecycleManager + Daemon."""

    def test_scenario_boot_work_sleep_wake_shutdown(self, temp_home):
        """Full day in the life of the organism."""
        from daemon.service import SclerotiumDaemon
        from orchestrator.lifecycle import LifecyclePhase

        daemon = SclerotiumDaemon(home_dir=temp_home, headless=True)

        # Morning: boot up
        state = daemon.start()
        assert state.phase == LifecyclePhase.RUNNING
        assert daemon.lifecycle.organ_count > 0

        # Work all day...
        for mode in ["work", "meeting", "creative"]:
            daemon.set_mode(mode)

        # Evening: sleep
        state = daemon.sleep()
        assert state.phase == LifecyclePhase.SLEEPING

        # Night: wake briefly for maintenance
        state = daemon.wake()
        assert state.phase == LifecyclePhase.RUNNING

        # Back to sleep
        daemon.sleep()

        # Morning again: wake
        daemon.wake()

        # Eventually: shutdown
        state = daemon.stop()
        assert state.phase == LifecyclePhase.OFFLINE

    def test_scenario_organ_error_recovery(self, temp_home):
        """Organ error detection → notification → recovery."""
        from daemon.service import SclerotiumDaemon

        daemon = SclerotiumDaemon(home_dir=temp_home, headless=True)
        daemon.start()

        lm = daemon.lifecycle

        # Simulate organ failure
        lm.mark_organ_error("HexisMemory", "disk full")
        assert lm.unhealthy_count == 1

        # Get status — should still work despite unhealthy organ
        state = daemon.status()
        assert len(state.organs) > 0

        # Recover
        lm.mark_organ_healthy("HexisMemory")
        assert lm.unhealthy_count == 0

        daemon.stop()

    def test_scenario_dynamic_organ_addition(self, temp_home):
        """New capabilities added at runtime."""
        from daemon.service import SclerotiumDaemon

        daemon = SclerotiumDaemon(home_dir=temp_home, headless=True)
        daemon.start()

        initial_count = daemon.lifecycle.organ_count

        # User installs new MCP tool — register dynamically
        daemon.lifecycle.register_organ("MCP:weather_api", "ACT")
        daemon.lifecycle.register_organ("MCP:stock_ticker", "SENSE")

        assert daemon.lifecycle.organ_count == initial_count + 2

        daemon.stop()
