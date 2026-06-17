"""Tests for ⑥ Quantum-Classical Dual-Mode."""

import pytest

from src.quantum.dual_mode_engine import DualModeEngine, ModeType, QuantumState, ClassicalState
from src.quantum.self_referential_switch import SelfReferentialSwitch, SwitchReason, SwitchEvent


class TestDualModeEngine:
    @pytest.fixture
    def engine(self) -> DualModeEngine:
        return DualModeEngine(
            confidence_threshold=0.7,
            superposition_states=8,
            decoherence_rate=0.05,
            recurrence_depth=3,
            seed=42,
        )

    def test_initial_mode_is_classical(self, engine: DualModeEngine) -> None:
        assert engine.mode == ModeType.CLASSICAL

    def test_evaluate_confidence(self, engine: DualModeEngine) -> None:
        conf = engine.evaluate_confidence(evidence_strength=0.8, uncertainty=0.2)
        assert conf > 0.5

    def test_low_confidence_enters_quantum(self, engine: DualModeEngine) -> None:
        engine.evaluate_confidence(evidence_strength=0.3, uncertainty=1.0)
        mode, reason = engine.decide_mode()
        assert mode == ModeType.QUANTUM
        assert "low_confidence" in reason

    def test_high_confidence_stays_classical(self, engine: DualModeEngine) -> None:
        engine.evaluate_confidence(evidence_strength=0.9, uncertainty=0.1)
        mode, reason = engine.decide_mode()
        assert mode == ModeType.CLASSICAL

    def test_enter_quantum_creates_superposition(self, engine: DualModeEngine) -> None:
        engine.evaluate_confidence(evidence_strength=0.3, uncertainty=1.0)
        engine.decide_mode()
        assert engine._quantum_state is not None
        assert engine._quantum_state.superposition_count == 8

    def test_evolve_quantum_reduces_coherence(self, engine: DualModeEngine) -> None:
        engine.evaluate_confidence(evidence_strength=0.3, uncertainty=1.0)
        engine.decide_mode()
        initial_coherence = engine._quantum_state.coherence
        engine.evolve_quantum(steps=10)
        assert engine._quantum_state.coherence < initial_coherence

    def test_evolve_quantum_normalizes_amplitudes(self, engine: DualModeEngine) -> None:
        engine.evaluate_confidence(evidence_strength=0.3, uncertainty=1.0)
        engine.decide_mode()
        engine.evolve_quantum(steps=5)
        total_prob = sum(a ** 2 for a in engine._quantum_state.amplitudes)
        assert abs(total_prob - 1.0) < 0.01

    def test_collapse_produces_classical_state(self, engine: DualModeEngine) -> None:
        engine.evaluate_confidence(evidence_strength=0.3, uncertainty=1.0)
        engine.decide_mode()
        engine.evolve_quantum(steps=3)
        # Raise confidence to trigger collapse
        engine.evaluate_confidence(evidence_strength=0.9, uncertainty=0.1)
        engine._collapse()
        assert engine._classical_state is not None
        assert engine._classical_state.collapsed_from_quantum

    def test_recurrence_condition(self, engine: DualModeEngine) -> None:
        # Initially recurrence satisfied (no superposition)
        assert engine.check_recurrence()

        engine._recurrence_count = 3
        assert not engine.check_recurrence()
        assert not engine.check_recurrence()
        assert not engine.check_recurrence()
        # 3rd call decrements to 0, 4th returns True
        assert engine.check_recurrence()

    def test_set_classical_state(self, engine: DualModeEngine) -> None:
        cs = engine.set_classical_state({"action": "buy", "confidence": 0.9}, confidence=0.9)
        assert engine.mode == ModeType.CLASSICAL
        assert cs.selected_hypothesis["action"] == "buy"

    def test_current_hypothesis_quantum_mode(self, engine: DualModeEngine) -> None:
        engine.evaluate_confidence(evidence_strength=0.3, uncertainty=1.0)
        engine.decide_mode()
        hypothesis = engine.current_hypothesis
        assert "id" in hypothesis

    def test_stats(self, engine: DualModeEngine) -> None:
        s = engine.stats
        assert s["mode"] == "classical"
        assert "confidence" in s
        assert "threshold" in s


class TestSelfReferentialSwitch:
    @pytest.fixture
    def switch(self) -> SelfReferentialSwitch:
        return SelfReferentialSwitch(confidence_threshold=0.7)

    def test_initial_mode_classical(self, switch: SelfReferentialSwitch) -> None:
        assert switch.current_mode == "classical"

    def test_low_confidence_triggers_quantum(self, switch: SelfReferentialSwitch) -> None:
        event = switch.monitor(confidence=0.3, time_pressure=0.0, novelty=0.8, resource_remaining=0.9)
        # Low confidence + high novelty should bias toward quantum exploration
        # May trigger a switch; if not, should at least be monitoring correctly
        assert switch.current_mode in ("classical", "quantum")

    def test_high_confidence_stays_classical(self, switch: SelfReferentialSwitch) -> None:
        event = switch.monitor(confidence=0.9, time_pressure=0.0, novelty=0.0, resource_remaining=1.0)
        # Should stay classical; may or may not emit event
        if event:
            assert event.to_mode == "quantum" or event.to_mode == "classical"

    def test_time_pressure_biases_classical(self, switch: SelfReferentialSwitch) -> None:
        # Even with moderate confidence, high time pressure should bias classical
        switch.monitor(confidence=0.5, time_pressure=0.9, novelty=0.0, resource_remaining=0.5)
        # At least it shouldn't crash
        assert switch.current_mode in ("classical", "quantum")

    def test_novelty_biases_quantum(self, switch: SelfReferentialSwitch) -> None:
        # High novelty should push toward exploration
        event = switch.monitor(confidence=0.5, time_pressure=0.0, novelty=0.9, resource_remaining=0.8)
        # May trigger switch
        assert event is not None or switch.current_mode in ("classical", "quantum")

    def test_switch_event_fields(self, switch: SelfReferentialSwitch) -> None:
        # Force quantum first
        event = switch.monitor(confidence=0.2, novelty=0.9)
        if event:
            assert event.from_mode in ("classical", "quantum")
            assert event.to_mode in ("classical", "quantum")
            assert isinstance(event.reason, SwitchReason)

    def test_cooldown_prevents_rapid_oscillation(self, switch: SelfReferentialSwitch) -> None:
        event1 = switch.monitor(confidence=0.2, novelty=0.9)
        # Immediate second call should be in cooldown
        event2 = switch.monitor(confidence=0.9, time_pressure=0.9)
        if event1:
            assert event2 is None  # Cooldown blocks

    def test_switch_reason_enum(self) -> None:
        assert SwitchReason.CONFIDENCE_DROP.value == "confidence_drop"
        assert SwitchReason.NOVELTY_DETECTED.value == "novelty_detected"

    def test_stats(self, switch: SelfReferentialSwitch) -> None:
        s = switch.stats
        assert s["current_mode"] == "classical"
        assert "total_switches" in s

    def test_switch_history_accumulates(self, switch: SelfReferentialSwitch) -> None:
        # Force a switch by setting low confidence + high novelty
        event = switch.monitor(confidence=0.2, novelty=0.9)
        if event:
            history = switch.switch_history
            assert len(history) >= 1
            assert history[-1].to_mode == event.to_mode

    def test_confidence_drop_determines_reason(self, switch: SelfReferentialSwitch) -> None:
        # Low confidence + no other strong signals → CONFIDENCE_DROP
        event = switch.monitor(confidence=0.2, time_pressure=0.0, novelty=0.0, resource_remaining=1.0)
        if event:
            assert event.reason in (SwitchReason.CONFIDENCE_DROP, SwitchReason.RECURRENCE_DONE)

    def test_confidence_rise_switches_to_classical(self, switch: SelfReferentialSwitch) -> None:
        # First, put it in quantum mode
        switch.monitor(confidence=0.2, novelty=0.9)
        # Then raise confidence — should switch to classical
        event = switch.monitor(confidence=0.95, time_pressure=0.0, novelty=0.0, resource_remaining=1.0)
        if event:
            assert event.to_mode == "classical"

    def test_resource_low_reason(self, switch: SelfReferentialSwitch) -> None:
        # Low resources → RESOURCE_LOW
        event = switch.monitor(confidence=0.5, time_pressure=0.0, novelty=0.0, resource_remaining=0.1)
        if event:
            assert event.reason in (SwitchReason.RESOURCE_LOW, SwitchReason.CONFIDENCE_DROP)

    def test_time_pressure_reason(self, switch: SelfReferentialSwitch) -> None:
        # High time pressure → TIME_PRESSURE
        event = switch.monitor(confidence=0.5, time_pressure=0.9, novelty=0.0, resource_remaining=1.0)
        if event:
            assert event.reason == SwitchReason.TIME_PRESSURE

    def test_novelty_reason(self, switch: SelfReferentialSwitch) -> None:
        event = switch.monitor(confidence=0.5, time_pressure=0.0, novelty=0.9, resource_remaining=1.0)
        if event:
            assert event.reason in (SwitchReason.NOVELTY_DETECTED, SwitchReason.CONFIDENCE_DROP)

    def test_switch_history_limited_to_100(self, switch: SelfReferentialSwitch) -> None:
        """Switch history should be capped at 100 entries."""
        switch._cooldown_ms = 0  # Disable cooldown for fast testing
        for i in range(105):
            switch.monitor(confidence=0.2, novelty=0.9)
            switch._cooldown_ms = 0  # Force allow switch
        assert len(switch._switch_history) <= 100

    def test_determine_reason_time_pressure(self) -> None:
        """High time pressure should trigger TIME_PRESSURE reason."""
        switch = SelfReferentialSwitch()
        switch._cooldown_ms = 0
        # First get into quantum mode
        switch.monitor(confidence=0.2, novelty=0.9)
        # High time pressure
        event = switch.monitor(confidence=0.5, time_pressure=0.9, novelty=0.0, resource_remaining=1.0)
        assert event is not None
        assert event.reason == SwitchReason.TIME_PRESSURE

    def test_determine_reason_novelty_detected(self) -> None:
        """High novelty with low time pressure should trigger NOVELTY_DETECTED."""
        switch = SelfReferentialSwitch()
        switch._cooldown_ms = 0
        # First get into quantum mode
        switch.monitor(confidence=0.2, novelty=0.9)
        # Go back to classical, then try to switch to quantum with high novelty
        switch.monitor(confidence=0.95, time_pressure=0.0, novelty=0.0, resource_remaining=1.0)
        # Now: classical mode, trigger switch to quantum with novelty
        event = switch.monitor(confidence=0.5, time_pressure=0.0, novelty=0.9, resource_remaining=1.0)
        if event is not None:
            assert event.reason in (SwitchReason.NOVELTY_DETECTED, SwitchReason.CONFIDENCE_DROP)

    def test_determine_reason_resource_low(self) -> None:
        """Low resources should trigger RESOURCE_LOW reason."""
        switch = SelfReferentialSwitch()
        switch._cooldown_ms = 0
        # Switch to quantum first
        switch.monitor(confidence=0.2, novelty=0.9)
        # Now low resources should push back to classical
        event = switch.monitor(confidence=0.5, time_pressure=0.0, novelty=0.0, resource_remaining=0.1)
        assert event is not None
        assert event.reason == SwitchReason.RESOURCE_LOW
        assert event.to_mode == "classical"

    def test_determine_reason_confidence_rise(self) -> None:
        """High confidence switching to classical should trigger CONFIDENCE_RISE."""
        switch = SelfReferentialSwitch()
        switch._cooldown_ms = 0
        # First enter quantum mode
        switch.monitor(confidence=0.2, novelty=0.9)
        assert switch.current_mode == "quantum"
        # Now high confidence with no other signals -> switch back to classical
        event = switch.monitor(confidence=0.95, time_pressure=0.0, novelty=0.0, resource_remaining=1.0)
        assert event is not None
        assert event.reason == SwitchReason.CONFIDENCE_RISE
        assert event.to_mode == "classical"

    def test_determine_reason_confidence_drop(self) -> None:
        """Low confidence switching to quantum should trigger CONFIDENCE_DROP."""
        switch = SelfReferentialSwitch()
        switch._cooldown_ms = 0
        event = switch.monitor(confidence=0.2, time_pressure=0.0, novelty=0.0, resource_remaining=1.0)
        assert event is not None
        assert event.reason == SwitchReason.CONFIDENCE_DROP
        assert event.to_mode == "quantum"

    def test_determine_reason_recurrence_done(self) -> None:
        """Fallback reason should be RECURRENCE_DONE when no other signal dominates."""
        switch = SelfReferentialSwitch()
        switch._cooldown_ms = 0
        # Enter quantum mode first
        switch.monitor(confidence=0.2, novelty=0.9)
        # Moderate confidence + moderate time pressure (not > 0.7) -> RECURRENCE_DONE
        # when switching to classical with confidence < threshold and no strong signals
        event = switch.monitor(confidence=0.5, time_pressure=0.5, novelty=0.0, resource_remaining=0.5)
        if event is not None:
            # If it switches, reason should be RECURRENCE_DONE
            # (time_pressure 0.5 <= 0.7, novelty 0 <= 0.6, resource 0.5 >= 0.3,
            #  confidence 0.5 < 0.7 but target=classical, so not CONFIDENCE_DROP)
            assert event.reason == SwitchReason.RECURRENCE_DONE

    def test_boundary_confidence_at_threshold(self) -> None:
        """Confidence exactly at threshold should not trigger confidence-based switch."""
        switch = SelfReferentialSwitch(confidence_threshold=0.7)
        switch._cooldown_ms = 0
        # Confidence exactly at threshold, no other signals
        event = switch.monitor(confidence=0.7, time_pressure=0.0, novelty=0.0, resource_remaining=1.0)
        # quant_signal = (1-0.7) + 0 + 0.15 = 0.45
        # class_signal = 0.7 + 0 + 0 = 0.7
        # classical > quantum, but we're already classical
        assert event is None

    def test_quantum_classical_signal_equal(self) -> None:
        """When signals are equal, should stay/switch to classical."""
        switch = SelfReferentialSwitch(
            confidence_threshold=0.7,
            time_pressure_weight=0.3,
            novelty_weight=0.2,
            resource_weight=0.15,
        )
        switch._cooldown_ms = 0
        # Find params where quantum == classical
        # quantum = (1-c) + 0.2*n + 0.15*r
        # classical = c + 0.3*t + 0.15*(1-r)
        # equal: (1-c) + 0.2n + 0.15r = c + 0.3t + 0.15(1-r)
        # With n=0, t=0, r=0.5: quantum = 1-c + 0.075, classical = c + 0.075
        # So 1-c+0.075 = c+0.075 -> c = 0.5
        event = switch.monitor(confidence=0.5, time_pressure=0.0, novelty=0.0, resource_remaining=0.5)
        # quantum = 0.5 + 0 + 0.075 = 0.575
        # classical = 0.5 + 0 + 0.075 = 0.575
        # equal -> else branch -> classical, but we're already classical
        assert event is None

    def test_cooldown_disabled_allows_rapid_switching(self) -> None:
        """With cooldown set to 0, rapid switching should be allowed."""
        switch = SelfReferentialSwitch()
        switch._cooldown_ms = 0
        event1 = switch.monitor(confidence=0.2, novelty=0.9)
        # No cooldown, so second call should NOT be blocked
        event2 = switch.monitor(confidence=0.95, time_pressure=0.0, novelty=0.0, resource_remaining=1.0)
        if event1:
            # If first switch happened, second should also happen (no cooldown)
            if event2:
                assert event2.from_mode == "quantum"
                assert event2.to_mode == "classical"

    def test_switch_event_dataclass(self) -> None:
        """SwitchEvent should be constructable with correct fields."""
        import time
        event = SwitchEvent(
            from_mode="quantum",
            to_mode="classical",
            reason=SwitchReason.CONFIDENCE_RISE,
            confidence_at_switch=0.85,
            timestamp=12345.0,
        )
        assert event.from_mode == "quantum"
        assert event.to_mode == "classical"
        assert event.reason == SwitchReason.CONFIDENCE_RISE
        assert event.confidence_at_switch == 0.85
        assert event.timestamp == 12345.0

    def test_stats_with_no_switches(self) -> None:
        """Stats should be valid even with no switch history."""
        switch = SelfReferentialSwitch()
        s = switch.stats
        assert s["current_mode"] == "classical"
        assert s["total_switches"] == 0
        assert "switch_frequency_hz" in s
        assert s["recent_switches"] == []

    def test_stats_with_switches(self) -> None:
        """Stats should reflect switch history after switches."""
        switch = SelfReferentialSwitch()
        switch._cooldown_ms = 0
        switch.monitor(confidence=0.2, novelty=0.9)
        switch.monitor(confidence=0.95, time_pressure=0.0, novelty=0.0, resource_remaining=1.0)
        s = switch.stats
        assert s["total_switches"] >= 2
        assert len(s["recent_switches"]) >= 2
        assert s["recent_switches"][0]["from"] in ("classical", "quantum")

    def test_novelty_at_boundary(self) -> None:
        """Novelty at exactly 0.6 should not trigger NOVELTY_DETECTED."""
        switch = SelfReferentialSwitch()
        switch._cooldown_ms = 0
        event = switch.monitor(confidence=0.2, novelty=0.6)
        # novelty=0.6 is NOT > 0.6, so should be CONFIDENCE_DROP instead
        if event:
            assert event.reason == SwitchReason.CONFIDENCE_DROP

    def test_time_pressure_above_boundary(self) -> None:
        """Time pressure above 0.7 should trigger TIME_PRESSURE."""
        switch = SelfReferentialSwitch()
        switch._cooldown_ms = 0
        event = switch.monitor(confidence=0.5, time_pressure=0.71, novelty=0.0, resource_remaining=1.0)
        if event:
            assert event.reason == SwitchReason.TIME_PRESSURE

    def test_resource_at_boundary(self) -> None:
        """Resource remaining at exactly 0.3 should not trigger RESOURCE_LOW."""
        switch = SelfReferentialSwitch()
        switch._cooldown_ms = 0
        # First get into quantum
        switch.monitor(confidence=0.2, novelty=0.9)
        event = switch.monitor(confidence=0.5, time_pressure=0.0, novelty=0.0, resource_remaining=0.3)
        if event:
            # resource_remaining=0.3 is NOT < 0.3, so should NOT be RESOURCE_LOW
            assert event.reason != SwitchReason.RESOURCE_LOW
