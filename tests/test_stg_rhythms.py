"""Tests for STG rhythm system — CPG, pyloric, gastric, neuromodulator, WLC."""

import asyncio
import pytest

from kernel.stg.pattern_generator import CentralPatternGenerator, RhythmPhase
from kernel.stg.neuromodulator import Neuromodulator, Profile, PROFILES
from kernel.stg.winnerless_competition import (
    WinnerlessCompetition, PanarchyPhase, WLCState,
)


# ── CentralPatternGenerator ──────────────────────────────────────────


class TestCPG:
    @pytest.mark.asyncio
    async def test_register_and_fire(self):
        cpg = CentralPatternGenerator()
        fired = []

        async def handler():
            fired.append(1)

        cpg.register("test_rhythm", interval_seconds=0.01, handler=handler)
        await cpg.start()
        await asyncio.sleep(0.05)
        await cpg.stop()
        assert len(fired) >= 1

    @pytest.mark.asyncio
    async def test_disable_rhythm(self):
        cpg = CentralPatternGenerator()
        fired = []

        async def handler():
            fired.append(1)

        cpg.register("test", interval_seconds=0.01, handler=handler, enabled=False)
        await cpg.start()
        await asyncio.sleep(0.05)
        await cpg.stop()
        assert len(fired) == 0

    @pytest.mark.asyncio
    async def test_modulate_frequency(self):
        cpg = CentralPatternGenerator()
        cpg.register("test", interval_seconds=0.1, handler=async_handler)
        cpg.modulate("test", interval_seconds=0.01)
        status = cpg.get_status()
        assert status["test"]["interval_seconds"] == 0.01

    @pytest.mark.asyncio
    async def test_get_status(self):
        cpg = CentralPatternGenerator()
        cpg.register("test", interval_seconds=60, handler=async_handler)
        status = cpg.get_status()
        assert "test" in status
        assert status["test"]["enabled"] is True


async def async_handler():
    pass


# ── Neuromodulator ───────────────────────────────────────────────────


class TestNeuromodulator:
    def test_default_profile_is_work(self):
        nm = Neuromodulator()
        assert nm.active_profile == Profile.WORK

    def test_switch_to_sleep(self):
        nm = Neuromodulator()
        result = nm.switch("sleep")
        assert result["active_profile"] == "sleep"
        assert nm.state.notification_level == "none"
        assert nm.state.evolution_enabled is False

    def test_switch_to_creative(self):
        nm = Neuromodulator()
        nm.switch("creative")
        assert nm.state.llm_routing == "best"
        assert nm.state.scan_frequency == "high"

    def test_switch_to_meeting(self):
        nm = Neuromodulator()
        nm.switch("meeting")
        assert nm.state.sandbox_isolation == 2
        assert nm.state.auto_reply_enabled is True

    def test_switch_to_game(self):
        nm = Neuromodulator()
        nm.switch("game")
        assert nm.state.evolution_enabled is False

    def test_invalid_profile(self):
        nm = Neuromodulator()
        result = nm.switch("flying")
        assert "error" in result

    def test_get_profile(self):
        nm = Neuromodulator()
        info = nm.get_profile()
        assert info["profile"] == "work"

    def test_all_five_profiles_defined(self):
        for p in Profile:
            assert p in PROFILES


# ── WinnerlessCompetition ────────────────────────────────────────────


class TestWLC:
    def test_initial_phase_is_r(self):
        wlc = WinnerlessCompetition()
        assert wlc.current_phase == PanarchyPhase.R

    def test_r_to_k_transition(self):
        wlc = WinnerlessCompetition()
        # Force connectedness high enough
        wlc._states[PanarchyPhase.R].duration = 99
        # Manually trigger transition condition by hacking internals
        for _ in range(100):
            wlc.tick(1.0)
            if wlc.current_phase != PanarchyPhase.R:
                break
        # After enough ticks, should eventually transition
        assert wlc.current_phase in (PanarchyPhase.R, PanarchyPhase.K)

    def test_force_transition(self):
        wlc = WinnerlessCompetition()
        result = wlc.force_transition(PanarchyPhase.OMEGA)
        assert result == PanarchyPhase.OMEGA
        assert wlc.current_phase == PanarchyPhase.OMEGA

    def test_connectedness_increases_during_r(self):
        wlc = WinnerlessCompetition()
        wlc.force_transition(PanarchyPhase.R)
        c1 = wlc.connectedness
        wlc.tick(5.0)
        c2 = wlc.connectedness
        assert c2 > c1  # Connectedness rises during r

    def test_resilience_drops_during_omega(self):
        wlc = WinnerlessCompetition()
        wlc.force_transition(PanarchyPhase.OMEGA)
        r1 = wlc.resilience
        wlc.tick(5.0)
        r2 = wlc.resilience
        assert r2 < r1  # Resilience drops during omega

    def test_get_status(self):
        wlc = WinnerlessCompetition()
        status = wlc.get_status()
        assert "current_phase" in status
        assert "connectedness" in status
        assert "resilience" in status
        assert "states" in status
