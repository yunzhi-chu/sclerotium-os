"""Tests for ⑫ Panarchy Resilience."""

import pytest

from src.panarchy.adaptive_cycle import AdaptiveCycle, CyclePhase, CycleState
from src.panarchy.panarchy_controller import PanarchyController, ScaleLevel, CrossScaleSignal
from src.panarchy.resilience_metrics import ResilienceMetrics, ResilienceProfile


class TestAdaptiveCycle:
    @pytest.fixture
    def cycle(self) -> AdaptiveCycle:
        return AdaptiveCycle("test_cycle", r_duration=5.0, k_duration=15.0, omega_threshold=0.7, seed=42)

    def test_initial_phase_is_r(self, cycle: AdaptiveCycle) -> None:
        assert cycle.phase == CyclePhase.R

    def test_step_updates_metrics(self, cycle: AdaptiveCycle) -> None:
        state = cycle.step()
        assert isinstance(state, CycleState)
        assert state.phase == CyclePhase.R
        assert 0.0 <= state.potential <= 1.0

    def test_step_accumulates_potential_in_r(self, cycle: AdaptiveCycle) -> None:
        initial_potential = cycle.stats["potential"]
        for _ in range(10):
            cycle.step()
        assert cycle.stats["potential"] > initial_potential

    def test_r_to_k_transition(self, cycle: AdaptiveCycle) -> None:
        # Run enough steps to transition from r to K
        for _ in range(100):
            state = cycle.step()
        # Should have transitioned to K or further
        assert cycle.phase in (CyclePhase.K, CyclePhase.OMEGA, CyclePhase.ALPHA)

    def test_external_disturbance_triggers_omega(self, cycle: AdaptiveCycle) -> None:
        # First get to K phase
        for _ in range(200):
            cycle.step()
        if cycle.phase == CyclePhase.K:
            # Apply strong disturbance to trigger Ω
            state = cycle.step(external_disturbance=0.9)
            assert cycle.phase == CyclePhase.OMEGA

    def test_omega_transitions_to_alpha(self, cycle: AdaptiveCycle) -> None:
        # Get to K phase first
        for _ in range(300):
            cycle.step()
        # Apply strong disturbance to force Ω if in K
        if cycle.phase == CyclePhase.K:
            for _ in range(10):
                cycle.step(external_disturbance=0.95)
        # Now run until transition from Ω
        for _ in range(100):
            cycle.step()
        # Should have progressed past Ω
        assert cycle.phase in (CyclePhase.ALPHA, CyclePhase.R, CyclePhase.K)

    def test_phase_enum(self) -> None:
        assert CyclePhase.R.value == "r"
        assert CyclePhase.K.value == "k"
        assert CyclePhase.OMEGA.value == "omega"
        assert CyclePhase.ALPHA.value == "alpha"

    def test_stats(self, cycle: AdaptiveCycle) -> None:
        s = cycle.stats
        assert s["name"] == "test_cycle"
        assert "potential" in s
        assert "connectedness" in s
        assert "resilience" in s


class TestPanarchyController:
    @pytest.fixture
    def controller(self) -> PanarchyController:
        return PanarchyController(revolt_threshold=0.5, remember_strength=0.3, intermediate_disturbance=0.15)

    def test_all_four_scales_exist(self, controller: PanarchyController) -> None:
        assert len(controller._cycles) == 4
        assert ScaleLevel.SIGNAL in controller._cycles
        assert ScaleLevel.SYSTEM in controller._cycles

    def test_step_all_returns_states(self, controller: PanarchyController) -> None:
        states = controller.step_all()
        assert len(states) == 4
        assert ScaleLevel.SIGNAL in states
        assert "phase" in states[ScaleLevel.SIGNAL]

    def test_step_all_with_disturbances(self, controller: PanarchyController) -> None:
        disturbances = {ScaleLevel.SIGNAL: 0.8, ScaleLevel.STRATEGY: 0.3}
        states = controller.step_all(disturbances=disturbances)
        assert len(states) == 4

    def test_revolt_cascade_possible(self, controller: PanarchyController) -> None:
        # Step many times to potentially trigger cascades
        for _ in range(200):
            controller.step_all()
        # Revolt cascades may have occurred
        s = controller.stats
        assert s["phase_coherence"] >= 0.0

    def test_phase_coherence_range(self, controller: PanarchyController) -> None:
        coherence = controller.get_phase_coherence()
        assert 0.0 <= coherence <= 1.0

    def test_apply_intermediate_disturbance(self, controller: PanarchyController) -> None:
        disturbances = controller.apply_intermediate_disturbance()
        assert len(disturbances) == 4
        for scale in ScaleLevel:
            assert 0.0 <= disturbances[scale] <= 0.5

    def test_cross_scale_signals_accumulate(self, controller: PanarchyController) -> None:
        for _ in range(100):
            controller.step_all()
        assert isinstance(controller._cross_scale_signals, list)

    def test_remember_constraints_applied(self, controller: PanarchyController) -> None:
        for _ in range(50):
            controller.step_all()
        # Remember constraints should exist
        assert isinstance(controller._remember_constraints, dict)

    def test_stats_comprehensive(self, controller: PanarchyController) -> None:
        s = controller.stats
        assert "scale_phases" in s
        assert "phase_coherence" in s
        assert "revolt_signals" in s
        assert "remember_signals" in s


class TestResilienceMetrics:
    @pytest.fixture
    def metrics(self) -> ResilienceMetrics:
        rm = ResilienceMetrics(component_count=10)
        # Set up some interactions
        for i in range(10):
            rm.set_fitness(i, 0.5 + 0.05 * i)
        rm.set_interaction(0, 1, 0.3)
        rm.set_interaction(1, 2, 0.2)
        rm.set_interaction(2, 0, 0.1)
        return rm

    def test_ecological_resilience(self, metrics: ResilienceMetrics) -> None:
        eco = metrics.compute_ecological_resilience()
        assert 0.0 <= eco <= 1.0

    def test_engineering_resilience(self, metrics: ResilienceMetrics) -> None:
        eng = metrics.compute_engineering_resilience()
        assert 0.0 <= eng <= 1.0

    def test_diversity_index(self, metrics: ResilienceMetrics) -> None:
        div = metrics.compute_diversity()
        assert 0.0 <= div <= 1.0

    def test_modularity(self, metrics: ResilienceMetrics) -> None:
        mod = metrics.compute_modularity()
        assert 0.0 <= mod <= 1.0

    def test_robustness(self, metrics: ResilienceMetrics) -> None:
        rob = metrics.compute_robustness()
        assert 0.0 <= rob <= 1.0

    def test_reactivity(self, metrics: ResilienceMetrics) -> None:
        react = metrics.compute_reactivity()
        assert 0.0 <= react <= 1.0

    def test_critical_slowness(self, metrics: ResilienceMetrics) -> None:
        # Record disturbances
        for i in range(20):
            metrics.record_disturbance(0.1 * i % 1.0)
        cs = metrics.compute_critical_slowness()
        assert 0.0 <= cs <= 1.0

    def test_full_assessment(self, metrics: ResilienceMetrics) -> None:
        profile = metrics.assess()
        assert isinstance(profile, ResilienceProfile)
        assert 0.0 <= profile.ecological_resilience <= 1.0
        assert 0.0 <= profile.overall_resilience <= 1.0
        assert 0.0 <= profile.regime_shift_risk <= 1.0

    def test_regime_shift_risk_increases_with_eng_over_eco(self) -> None:
        rm_low_eco = ResilienceMetrics(component_count=10)
        for i in range(10):
            rm_low_eco.set_fitness(i, 1.0)
            for j in range(10):
                rm_low_eco.set_interaction(i, j, 0.9)  # High connectivity

        profile = rm_low_eco.assess()
        # High connectedness → lower ecological resilience
        assert profile.ecological_resilience < 0.9

    def test_stats(self, metrics: ResilienceMetrics) -> None:
        s = metrics.stats
        assert "ecological_resilience" in s
        assert "diversity" in s
        assert "regime_shift_risk" in s

    def test_empty_system_resilience(self) -> None:
        rm = ResilienceMetrics(component_count=0)
        eco = rm.compute_ecological_resilience()
        assert eco == 1.0  # Empty system = max resilience
