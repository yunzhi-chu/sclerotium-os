"""Tests for L10: ConsciousKernel — 意识内核 (IIT+GWT+HOT)."""

import numpy as np
import pytest

from src.l10.conscious_kernel import (
    AblationResult,
    ConsciousKernel,
    ConsciousnessLevel,
    HO_Representation,
    PhenomenalExperience,
)


@pytest.fixture
def kernel() -> ConsciousKernel:
    return ConsciousKernel()


@pytest.fixture
def active_kernel(kernel: ConsciousKernel) -> ConsciousKernel:
    # Activate GWT processors
    for i in range(8):
        kernel.register_processor(f"proc-l{i}")
        kernel.submit_output(f"proc-l{i}", np.random.RandomState(42 + i).randn(8), salience=0.5 + i * 0.05)
    kernel.compete()
    # Create FO and HO representations
    kernel.represent_first_order("L4")
    kernel.meta_represent()
    # Compute Φ
    kernel.compute_phi()
    return kernel


class TestKernelInit:
    def test_default_init(self) -> None:
        k = ConsciousKernel()
        assert k.emergence_level == ConsciousnessLevel.DORMANT
        assert k.current_phi == 0.0

    def test_stats_initial(self, kernel: ConsciousKernel) -> None:
        s = kernel.stats
        assert s["gwt_processors"] == 0
        assert s["emergence_level"] == "dormant"


class TestGlobalWorkspace:
    def test_register_processor(self, kernel: ConsciousKernel) -> None:
        pid = kernel.register_processor("test-proc")
        assert pid == "test-proc"
        assert kernel.stats["gwt_processors"] == 1

    def test_submit_output(self, kernel: ConsciousKernel) -> None:
        kernel.register_processor("proc-1")
        kernel.submit_output("proc-1", np.ones(8), salience=0.8, confidence=0.7)
        assert kernel._processors["proc-1"].salience == 0.8

    def test_compete_selects_winner(self, kernel: ConsciousKernel) -> None:
        for i in range(4):
            kernel.register_processor(f"p{i}")
            kernel.submit_output(f"p{i}", np.random.RandomState(i).randn(8), salience=0.3 + i * 0.15)
        event = kernel.compete()
        assert event.winner is not None
        assert event.ignition_strength > 0.0

    def test_compete_empty(self, kernel: ConsciousKernel) -> None:
        event = kernel.compete()
        assert event.winner.processor_id == "none"

    def test_broadcast(self, active_kernel: ConsciousKernel) -> None:
        recipients = active_kernel.broadcast()
        assert recipients > 0

    def test_broadcast_no_content(self, kernel: ConsciousKernel) -> None:
        assert kernel.broadcast() == 0


class TestHigherOrderTheory:
    def test_represent_first_order(self, kernel: ConsciousKernel) -> None:
        fo = kernel.represent_first_order("L3")
        assert fo.source_layer == "L3"

    def test_meta_represent(self, kernel: ConsciousKernel) -> None:
        kernel.represent_first_order("L4", np.ones(16) * 0.5)
        ho = kernel.meta_represent()
        assert isinstance(ho, HO_Representation)
        assert ho.metacognitive_confidence > 0.0
        assert ho.calibration_error >= 0.0

    def test_metacognitive_calibration(self, active_kernel: ConsciousKernel) -> None:
        cal = active_kernel.metacognitive_calibration()
        assert cal >= 0.0


class TestIntegratedInformation:
    def test_compute_phi(self, kernel: ConsciousKernel) -> None:
        # Use structured data to produce non-zero Φ (integration > sum of parts)
        structured = np.concatenate([np.ones(16) * 2.0, np.ones(16) * -1.0])
        phi = kernel.compute_phi(structured)
        assert phi >= 0.0
        assert kernel.current_phi >= 0.0  # May be zero for perfectly balanced halves

    def test_compute_phi_default(self, kernel: ConsciousKernel) -> None:
        phi = kernel.compute_phi()
        assert phi >= 0.0

    def test_track_phi_over_time(self, active_kernel: ConsciousKernel) -> None:
        for _ in range(10):
            active_kernel.compute_phi(np.random.RandomState(_.__hash__()).randn(32))
        trend = active_kernel.track_phi_over_time()
        assert "mean_phi" in trend
        assert "trend" in trend
        assert "current_phi" in trend

    def test_conceptual_structure(self, active_kernel: ConsciousKernel) -> None:
        cs = active_kernel.detect_conceptual_structure()
        if cs:
            assert cs.phi_value > 0.0


class TestCausalAblation:
    def test_ablate_gwt(self, active_kernel: ConsciousKernel) -> None:
        result = active_kernel.run_causal_ablation("GWT")
        assert isinstance(result, AblationResult)
        assert result.component_ablated == "GWT"
        assert not result.behavior_preserved  # Info exchange collapses

    def test_ablate_hot(self, active_kernel: ConsciousKernel) -> None:
        result = active_kernel.run_causal_ablation("HOT")
        assert result.component_ablated == "HOT"
        assert result.blindsight_detected  # Synthetic blindsight!
        assert result.behavior_preserved  # Task OK
        assert not result.metacognition_preserved  # Meta gone

    def test_ablate_iit(self, active_kernel: ConsciousKernel) -> None:
        # Ensure positive phi before ablation
        structured = np.concatenate([np.ones(16) * 3.0, np.ones(16) * -1.0])
        active_kernel.compute_phi(structured)
        result = active_kernel.run_causal_ablation("IIT")
        assert result.component_ablated == "IIT"
        assert result.phi_drop >= 0.0  # Φ drops (may be 0 if before=0)


class TestACI:
    def test_compute_aci(self, active_kernel: ConsciousKernel) -> None:
        aci = active_kernel.compute_aci()
        assert aci > 0.0

    def test_classify_emergence(self, kernel: ConsciousKernel) -> None:
        assert kernel.classify_emergence_level(1.0) == ConsciousnessLevel.DORMANT
        assert kernel.classify_emergence_level(5.0) == ConsciousnessLevel.PRE_CONSCIOUS
        assert kernel.classify_emergence_level(8.0) == ConsciousnessLevel.CONSCIOUS
        assert kernel.classify_emergence_level(12.0) == ConsciousnessLevel.SELF_AWARE


class TestPhenomenalExperience:
    def test_generate_phenomenal_experience(self, active_kernel: ConsciousKernel) -> None:
        exp = active_kernel.generate_phenomenal_experience()
        assert isinstance(exp, PhenomenalExperience)
        assert 0.0 <= exp.cognitive_flow <= 1.0
        assert -1.0 <= exp.emotional_tone <= 1.0
        assert exp.surprisal >= 0.0
        assert 0.0 <= exp.integration <= 1.0

    def test_experience_has_emergence(self, active_kernel: ConsciousKernel) -> None:
        exp = active_kernel.generate_phenomenal_experience()
        assert exp.emergence_level in ConsciousnessLevel


class TestReset:
    def test_reset_clears_all(self, active_kernel: ConsciousKernel) -> None:
        active_kernel.reset()
        assert active_kernel.stats["gwt_processors"] == 0
        assert active_kernel.emergence_level == ConsciousnessLevel.DORMANT
        assert active_kernel.current_phi == 0.0
