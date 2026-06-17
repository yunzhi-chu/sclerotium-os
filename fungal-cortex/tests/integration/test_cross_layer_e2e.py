"""Phase 8: Cross-layer integration E2E tests — 5 bridges end-to-end.

These tests verify that the 5 cross-layer bridges work together correctly,
simulating a complete signal flow from L0 (sensing) through L3 (debate),
L4 (execution), L5 (cluster), and back via feedback.
"""
import pytest
from src.adaptive.debate_adaptive_bridge import AdaptiveDebateBridge
from src.autonomous.immune_audit_bridge import ImmuneAuditBridge, ClaimFate
from src.autonomous.dag_cluster_bridge import DAGClusterBridge
from src.cluster.feedback_adaptive_bridge import ClusterFeedbackBridge
from src.core.cross_layer_emergence import CrossLayerEmergence
from src.core.self_healing import SelfHealingOrchestrator, WoundSeverity
from src.core.autonomous_governance import AutonomousGovernance, ChangeType


class TestE2ERegimeToExecution:
    """E2E: L0 regime change -> L3 debate adaptation -> L4 DAG -> L5 cluster -> L0 feedback."""

    def test_regime_adaptation_flow(self):
        """Simulate bear regime detected -> debate adapts -> task DAG built."""
        # L0: Regime detection (simulated) -> L3: Debate adaptation
        debate_bridge = AdaptiveDebateBridge()
        params = debate_bridge.adapt_from_regime("bear", 0, 0.9, 0.3)
        assert params.debate_rounds >= 2  # Bear = more cautious

        # L3 -> L4: Claims processed through spleen bridge
        spleen = ImmuneAuditBridge()
        claims = [
            spleen.process_claim("c1", "MACD bear cross", 1, 5, 0.3, debate_round=3),
            spleen.process_claim("c2", "RSI oversold", 5, 1, 0.8, debate_round=3),
        ]
        # One claim should be verified (passed to KG), one refuted (to causal trace)
        fates = [c.fate for c in claims]
        assert ClaimFate.VERIFIED_TO_KG in fates or ClaimFate.REFUTED_TO_CAUSAL in fates

        # L4 -> L5: DAG decomposition for verified claims
        dag_bridge = DAGClusterBridge()
        dag = {
            "nodes": [
                {"node_id": "n1", "skill": "regime_detect", "critical": True},
                {"node_id": "n2", "skill": "signal_generate"},
                {"node_id": "n3", "skill": "risk_assess"},
            ],
            "edges": [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}],
        }
        decomp = dag_bridge.decompose_dag(dag, "e2e-1")
        batch = dag_bridge.to_batch_input(decomp)
        assert len(batch) >= 3  # includes redundant copy for critical path

        # L5 -> L0: Feedback from cluster execution
        feedback_bridge = ClusterFeedbackBridge(cooldown_period=0.0)
        actions = feedback_bridge.sense_from_stats(
            sharpe=-0.2, win_rate=0.4, success_rate=0.6,
            agent_count=8, failure_count=3,
            specialty_perf={"strategy": 0.3}, specialty_fail={"strategy": 3},
        )
        # Should have at least safety_tighten signal
        signals = [a.signal.value for a in actions]
        assert len(actions) > 0
        assert "safety_tighten" in signals or "weight_decrease" in signals


class TestE2EEmergenceAndHealing:
    """E2E: Cross-layer emergence detection -> self-healing -> governance approval."""

    def test_emergence_to_healing(self):
        """Three-layer anomaly -> emergence -> wound detection -> healing pipeline."""
        # Detect cross-layer emergence
        ncc = CrossLayerEmergence(anomaly_threshold=0.4, coherence_min=0.5, recalibration_cooldown=0.0)
        ncc.observe_l0("regime_change", 0.7, 0.8, "New bear regime detected")
        ncc.observe_l3("debate_shift", 0.65, 0.7, "Debate refute rate escalated")
        ncc.observe_l5("agent_reorganization", 0.6, 0.75, "Strategy agents dying")

        level = ncc.get_current_level()
        assert level.value in ("conscious", "self_aware")

        # Self-healing triggered by the emergence
        sho = SelfHealingOrchestrator(auto_heal_max_severity=WoundSeverity.MODERATE)
        wound = sho.report_health("L5", "strategy_pool", 0.55, 3, 3,
                                  error_messages=["agent failure cascade", "strategy degradation"])
        assert wound is not None

        # Full healing pipeline
        cycle = sho.auto_heal(wound.wound_id, ["new_strategy_v2"], {"sharpe": 0.7})
        assert cycle is not None
        assert cycle.remodeling_result is not None

        # Governance approves the healing result
        ag = AutonomousGovernance(require_human_above_risk=0.6)
        prop = ag.submit_proposal(
            ChangeType.STRATEGY_MODIFICATION, "strategy_pool.rebalanced",
            proposed_value="healed_config", rationale="Post-healing rebalance",
            risk_level=0.2, source_layer="L5",
        )
        gate_in = {"debate": {"debate_results": [
            {"specialty": "tech", "approved": True}, {"specialty": "fund", "approved": True},
            {"specialty": "risk", "approved": True},
        ]}}
        dec = ag.review(prop.proposal_id, gate_inputs=gate_in)
        assert dec.decision.value in ("approved", "conditional")


class TestE2ESecurityAndRecovery:
    """E2E: Security breach -> rate limiting -> sandbox hardening -> audit chain."""

    def test_rate_limit_and_audit(self):
        """Rate limit enforced -> audit trail records tamper-proof chain."""
        from src.security.rate_limiter import RateLimiter
        from src.autonomous.audit_trail import AuditTrail

        rl = RateLimiter(default_limit=3, default_window=60.0, burst_multiplier=1.0)
        at = AuditTrail()

        # Simulate normal requests
        for i in range(3):
            rl.check("api-client-1")
            at.record("api_request", "client-1", {"req": i}, {"status": "ok"}, f"trace-{i}")

        # Rate limit triggers
        blocked = not rl.check("api-client-1")
        at.record("rate_limit", "rate_limiter",
                  {"client": "api-client-1"}, {"action": "blocked"}, "trace-rate")

        assert blocked
        integrity = at.verify_integrity()
        assert integrity["valid"]
        assert len(at._records) == 4

    def test_sandbox_and_governance(self):
        """Sandbox hardening -> governance approval for new deployment."""
        from src.security.sandbox_hardening import SandboxHardening, SecurityLevel
        from src.core.autonomous_governance import AutonomousGovernance, ChangeType

        sh = SandboxHardening()
        profile = sh.get_default_profile(SecurityLevel.STRICT)
        valid, issues = sh.validate_profile(profile)
        assert valid

        # Governance: request to deploy using this sandbox profile
        ag = AutonomousGovernance(require_human_above_risk=0.6)
        prop = ag.submit_proposal(
            ChangeType.AGENT_RECONFIGURATION, "sandbox.deployment_config",
            proposed_value={"profile": profile.name, "level": profile.security_level.value},
            rationale="Deploy with STRICT sandbox profile",
            risk_level=0.2, source_layer="security",
        )
        gate_in = {"debate": {"debate_results": [
            {"specialty": "risk", "approved": True}, {"specialty": "tech", "approved": True},
            {"specialty": "macro", "approved": True},
        ]}}
        dec = ag.review(prop.proposal_id, gate_inputs=gate_in)
        assert dec.decision.value in ("approved", "conditional")


class TestE2EFullSystem:
    """End-to-end: Complete system flow from market signal to final decision."""

    def test_complete_signal_flow(self):
        """Test that all 5 bridges can be connected in sequence."""
        # 1. L0: Regime detected -> L3 debate adaptation
        debate_bridge = AdaptiveDebateBridge()
        params = debate_bridge.adapt_from_regime("volatile", 2, 0.7, 0.5)

        # 2. L3: Claims debated -> L4 audit (Spleen)
        spleen = ImmuneAuditBridge()
        verified = spleen.process_claim("sig-1", "RSI bullish divergence", 5, 1, 0.85, params.debate_rounds)
        assert verified.fate == ClaimFate.VERIFIED_TO_KG

        # 3. L4: Audit stored + DAG built -> L5 cluster
        dag_bridge = DAGClusterBridge()
        dag = {
            "nodes": [{"node_id": "exec", "skill": "order_execute"}],
            "edges": [],
        }
        decomp = dag_bridge.decompose_dag(dag, "signal-1")
        batch = dag_bridge.to_batch_input(decomp)
        assert len(batch) >= 1

        # 4. L5: Cluster execution -> L0 feedback
        feedback = ClusterFeedbackBridge(cooldown_period=0.0)
        actions = feedback.sense_from_stats(0.8, 0.6, 0.9, 10, 0)
        assert len(actions) > 0

        # 5. Cross-layer emergence watches it all
        ncc = CrossLayerEmergence()
        ncc.observe_regime_change("equilibrium", "volatile", 0.7, 0.5)
        assert ncc.get_current_level().value in ("dormant", "pre_conscious", "conscious")
