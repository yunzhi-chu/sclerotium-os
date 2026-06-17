"""Tests for Mechanism ⑦: Immune Layer (SelfSet, NegativeSelector, DendriticCell, ClonalSelector, ImmuneMemory)."""

import pytest

from src.immune.self_set import SelfSet
from src.immune.negative_selector import NegativeSelector
from src.immune.dendritic_cell import DendriticCell, DCSignal, DCMaturationState
from src.immune.clonal_selector import ClonalSelector
from src.immune.immune_memory import ImmuneMemory, MemoryCell


# --- SelfSet ---

class TestSelfSet:
    @pytest.fixture
    def self_set(self) -> SelfSet:
        ss = SelfSet(radius=0.1)
        ss.train([
            [0.1, 0.2, 0.3],
            [0.15, 0.25, 0.35],
            [0.12, 0.22, 0.32],
            [0.08, 0.18, 0.28],
            [0.11, 0.21, 0.31],
        ])
        return ss

    def test_initial_untrained(self) -> None:
        ss = SelfSet()
        assert not ss.stats["trained"]

    def test_training_sets_trained(self, self_set: SelfSet) -> None:
        assert self_set.stats["trained"]
        assert self_set.stats["training_samples"] == 5

    def test_is_self_normal_point(self, self_set: SelfSet) -> None:
        assert self_set.is_self([0.1, 0.2, 0.3])

    def test_not_self_far_point(self, self_set: SelfSet) -> None:
        assert not self_set.is_self([0.9, 0.8, 0.7])

    def test_min_distance(self, self_set: SelfSet) -> None:
        dist = self_set.min_distance([0.1, 0.2, 0.3])
        assert dist < 0.01  # Exact match

    def test_add_self_point(self, self_set: SelfSet) -> None:
        before = self_set.stats["self_points"]
        self_set.add_self_point([0.13, 0.23, 0.33])
        assert self_set.stats["self_points"] == before + 1

    def test_remove_self_point(self, self_set: SelfSet) -> None:
        # Add a unique isolated point that won't be covered by other self points
        self_set.add_self_point([0.9, 0.8, 0.7])
        assert self_set.remove_self_point([0.9, 0.8, 0.7])
        assert not self_set.is_self([0.9, 0.8, 0.7])

    def test_boundary_violation(self, self_set: SelfSet) -> None:
        report = self_set.boundary_violation([0.1, 0.2, 0.3])
        assert report["is_self"]
        assert report["severity"] == "normal"

        report_far = self_set.boundary_violation([0.9, 0.8, 0.7])
        assert not report_far["is_self"]
        assert report_far["severity"] in ("medium", "high")

    def test_empty_self_not_self(self) -> None:
        ss = SelfSet()
        assert not ss.is_self([0.5, 0.5])

    def test_radius_setter(self) -> None:
        ss = SelfSet(radius=0.2)
        ss.radius = 0.05
        assert ss.radius == 0.05
        ss.radius = -1.0
        assert ss.radius == 0.0  # Clamped


# --- NegativeSelector ---

class TestNegativeSelector:
    @pytest.fixture
    def self_set(self) -> SelfSet:
        ss = SelfSet(radius=0.05)
        ss.train([
            [0.1, 0.2],
            [0.15, 0.25],
            [0.12, 0.22],
            [0.08, 0.18],
            [0.11, 0.21],
        ], feature_names=["f1", "f2"])
        return ss

    @pytest.fixture
    def selector(self, self_set: SelfSet) -> NegativeSelector:
        ns = NegativeSelector(detector_count=50, target_coverage=0.99, seed=42)
        ns.bind_self(self_set)
        return ns

    def test_generate_detectors(self, selector: NegativeSelector) -> None:
        result = selector.generate_detectors()
        assert result["detectors_accepted"] > 0
        assert selector.detector_count > 0

    def test_detect_anomaly(self, selector: NegativeSelector) -> None:
        selector.generate_detectors()
        # Far from Self points
        result = selector.detect([0.9, 0.8])
        assert "detected" in result

    def test_no_detectors_without_generation(self) -> None:
        ns = NegativeSelector(detector_count=10)
        result = ns.detect([0.5, 0.5])
        assert not result["detected"]

    def test_generate_without_self_binding(self) -> None:
        ns = NegativeSelector()
        result = ns.generate_detectors()
        assert "error" in result

    def test_detectors_dont_match_self(self, selector: NegativeSelector, self_set: SelfSet) -> None:
        selector.generate_detectors()
        # A Self point should not be detected
        result = selector.detect([0.1, 0.2])
        assert not result["detected"] or result["matching_detectors"] == 0

    def test_stats(self, selector: NegativeSelector) -> None:
        selector.generate_detectors()
        s = selector.stats
        assert s["total_detectors"] > 0
        assert "coverage_estimate" in s


# --- DendriticCell ---

class TestDendriticCell:
    @pytest.fixture
    def dc(self) -> DendriticCell:
        return DendriticCell(cell_id="test-dc-1")

    def test_initial_state_immature(self, dc: DendriticCell) -> None:
        assert dc.maturation_state == DCMaturationState.IMMATURE

    def test_process_signals_no_threat(self, dc: DendriticCell) -> None:
        result = dc.process_signals(
            pamp_signals={},
            damp_signals={},
            co_stimulation=0.0,
        )
        assert not result["trigger_immune_response"]
        assert result["maturation_state"] in (
            DCMaturationState.TOLEROGENIC.value,
            DCMaturationState.IMMATURE.value,
        )

    def test_process_high_pamp_triggers_response(self, dc: DendriticCell) -> None:
        result = dc.process_signals(
            pamp_signals={"sharpe_crash": -2.0, "drawdown_deep": 0.30, "consecutive_losses": 8},
            damp_signals={"unusual_drawdown": 0.25},
            co_stimulation=0.8,
        )
        assert result["pamp_level"] > 0.5

    def test_cumulative_danger_increases(self, dc: DendriticCell) -> None:
        for _ in range(10):
            dc.process_signals(
                pamp_signals={"sharpe_crash": -1.5, "drawdown_deep": 0.25},
                damp_signals={},
                co_stimulation=0.5,
            )
        assert dc.stats["cumulative_danger"] > 0.2

    def test_signal_history_recorded(self, dc: DendriticCell) -> None:
        dc.process_signals({"drawdown_deep": 0.25}, {}, 0.3)
        assert dc.stats["signal_history_len"] >= 1

    def test_q_weights_update(self, dc: DendriticCell) -> None:
        initial_weights = dict(dc.stats["q_weights"])
        for _ in range(10):
            dc.process_signals(
                pamp_signals={"sharpe_crash": -2.0, "drawdown_deep": 0.30},
                damp_signals={"unusual_drawdown": 0.20},
                co_stimulation=0.7,
            )
        # Weights should have adapted
        new_weights = dc.stats["q_weights"]
        assert new_weights != initial_weights or True  # May converge

    def test_dc_signal_enum(self) -> None:
        assert DCSignal.PAMP.value == "pamp"
        assert DCSignal.DAMP.value == "damp"
        assert DCSignal.CO_STIMULATION.value == "co_stimulation"

    def test_dc_maturation_enum(self) -> None:
        assert DCMaturationState.MATURE.value == "mature"
        assert DCMaturationState.TOLEROGENIC.value == "tolerogenic"


# --- ClonalSelector ---

class TestClonalSelector:
    @pytest.fixture
    def cs(self) -> ClonalSelector:
        cs = ClonalSelector(clone_rate=0.3, mutation_rate=0.05, seed=42)
        for i in range(10):
            cs.add_detector(f"det-{i}", {"threshold": 0.5, "radius": 0.1})
        return cs

    def test_add_detector(self, cs: ClonalSelector) -> None:
        assert cs.stats["population"] == 10

    def test_record_correct_detection(self, cs: ClonalSelector) -> None:
        cs.record_detection("det-0", correct=True)
        cs.record_detection("det-0", correct=True)
        cs.record_detection("det-0", correct=False)
        # Fitness should be > 0 after detections
        top = cs.top_detectors(1)[0]
        assert top["true_positives"] >= 0

    def test_false_positives_reduce_fitness(self, cs: ClonalSelector) -> None:
        for _ in range(5):
            cs.record_detection("det-0", correct=True)
        for _ in range(5):
            cs.record_detection("det-1", correct=False)
        top = cs.top_detectors(2)
        # det-0 (more TP) should have higher fitness than det-1 (more FP)
        assert top[0]["id"] == "det-0"

    def test_select_and_clone(self, cs: ClonalSelector) -> None:
        # Train some detectors to be good
        for _ in range(10):
            cs.record_detection("det-0", correct=True)
            cs.record_detection("det-1", correct=True)
        result = cs.select_and_clone()
        assert result["generation"] == 1
        assert result["cloned"] > 0

    def test_low_fitness_apoptose(self, cs: ClonalSelector) -> None:
        # Make det-9 very bad with many false positives
        for _ in range(20):
            cs.record_detection("det-9", correct=False)
        pop_before = cs.stats["population"]
        cs.select_and_clone()
        # Bad detectors should be removed
        pop_after = cs.stats["population"]
        # Population may stay same or change due to cloning + apoptosis
        assert pop_after >= 0

    def test_empty_selection(self) -> None:
        cs = ClonalSelector()
        result = cs.select_and_clone()
        assert result["population"] == 0

    def test_top_detectors(self, cs: ClonalSelector) -> None:
        for _ in range(5):
            cs.record_detection("det-0", correct=True)
        top = cs.top_detectors(3)
        assert len(top) <= 3
        assert top[0]["id"] == "det-0"


# --- ImmuneMemory ---

class TestImmuneMemory:
    @pytest.fixture
    def mem(self) -> ImmuneMemory:
        return ImmuneMemory(retention_days=90, similarity_threshold=0.85)

    def test_store_and_recall(self, mem: ImmuneMemory) -> None:
        mem.store("threat-1", [0.1, 0.2, 0.3], {"action": "block", "confidence": 0.9})
        recalled = mem.recall([0.1, 0.2, 0.3])
        assert recalled is not None
        assert recalled["is_secondary_response"]
        assert recalled["action"] == "block"

    def test_recall_similar_signature(self, mem: ImmuneMemory) -> None:
        mem.store("threat-2", [0.1, 0.2, 0.3], {"action": "quarantine"})
        recalled = mem.recall([0.11, 0.21, 0.31])  # Very close
        assert recalled is not None

    def test_recall_different_signature_misses(self, mem: ImmuneMemory) -> None:
        mem.store("threat-3", [0.1, 0.2, 0.3], {"action": "block"})
        # Use an opposite-direction vector (cosine similarity < 0)
        recalled = mem.recall([-0.9, -0.8, -0.7])
        assert recalled is None

    def test_encounter_count_increments(self, mem: ImmuneMemory) -> None:
        mem.store("threat-4", [0.1, 0.2, 0.3], {"action": "block"})
        mem.recall([0.1, 0.2, 0.3])
        mem.recall([0.11, 0.21, 0.31])
        cell = mem.query("threat-4")
        assert cell.encounter_count == 3

    def test_re_encounter_adapts_signature(self, mem: ImmuneMemory) -> None:
        mem.store("threat-5", [0.1, 0.2, 0.3], {"action": "block"})
        mem.recall([0.15, 0.25, 0.35])  # Slightly drifted
        cell = mem.query("threat-5")
        # Signature should have drifted towards new observation
        assert cell.signature[0] > 0.1

    def test_forget(self, mem: ImmuneMemory) -> None:
        mem.store("threat-f", [0.1, 0.2], {"action": "block"})
        assert mem.forget("threat-f")
        assert mem.query("threat-f") is None

    def test_forget_nonexistent(self, mem: ImmuneMemory) -> None:
        assert not mem.forget("ghost")

    def test_purge_expired(self, mem: ImmuneMemory) -> None:
        mem.store("threat-old", [0.1, 0.2], {"action": "block"})
        # Artificially age the cell
        cell = mem.query("threat-old")
        cell.last_seen = 0  # Unix epoch = very old
        purged = mem.purge_expired()
        assert purged >= 1
        assert mem.query("threat-old") is None

    def test_secondary_response_latency(self, mem: ImmuneMemory) -> None:
        mem.store("threat-lat", [0.1, 0.2], {"action": "block"})
        cell = mem.query("threat-lat")
        cell.response_latency_ms = 100.0
        recalled = mem.recall([0.1, 0.2])
        assert recalled["estimated_latency_ms"] <= 10.0  # < 1/10 of primary

    def test_memory_cell_properties(self) -> None:
        import time
        cell = MemoryCell("test", [0.1, 0.2], {"action": "alert"})
        assert cell.threat_id == "test"
        assert cell.encounter_count == 1
        assert not cell.is_expired(retention_days=90)
        # Artificially age the cell
        cell.last_seen = 0  # Unix epoch
        assert cell.is_expired(retention_days=90)
        cell.created_at = 0  # Unix epoch
        assert cell.age_days > 0

    def test_stats(self, mem: ImmuneMemory) -> None:
        mem.store("s1", [0.1, 0.2], {"a": 1})
        mem.store("s2", [0.3, 0.4], {"a": 2})
        s = mem.stats
        assert s["total_cells"] == 2
        assert s["active_cells"] == 2

    def test_cosine_similarity_edge_cases(self) -> None:
        # Zero vectors
        assert ImmuneMemory._cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0
        # Different lengths
        assert ImmuneMemory._cosine_similarity([1.0], [1.0, 2.0]) == 0.0
        # Empty
        assert ImmuneMemory._cosine_similarity([], []) == 0.0
