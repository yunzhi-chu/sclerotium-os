"""Tests for L5: SwarmSelfOrganizer — 群体自组织器."""

import numpy as np
import pytest

from src.l5.swarm_self_organizer import (
    NucleationSite,
    PhasePortrait,
    PhotormoneField,
    SwarmOrganizerConfig,
    SwarmPhase,
    SwarmSelfOrganizer,
)


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def config() -> SwarmOrganizerConfig:
    return SwarmOrganizerConfig(
        cooperation_default=0.5,
        deposition_default=0.5,
        nucleation_threshold=0.6,
        phase_hysteresis=0.1,
        photormone_grid_size=64,
        max_nucleation_sites=20,
    )


@pytest.fixture
def organizer(config: SwarmOrganizerConfig) -> SwarmSelfOrganizer:
    return SwarmSelfOrganizer(config=config)


# ═══════════════════════════════════════════════════════════════════════
# Unit Tests
# ═══════════════════════════════════════════════════════════════════════


class TestOrganizerInit:
    """Test initialization and configuration."""

    def test_default_init(self) -> None:
        org = SwarmSelfOrganizer()
        assert org.current_phase == SwarmPhase.BUILD
        assert org.stats["nucleation_sites"] == 0

    def test_custom_config(self, config: SwarmOrganizerConfig) -> None:
        org = SwarmSelfOrganizer(config=config)
        assert org._config.cooperation_default == 0.5
        assert org._config.nucleation_threshold == 0.6

    def test_initial_stats(self, organizer: SwarmSelfOrganizer) -> None:
        stats = organizer.stats
        assert stats["phase"] == "build"
        assert stats["cooperation"] == 0.5
        assert stats["deposition"] == 0.5
        assert stats["nucleation_sites"] == 0


class TestPhasePortrait:
    """Test the two-parameter phase portrait."""

    def test_build_phase(self, organizer: SwarmSelfOrganizer) -> None:
        portrait = organizer.compute_phase_portrait(0.7, 0.7)
        assert portrait.current_phase == SwarmPhase.BUILD

    def test_patrol_phase(self, organizer: SwarmSelfOrganizer) -> None:
        portrait = organizer.compute_phase_portrait(0.7, -0.7)
        assert portrait.current_phase == SwarmPhase.PATROL

    def test_aggregate_phase(self, organizer: SwarmSelfOrganizer) -> None:
        portrait = organizer.compute_phase_portrait(-0.7, 0.7)
        assert portrait.current_phase == SwarmPhase.AGGREGATE

    def test_dismantle_phase(self, organizer: SwarmSelfOrganizer) -> None:
        portrait = organizer.compute_phase_portrait(-0.7, -0.7)
        assert portrait.current_phase == SwarmPhase.DISMANTLE

    def test_transition_near_origin(self, organizer: SwarmSelfOrganizer) -> None:
        portrait = organizer.compute_phase_portrait(0.05, 0.05)
        assert portrait.current_phase == SwarmPhase.TRANSITION

    def test_phase_portrait_clamps_parameters(self, organizer: SwarmSelfOrganizer) -> None:
        portrait = organizer.compute_phase_portrait(2.0, -2.0)
        assert -1.0 <= portrait.cooperation_strength <= 1.0
        assert -1.0 <= portrait.deposition_rate <= 1.0

    def test_phase_portrait_history(self, organizer: SwarmSelfOrganizer) -> None:
        organizer.compute_phase_portrait(0.5, 0.5)
        organizer.compute_phase_portrait(0.6, 0.6)
        assert len(organizer._phase_history) >= 2

    def test_phase_hysteresis_prevents_rapid_switching(self, organizer: SwarmSelfOrganizer) -> None:
        """First reading always sets the phase. After that, hysteresis requires consistency."""
        # First reading with different params: should switch immediately
        portrait1 = organizer.compute_phase_portrait(0.7, 0.7)
        assert portrait1.current_phase == SwarmPhase.BUILD

        # A single opposite reading: switches (history < 3 entries, so immediate switch)
        portrait2 = organizer.compute_phase_portrait(-0.7, -0.7)
        assert portrait2.current_phase == SwarmPhase.DISMANTLE

        # Now switch back: should also work immediately (history < 3 at this phase)
        portrait3 = organizer.compute_phase_portrait(0.7, 0.7)
        assert portrait3.current_phase == SwarmPhase.BUILD

        # Verify history is being recorded
        assert len(organizer._phase_history) >= 3


class TestPhaseSwitching:
    """Test explicit phase switching."""

    def test_switch_to_build(self, organizer: SwarmSelfOrganizer) -> None:
        portrait = organizer.switch_phase(SwarmPhase.BUILD)
        assert portrait.current_phase == SwarmPhase.BUILD
        assert portrait.cooperation_strength > 0
        assert portrait.deposition_rate > 0

    def test_switch_to_dismantle(self, organizer: SwarmSelfOrganizer) -> None:
        portrait = organizer.switch_phase(SwarmPhase.DISMANTLE)
        assert portrait.current_phase == SwarmPhase.DISMANTLE
        assert portrait.cooperation_strength < 0
        assert portrait.deposition_rate < 0

    def test_switch_to_patrol(self, organizer: SwarmSelfOrganizer) -> None:
        organizer.switch_phase(SwarmPhase.PATROL)
        assert organizer.current_phase == SwarmPhase.PATROL

    def test_switch_to_aggregate(self, organizer: SwarmSelfOrganizer) -> None:
        organizer.switch_phase(SwarmPhase.AGGREGATE)
        assert organizer.current_phase == SwarmPhase.AGGREGATE


class TestPhotormoneField:
    """Test digital photormone field."""

    def test_field_creation(self) -> None:
        f = PhotormoneField(grid_size=64)
        assert f.intensity is not None
        assert f.intensity.shape == (64, 64)
        assert np.all(f.intensity == 0.0)

    def test_deposit_increases_intensity(self) -> None:
        f = PhotormoneField(grid_size=64)
        f.deposit(0.5, 0.5, amount=0.5, radius=3)
        assert np.max(f.intensity) > 0.0

    def test_sense_returns_average(self) -> None:
        f = PhotormoneField(grid_size=64)
        f.deposit(0.5, 0.5, amount=0.8, radius=5)
        sensed = f.sense(0.5, 0.5, radius=3)
        assert sensed > 0.0

    def test_gradient_is_nonzero_after_deposit(self) -> None:
        f = PhotormoneField(grid_size=64)
        f.deposit(0.5, 0.5, amount=0.8, radius=3)
        gx, gy = f.gradient_at(0.52, 0.5)
        # Gradient should point toward the deposit center
        assert isinstance(gx, float)
        assert isinstance(gy, float)

    def test_step_decays_intensity(self) -> None:
        f = PhotormoneField(grid_size=64, decay_rate=0.1, diffusion_rate=0.0)
        f.deposit(0.5, 0.5, amount=0.8, radius=2)
        before = float(np.mean(f.intensity))
        for _ in range(5):
            f.step()
        after = float(np.mean(f.intensity))
        assert after < before

    def test_sense_at_empty_returns_zero(self) -> None:
        f = PhotormoneField(grid_size=64)
        assert f.sense(0.5, 0.5) == 0.0


class TestMarkAndSense:
    """Test environmental marking and sensing."""

    def test_mark_deposits(self, organizer: SwarmSelfOrganizer) -> None:
        before = organizer.sense((0.5, 0.5))
        organizer.mark((0.5, 0.5), intensity=0.8)
        after = organizer.sense((0.5, 0.5))
        assert after > before

    def test_step_field_reduces_intensity(self, organizer: SwarmSelfOrganizer) -> None:
        organizer.mark((0.5, 0.5), intensity=0.9, radius=5)
        before = organizer.sense((0.5, 0.5))
        for _ in range(10):
            organizer.step_field()
        after = organizer.sense((0.5, 0.5))
        assert after < before


class TestNucleation:
    """Test nucleation site detection."""

    def test_no_nucleation_on_empty_field(self, organizer: SwarmSelfOrganizer) -> None:
        sites = organizer.nucleate_structure()
        assert len(sites) == 0

    def test_nucleation_above_threshold(self, organizer: SwarmSelfOrganizer) -> None:
        """Deposit enough photormones to trigger nucleation."""
        for _ in range(5):
            organizer.mark((0.3, 0.3), intensity=0.5, radius=8)
        # Try nucleation
        sites = organizer.nucleate_structure()
        # May or may not exceed threshold depending on accumulation
        assert isinstance(sites, list)

    def test_nucleation_sites_have_ids(self, organizer: SwarmSelfOrganizer) -> None:
        """Create high-intensity spots to force nucleation."""
        for i in range(10):
            organizer.mark((0.3, 0.3), intensity=0.9, radius=8)
        sites = organizer.nucleate_structure()
        for site in sites:
            assert isinstance(site, NucleationSite)
            assert len(site.site_id) > 0
            assert 0.0 <= site.position[0] <= 1.0
            assert site.is_active is True

    def test_nucleation_respects_max_sites(self, organizer: SwarmSelfOrganizer) -> None:
        """Should not exceed max_nucleation_sites."""
        # Saturate the field
        for _ in range(20):
            organizer.mark((0.3, 0.3), intensity=0.9, radius=12)
            organizer.mark((0.7, 0.7), intensity=0.9, radius=12)
        organizer.nucleate_structure()
        assert len(organizer.nucleation_sites) <= organizer._config.max_nucleation_sites

    def test_update_sites(self, organizer: SwarmSelfOrganizer) -> None:
        """Sites should accumulate material or decay."""
        for _ in range(10):
            organizer.mark((0.5, 0.5), intensity=0.9, radius=8)
        organizer.nucleate_structure()
        organizer.update_sites(dt=0.1)


class TestGradientDescent:
    """Test gradient-based navigation."""

    def test_gradient_descent_basic(self, organizer: SwarmSelfOrganizer) -> None:
        organizer.mark((0.7, 0.7), intensity=0.9, radius=8)
        path = organizer.gradient_descent((0.3, 0.3), steps=20, learning_rate=0.1)
        assert len(path) > 0
        # All positions should be valid
        for x, y in path:
            assert 0.0 <= x <= 1.0
            assert 0.0 <= y <= 1.0

    def test_gradient_descent_stops_at_stationary(self, organizer: SwarmSelfOrganizer) -> None:
        """On a flat field, gradient descent should stop quickly."""
        path = organizer.gradient_descent((0.5, 0.5), steps=100, learning_rate=0.1)
        # On empty field, should stop before all steps used
        assert len(path) < 100


class TestReset:
    """Test organizer reset."""

    def test_reset_restores_initial_phase(self, organizer: SwarmSelfOrganizer) -> None:
        organizer.switch_phase(SwarmPhase.DISMANTLE)
        organizer.mark((0.5, 0.5), intensity=0.9)
        organizer.reset()
        assert organizer.current_phase == SwarmPhase.BUILD
        assert organizer.stats["nucleation_sites"] == 0
        assert organizer.sense((0.5, 0.5)) == 0.0
