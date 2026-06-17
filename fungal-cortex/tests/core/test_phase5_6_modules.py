"""Tests for Phase 5.5 + Phase 6 core modules."""
import pytest
import asyncio
from src.core.unified_event_bus import (
    UnifiedEventBus, UnifiedEvent, EventPriority, StandardEventType,
)
from src.core.cross_layer_emergence import (
    CrossLayerEmergence, EmergenceLevel, ShiftType,
)
from src.core.self_healing import (
    SelfHealingOrchestrator, HealingPhase, WoundSeverity, WoundType,
)
from src.core.autonomous_governance import (
    AutonomousGovernance, ChangeType, GovernanceDecision, GateResult,
)


class TestUnifiedEventBus:
    @pytest.mark.asyncio
    async def test_publish_standard_events(self):
        bus = UnifiedEventBus(db_path="data/test_core.db", enable_persistence=True)
        ok = await bus.publish_regime_change("eq", "bear", 0.9)
        assert ok
        ok = await bus.publish_claim_resolved("c1", "verified", 0.7)
        assert ok
        ok = await bus.publish_task_completed("t1", "d1", True)
        assert ok
        ok = await bus.publish_agent_apoptosed("a1", "low_perf")
        assert ok
        import os
        try:
            os.remove("data/test_core.db")
        except OSError:
            pass

    @pytest.mark.asyncio
    async def test_dispatch_and_trace(self):
        bus = UnifiedEventBus(db_path="data/test_dispatch.db")
        received = []
        async def handler(topic, data):
            received.append(topic)
        bus.subscribe("L0.*", handler)
        bus.subscribe("L3.*", handler)
        trace_id = bus.generate_trace_id()
        await bus.publish_regime_change("eq", "bear", 0.8)
        await bus.publish_claim_resolved("c1", "ok", 0.7, trace_id=trace_id)
        await bus.start()
        await asyncio.sleep(0.1)
        await bus.stop()
        assert len(received) >= 2
        import os
        try:
            os.remove("data/test_dispatch.db")
        except OSError:
            pass


class TestCrossLayerEmergence:
    def test_dormant_to_conscious(self):
        ncc = CrossLayerEmergence(anomaly_threshold=0.4, coherence_min=0.5, recalibration_cooldown=0.0)
        assert ncc.get_current_level() == EmergenceLevel.DORMANT
        ncc.observe_l0("drift", 0.6, 0.8)
        assert ncc.get_current_level() == EmergenceLevel.PRE_CONSCIOUS
        ncc.observe_l3("debate", 0.55, 0.7)
        ncc.observe_l5("agent_reorg", 0.65, 0.75)
        assert ncc.get_current_level() == EmergenceLevel.CONSCIOUS

    def test_structured_observation(self):
        ncc = CrossLayerEmergence(anomaly_threshold=0.3, coherence_min=0.4, recalibration_cooldown=0.0)
        ncc.observe_regime_change("equilibrium", "bear", 0.9, 0.4)
        ncc.observe_debate_shift(0.3, 0.65, 0.5, 0.7)
        ncc.observe_agent_reorganization({"strategy": -0.3}, -5, 0.8)
        events = ncc.get_recent_events()
        assert len(events) >= 1

    def test_ecotype_management(self):
        ncc = CrossLayerEmergence()
        eco = ncc.recognize_ecotype(
            "test_ecotype", "Test pattern",
            {"regime": "bear"}, {"refute_rate_min": 0.5}, {"specialty_shift": ["strategy"]},
        )
        assert eco.name == "test_ecotype"
        ecotypes = ncc.get_ecotypes()
        assert len(ecotypes) == 1

    def test_recalibration_execution(self):
        ncc = CrossLayerEmergence(anomaly_threshold=0.4, coherence_min=0.5, recalibration_cooldown=0.0)
        ncc.observe_l0("drift", 0.6, 0.8)
        ncc.observe_l3("debate", 0.55, 0.7)
        ncc.observe_l5("reorg", 0.65, 0.75)
        events = ncc.get_recent_events()
        if events:
            result = ncc.execute_recalibration(events[-1])
            assert result["status"] == "completed"


class TestSelfHealing:
    def test_wound_detection(self):
        sho = SelfHealingOrchestrator()
        wound = sho.report_health("L5", "agent_factory", 0.7, 2, 2, error_messages=["agent failure"])
        assert wound is not None
        assert wound.severity == WoundSeverity.MILD

    def test_healthy_no_wound(self):
        sho = SelfHealingOrchestrator()
        wound = sho.report_health("L0", "hmm", 0.95, 0, 0)
        assert wound is None

    def test_severe_wound(self):
        sho = SelfHealingOrchestrator()
        wound = sho.report_health("L3", "debate", 0.3, 5, 5)
        assert wound is not None
        assert wound.severity in (WoundSeverity.SEVERE, WoundSeverity.CRITICAL)

    def test_diagnose(self):
        sho = SelfHealingOrchestrator()
        wound = sho.report_health("L5", "test", 0.6, 1, 0)
        diag = sho.diagnose(wound.wound_id)
        assert "root_cause" in diag

    def test_repair_and_verify(self):
        sho = SelfHealingOrchestrator(auto_heal_max_severity=WoundSeverity.MODERATE)
        wound = sho.report_health("L5", "test", 0.7, 1, 0)
        repair = sho.repair(wound.wound_id, ["test_ability"])
        assert "actions_taken" in repair
        verify = sho.verify(wound.wound_id, {"sharpe": 0.8})
        assert "passed" in verify

    def test_auto_heal_pipeline(self):
        sho = SelfHealingOrchestrator(auto_heal_max_severity=WoundSeverity.MODERATE)
        wound = sho.report_health("L5", "test", 0.7, 1, 0)
        cycle = sho.auto_heal(wound.wound_id, ["ability"], {"sharpe": 0.6})
        assert cycle is not None


class TestAutonomousGovernance:
    def test_low_risk_approved(self):
        ag = AutonomousGovernance(require_human_above_risk=0.6)
        prop = ag.submit_proposal(ChangeType.PARAMETER_UPDATE, "test.param", 10, 5, risk_level=0.1)
        gate_in = {"debate": {"debate_results": [
            {"specialty": "tech", "approved": True}, {"specialty": "fund", "approved": True},
            {"specialty": "risk", "approved": True},
        ]}}
        dec = ag.review(prop.proposal_id, gate_inputs=gate_in)
        assert dec.decision == GovernanceDecision.APPROVED

    def test_policy_violation_rejected(self):
        ag = AutonomousGovernance()
        prop = ag.submit_proposal(ChangeType.PARAMETER_UPDATE, "risk.position_limit", 0.8, 0.15, risk_level=0.4)
        dec = ag.review(prop.proposal_id)
        assert dec.decision == GovernanceDecision.REJECTED

    def test_human_override(self):
        ag = AutonomousGovernance(require_human_above_risk=0.6)
        prop = ag.submit_proposal(ChangeType.PARAMETER_UPDATE, "test.param", 10, 5, risk_level=0.1)
        gate_in = {"debate": {"debate_results": [
            {"specialty": "tech", "approved": True}, {"specialty": "fund", "approved": True},
            {"specialty": "risk", "approved": True},
        ]}}
        ag.review(prop.proposal_id, gate_inputs=gate_in)
        override = ag.human_override(prop.proposal_id, True, "Approved")
        assert override.decision == GovernanceDecision.APPROVED

    def test_five_gate_statistics(self):
        ag = AutonomousGovernance(require_human_above_risk=0.6)
        prop = ag.submit_proposal(ChangeType.PARAMETER_UPDATE, "test.p", 5, 3, risk_level=0.15)
        gate_in = {"debate": {"debate_results": [
            {"specialty": "a", "approved": True}, {"specialty": "b", "approved": True},
            {"specialty": "c", "approved": True},
        ]}}
        ag.review(prop.proposal_id, gate_inputs=gate_in)
        stats = ag.get_gate_statistics()
        assert len(stats) >= 5

    def test_quarantine_flow(self):
        ag = AutonomousGovernance(quarantine_default=0.0)
        prop = ag.submit_proposal(ChangeType.KNOWLEDGE_GRAPH_EDIT, "kg.node", "delete", risk_level=0.3)
        gate_in = {"debate": {"debate_results": [
            {"specialty": "a", "approved": True}, {"specialty": "b", "approved": True},
            {"specialty": "c", "approved": True},
        ]}}
        ag.review(prop.proposal_id, gate_inputs=gate_in)
        q = ag.check_quarantine(prop.proposal_id)
        ag.release_from_quarantine(prop.proposal_id)
        q2 = ag.check_quarantine(prop.proposal_id)
        assert q2["status"] == "not_quarantined"
