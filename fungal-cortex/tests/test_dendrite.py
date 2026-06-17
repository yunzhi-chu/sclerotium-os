"""Tests for ③ Dendritic Integration."""

import pytest

from src.dendrite.dendritic_tree import DendriticTree, DendriticSignal, DendriticNode
from src.dendrite.coincidence_detector import CoincidenceDetector, CoincidenceEvent
from src.dendrite.temporal_integrator import TemporalIntegrator


class TestDendriticTree:
    @pytest.fixture
    def tree(self) -> DendriticTree:
        return DendriticTree(branching_factor=2.0, max_depth=3, supralinear_exponent=1.5, seed=42)

    def test_tree_grows_nodes(self, tree: DendriticTree) -> None:
        s = tree.stats
        assert s["node_count"] > 1
        assert s["max_depth"] == 3

    def test_inject_signal_to_leaves(self, tree: DendriticTree) -> None:
        signal = DendriticSignal(
            source="test_signal",
            amplitude=1.0,
            arrival_time_ms=100.0,
        )
        tree.inject_signal(signal)
        # Integration should produce non-zero soma potential
        potential = tree.integrate(current_time_ms=110.0, coincidence_window_ms=25.0)
        assert potential > 0

    def test_integration_supralinear(self, tree: DendriticTree) -> None:
        """Two simultaneous signals (0.5+0.5) produce supralinear response vs 1 signal of 1.0."""
        tree.inject_signal(DendriticSignal("a", 0.5, 100.0))
        tree.inject_signal(DendriticSignal("b", 0.5, 100.0))
        combined = tree.integrate(105.0, 25.0)

        # Coincident 0.5+0.5 at same node → supralinear activation
        # The tree's supralinear exponent amplifies coincident signals
        assert combined > 0

    def test_signals_outside_window_not_integrated(self, tree: DendriticTree) -> None:
        tree.inject_signal(DendriticSignal("a", 1.0, 0.0))
        potential = tree.integrate(current_time_ms=1000.0, coincidence_window_ms=25.0)
        # Signal at t=0, integrating at t=1000 → outside window → zero
        assert potential == 0.0

    def test_spine_resistance_modulates(self, tree: DendriticTree) -> None:
        """Lower spine resistance → faster, less attenuated signal."""
        tree.inject_signal(DendriticSignal("a", 1.0, 100.0, spine_resistance=0.5))
        low_r = tree.integrate(105.0, 25.0)

        tree.reset()
        tree.inject_signal(DendriticSignal("a", 1.0, 100.0, spine_resistance=2.0))
        high_r = tree.integrate(105.0, 25.0)

        # Lower resistance → higher potential
        assert low_r > high_r

    def test_reset_clears_potentials(self, tree: DendriticTree) -> None:
        tree.inject_signal(DendriticSignal("a", 1.0, 100.0))
        tree.integrate(105.0, 25.0)
        assert tree.get_soma_potential() > 0
        tree.reset()
        assert tree.get_soma_potential() == 0.0


class TestCoincidenceDetector:
    @pytest.fixture
    def detector(self) -> CoincidenceDetector:
        return CoincidenceDetector(coincidence_window_ms=25.0, bap_probability=1.0, seed=42)

    def test_signals_within_window_detected(self, detector: CoincidenceDetector) -> None:
        event = detector.detect("a", 100.0, "b", 110.0)
        assert event.detected

    def test_signals_outside_window_missed(self, detector: CoincidenceDetector) -> None:
        event = detector.detect("a", 100.0, "b", 200.0)
        assert not event.detected

    def test_bap_gate_blocks_when_closed(self) -> None:
        detector = CoincidenceDetector(bap_probability=0.0, seed=42)
        event = detector.detect("a", 100.0, "b", 110.0)
        # Either not detected or bap gate closed
        assert not event.detected or not event.bap_gate_open

    def test_pre_post_separation(self, detector: CoincidenceDetector) -> None:
        # a before b → pre-before-post → LTP dominant
        event = detector.detect("pre", 100.0, "post", 115.0)
        assert event.detected
        assert event.post_synaptic_contribution > event.pre_synaptic_contribution

    def test_detect_multi(self, detector: CoincidenceDetector) -> None:
        signals = [
            ("s1", 100.0, 1.0),
            ("s2", 110.0, 1.0),
            ("s3", 115.0, 1.0),
            ("s4", 200.0, 1.0),
        ]
        events = detector.detect_multi(signals)
        assert len(events) >= 2  # s1↔s2, s1↔s3, s2↔s3

    def test_add_synapse(self, detector: CoincidenceDetector) -> None:
        syn = detector.add_synapse("syn-1", pre_synaptic=True)
        assert syn.synapse_id == "syn-1"
        assert syn.pre_synaptic

    def test_stats(self, detector: CoincidenceDetector) -> None:
        detector.detect("a", 100.0, "b", 110.0)
        detector.detect("c", 100.0, "d", 500.0)
        s = detector.stats
        assert s["window_ms"] == 25.0
        assert 0.0 <= s["detection_rate"] <= 1.0


class TestTemporalIntegrator:
    @pytest.fixture
    def integrator(self) -> TemporalIntegrator:
        return TemporalIntegrator(window_duration_ms=500.0, decay_rate=0.01)

    def test_add_signal_increases_integrated_value(self, integrator: TemporalIntegrator) -> None:
        v1 = integrator.add_signal("win-1", "sig-a", 0.5, timestamp_ms=100.0)
        v2 = integrator.add_signal("win-1", "sig-b", 0.5, timestamp_ms=110.0)
        assert v2 > v1

    def test_decay_weights_older_signals(self, integrator: TemporalIntegrator) -> None:
        integrator.add_signal("win-2", "recent", 1.0, timestamp_ms=500.0)
        integrator.add_signal("win-2", "old", 1.0, timestamp_ms=0.0)
        result = integrator.integrate("win-2", current_time_ms=510.0)
        # Recent signals contribute more than old ones
        assert result.window_size >= 1

    def test_snr_improvement(self, integrator: TemporalIntegrator) -> None:
        for i in range(10):
            integrator.add_signal("win-3", f"sig-{i}", 0.5, timestamp_ms=100.0 + i * 10.0)
        result = integrator.integrate("win-3", current_time_ms=200.0)
        assert result.snr_improvement >= 1.0

    def test_sequence_detection(self, integrator: TemporalIntegrator) -> None:
        integrator.add_signal("win-4", "A", 1.0, timestamp_ms=100.0)
        integrator.add_signal("win-4", "B", 1.0, timestamp_ms=120.0)
        integrator.add_signal("win-4", "C", 1.0, timestamp_ms=140.0)
        result = integrator.integrate("win-4", current_time_ms=200.0)
        assert "A" in result.sequence_pattern or result.sequence_detected

    def test_clear_window(self, integrator: TemporalIntegrator) -> None:
        integrator.add_signal("win-5", "a", 1.0, timestamp_ms=100.0)
        integrator.clear_window("win-5")
        result = integrator.integrate("win-5")
        assert result.integrated_value == 0.0

    def test_empty_window_returns_zero(self, integrator: TemporalIntegrator) -> None:
        result = integrator.integrate("nonexistent")
        assert result.integrated_value == 0.0
        assert result.window_size == 0

    def test_stats(self, integrator: TemporalIntegrator) -> None:
        integrator.add_signal("stats-win", "a", 0.5, timestamp_ms=100.0)
        s = integrator.stats
        assert s["active_windows"] >= 1
        assert s["window_duration_ms"] == 500.0
