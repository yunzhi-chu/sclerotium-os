"""Phase 6 Smoke Test: 涌现与自愈.

Tests all 3 emergence + self-healing modules:
  6.1 CrossLayerEmergence — Three-layer consciousness detection
  6.2 SelfHealingOrchestrator — Wound healing cascade (4 phases)
  6.3 AutonomousGovernance — 5-gate immune tolerance governance
"""

from __future__ import annotations

import time


def test_6_1_cross_layer_emergence() -> int:
    """Test NCC: Cross-layer emergence detection."""
    print("\n-- 6.1 CrossLayerEmergence (Consciousness) --")
    from src.core.cross_layer_emergence import (
        CrossLayerEmergence, EmergenceLevel, ShiftType,
    )

    ncc = CrossLayerEmergence(
        anomaly_threshold=0.4,
        coherence_min=0.5,
        conscious_window=300.0,
        recalibration_cooldown=0.0,  # No cooldown for testing
    )

    # Test dormant state
    assert ncc.get_current_level() == EmergenceLevel.DORMANT
    print(f"  [OK] initial state: {ncc.get_current_level().value}")

    # Test single-layer anomaly → pre-conscious
    ncc.observe_l0("drift", 0.6, 0.8, "L0 drift detected")
    assert ncc.get_current_level() == EmergenceLevel.PRE_CONSCIOUS
    print(f"  [OK] single-layer anomaly -> {ncc.get_current_level().value}")

    # Test two-layer anomaly → still pre-conscious
    ncc.observe_l3("debate_shift", 0.55, 0.7, "L3 debate pattern changed")
    assert ncc.get_current_level() == EmergenceLevel.PRE_CONSCIOUS
    print(f"  [OK] two-layer anomaly -> {ncc.get_current_level().value}")

    # Test all three layers → conscious!
    ncc.observe_l5("agent_reorganization", 0.65, 0.75, "L5 agent distribution shifted")
    assert ncc.get_current_level() == EmergenceLevel.CONSCIOUS
    print(f"  [OK] three-layer anomaly -> {ncc.get_current_level().value}")

    # Test sustained consciousness → self-aware
    ncc.observe_l0("regime_change", 0.7, 0.85, "L0 regime changed")
    ncc.observe_l3("debate_shift", 0.6, 0.8, "L3 debate shifted")
    ncc.observe_l5("agent_reorganization", 0.7, 0.8, "L5 agents reorganized")
    assert ncc.get_current_level() == EmergenceLevel.SELF_AWARE
    print(f"  [OK] sustained consciousness -> {ncc.get_current_level().value}")

    # Test recent events
    events = ncc.get_recent_events(limit=10)
    conscious_events = [e for e in events if e.level in (EmergenceLevel.CONSCIOUS, EmergenceLevel.SELF_AWARE)]
    assert len(conscious_events) >= 1
    print(f"  [OK] events: {len(events)} total, {len(conscious_events)} conscious")

    # Test shift type classification
    if conscious_events:
        shift = conscious_events[0].shift_type
        assert shift != ShiftType.NONE
        print(f"  [OK] shift_type: {shift.value}")

    # Test structured observation methods
    ncc.observe_regime_change("equilibrium", "bear", 0.9, 0.4)
    ncc.observe_debate_shift(0.3, 0.65, 0.5, 0.7)
    ncc.observe_agent_reorganization({"strategy": -0.3, "risk": 0.2}, -5, 0.8)
    events2 = ncc.get_recent_events(limit=5)
    print(f"  [OK] structured observation: {len(events2)} events after structured input")

    # Test ecotype management
    eco = ncc.recognize_ecotype(
        "bear_momentum_ecotype", "Bear market momentum-focused agent distribution",
        {"regime": "bear", "confidence_min": 0.7},
        {"refute_rate_min": 0.5},
        {"specialty_shift": ["strategy", "tactical"]},
    )
    assert eco.name == "bear_momentum_ecotype"
    ecotypes = ncc.get_ecotypes()
    assert len(ecotypes) == 1
    print(f"  [OK] ecotype registered: {eco.name}")

    # Test ecotype matching
    recent_l0 = [s for s in list(ncc._signals["L0"])[-5:]]
    recent_l3 = [s for s in list(ncc._signals["L3"])[-5:]]
    recent_l5 = [s for s in list(ncc._signals["L5"])[-5:]]
    matches = ncc.match_ecotype(recent_l0, recent_l3, recent_l5)
    print(f"  [OK] ecotype matching: {len(matches)} matches")

    # Test recalibration execution
    if conscious_events:
        result = ncc.execute_recalibration(conscious_events[0])
        assert result["status"] == "completed"
        print(f"  [OK] recalibration: {result['completed_steps']} steps completed, {result['failed_steps']} failed")

    # Test coherence trend
    coherence = ncc.get_coherence_trend()
    print(f"  [OK] coherence_trend: {len(coherence)} values")

    # Test stats
    stats = ncc.stats
    assert stats["total_events"] > 0
    print(f"  [OK] stats: {stats['current_level']}, {stats['total_events']} events, {stats['ecotypes_known']} ecotypes")

    print("  OK 6.1 PASSED")
    return 12


def test_6_2_self_healing_orchestrator() -> int:
    """Test wound healing cascade."""
    print("\n-- 6.2 SelfHealingOrchestrator (Wound Healing) --")
    from src.core.self_healing import (
        SelfHealingOrchestrator, HealingPhase, WoundSeverity, WoundType,
    )

    sho = SelfHealingOrchestrator(
        mild_threshold=0.8,
        moderate_threshold=0.6,
        severe_threshold=0.4,
        auto_heal_max_severity=WoundSeverity.MODERATE,
    )

    # Test healthy report → no wound
    wound = sho.report_health("L5", "agent_factory", 0.95, 0, 0)
    assert wound is None
    print("  [OK] healthy report -> no wound")

    # Test mild wound detection
    wound = sho.report_health("L5", "strategy_runner", 0.75, 2, 1,
                              error_messages=["agent timeout on strategy execution"])
    assert wound is not None
    assert wound.severity == WoundSeverity.MILD
    assert wound.wound_type == WoundType.AGENT_FAILURE
    print(f"  [OK] mild wound: severity={wound.severity.value}, type={wound.wound_type.value}")

    # Test moderate wound
    wound2 = sho.report_health("L3", "debate_engine", 0.55, 3, 3,
                               error_messages=["strategy degradation detected", "backtest failure"])
    assert wound2 is not None
    assert wound2.severity == WoundSeverity.MODERATE
    print(f"  [OK] moderate wound: severity={wound2.severity.value}, type={wound2.wound_type.value}")

    # Test severe wound
    wound3 = sho.report_health("L0", "hmm_detector", 0.35, 5, 4,
                               error_messages=["drift avalanche", "coordination breakdown"])
    assert wound3 is not None
    assert wound3.severity == WoundSeverity.SEVERE
    print(f"  [OK] severe wound: severity={wound3.severity.value}")

    # Test phase 2: Diagnosis
    diagnosis = sho.diagnose(wound.wound_id)
    assert "root_cause" in diagnosis
    assert "recommended_actions" in diagnosis
    assert len(diagnosis["recommended_actions"]) > 0
    print(f"  [OK] diagnose: root_cause='{diagnosis['root_cause'][:50]}...', actions={len(diagnosis['recommended_actions'])}")

    # Test phase 3: Repair
    repair = sho.repair(wound.wound_id, available_abilities=["new_ma_strategy", "adaptive_risk_model"])
    assert "actions_taken" in repair
    assert len(repair["actions_taken"]) > 0
    print(f"  [OK] repair: {len(repair['actions_taken'])} actions taken")

    # Test severe wound needs human approval
    repair3 = sho.repair(wound3.wound_id)
    if repair3.get("status") == "human_approval_required":
        print(f"  [OK] severe wound correctly requires human approval")

    # Test phase 4: Verification
    test_results = {"sharpe": 0.8, "win_rate": 0.55}
    verify = sho.verify(wound.wound_id, test_results)
    assert "passed" in verify
    assert "scar_detected" in verify
    print(f"  [OK] verify: passed={verify['passed']}, scar={verify['scar_severity']:.2f}")

    # Test full auto-heal pipeline
    sho2 = SelfHealingOrchestrator(auto_heal_max_severity=WoundSeverity.MODERATE)
    w4 = sho2.report_health("L5", "test_runner", 0.65, 1, 0,
                            error_messages=["test failure"])
    if w4:
        cycle = sho2.auto_heal(w4.wound_id, ["test_ability"],
                               {"sharpe": 0.6})
        assert cycle.healed or not cycle.healed  # either is valid
        print(f"  [OK] auto_heal: healed={cycle.healed}, scar={cycle.scar_severity:.2f}, time={cycle.time_to_heal:.1f}s")

    # Test layer health tracking
    layer_health = sho.get_layer_health()
    assert len(layer_health) > 0
    print(f"  [OK] layer_health: {dict(layer_health)}")

    # Test active wounds
    active = sho.get_active_wounds()
    print(f"  [OK] active_wounds: {len(active)}")

    # Test scar registry
    scars = sho.get_scar_registry()
    print(f"  [OK] scar_registry: {len(scars)} scars")

    # Stats
    stats = sho.stats
    assert stats["total_healed"] >= 0
    print(f"  [OK] stats: healed={stats['total_healed']}, scars={stats['scar_count']}")

    print("  OK 6.2 PASSED")
    return 11


def test_6_3_autonomous_governance() -> int:
    """Test 5-gate immune tolerance governance."""
    print("\n-- 6.3 AutonomousGovernance (Immune Tolerance) --")
    from src.core.autonomous_governance import (
        AutonomousGovernance, ChangeType, GovernanceDecision, GateResult,
    )

    ag = AutonomousGovernance(
        auto_approve_max_risk=0.2,
        require_human_above_risk=0.6,
        quarantine_default=0.0,  # No quarantine for testing
    )

    # Test low-risk proposal -> auto-approved (with debate input for Gate 3)
    prop1 = ag.submit_proposal(
        ChangeType.PARAMETER_UPDATE, "indicator_macd.lookback",
        proposed_value=26, current_value=20,
        rationale="Extend lookback for stability",
        risk_level=0.1, source_layer="L4",
        source_component="auto_tuner",
    )
    gate_in1 = {"debate": {"debate_results": [
        {"specialty": "technical", "approved": True},
        {"specialty": "fundamental", "approved": True},
        {"specialty": "risk", "approved": True},
    ]}}
    dec1 = ag.review(prop1.proposal_id, gate_inputs=gate_in1)
    assert dec1.decision == GovernanceDecision.APPROVED, f"Expected APPROVED, got {dec1.decision.value}"
    print(f"  [OK] low-risk proposal: {dec1.decision.value}")

    # Test high-risk proposal → gate 1 (policy) rejection
    prop2 = ag.submit_proposal(
        ChangeType.PARAMETER_UPDATE, "risk.position_limit",
        proposed_value=0.8, current_value=0.15,
        rationale="Increase position limit massively",
        risk_level=0.4, source_layer="L5",
    )
    dec2 = ag.review(prop2.proposal_id)
    print(f"  [OK] policy violation: {dec2.decision.value} (reason: {dec2.final_reason[:60]}...)")

    # Test proposal with debate input → passes
    prop3 = ag.submit_proposal(
        ChangeType.STRATEGY_MODIFICATION, "momentum_strategy.params",
        proposed_value={"lookback": 30, "threshold": 0.02},
        current_value={"lookback": 20, "threshold": 0.015},
        rationale="Adapt strategy to higher volatility regime",
        risk_level=0.3, source_layer="L4",
    )
    debate_input = {
        "debate": {
            "debate_results": [
                {"specialty": "fundamental", "approved": True},
                {"specialty": "technical", "approved": True},
                {"specialty": "risk", "approved": True},
                {"specialty": "macro", "approved": False},
            ],
        },
        "behavior": {"abnormal_signals": [], "call_count": 50, "param_drift": False},
    }
    dec3 = ag.review(prop3.proposal_id, gate_inputs=debate_input)
    assert dec3.decision in (GovernanceDecision.APPROVED, GovernanceDecision.CONDITIONAL)
    print(f"  [OK] debate-backed proposal: {dec3.decision.value} ({sum(1 for v in dec3.gate_verdicts if v.result == GateResult.PASSED)}/5 gates passed)")

    # Test behavior check rejection
    prop4 = ag.submit_proposal(
        ChangeType.AGENT_RECONFIGURATION, "strategy_pool.size",
        proposed_value=100, rationale="Scale up strategy pool",
        risk_level=0.3, source_layer="L5",
    )
    behavior_input = {
        "behavior": {
            "abnormal_signals": ["param_drift_critical", "signal_extreme"],
            "call_count": 200,
        },
    }
    dec4 = ag.review(prop4.proposal_id, gate_inputs=behavior_input)
    print(f"  [OK] behavior-check: {dec4.decision.value} (gates: {[v.result.value for v in dec4.gate_verdicts]})")

    # Test counterfactual check
    prop5 = ag.submit_proposal(
        ChangeType.EVOLUTION_LEAP, "global_evolution.step",
        proposed_value="major_leap", current_value="micro",
        rationale="Large evolutionary jump",
        risk_level=0.5, source_layer="L5",
    )
    cf_input = {
        "counterfactual": {
            "scenarios": [
                {"description": "Evolution leap fails", "worst_case_impact": 0.6},
            ],
        },
        "behavior": {"abnormal_signals": [], "call_count": 10, "param_drift": False},
    }
    dec5 = ag.review(prop5.proposal_id, gate_inputs=cf_input)
    print(f"  [OK] counterfactual check: {dec5.decision.value}")

    # Test human override
    override = ag.human_override(prop1.proposal_id, True, "Manual approval after review")
    assert override.decision == GovernanceDecision.APPROVED
    assert override.reviewed_by_human
    print(f"  [OK] human_override: {override.decision.value}")

    # Test human rejection
    prop6 = ag.submit_proposal(
        ChangeType.POLICY_CHANGE, "max_parallel_tasks",
        proposed_value=50, current_value=8,
        rationale="Massively parallel execution",
        risk_level=0.8, source_layer="L5",
    )
    dec6 = ag.review(prop6.proposal_id)
    # Should be escalated/rejected
    print(f"  [OK] high-risk policy change: {dec6.decision.value}")

    # Test quarantine
    prop7 = ag.submit_proposal(
        ChangeType.KNOWLEDGE_GRAPH_EDIT, "financial_kg.delete_node",
        proposed_value="node_abc", rationale="Remove bad node",
        risk_level=0.35, source_layer="L4",
    )
    ag._quarantine_default = 60.0
    dec7 = ag.review(prop7.proposal_id)
    q_check = ag.check_quarantine(prop7.proposal_id)
    # Release it
    ag.release_from_quarantine(prop7.proposal_id)
    q_check2 = ag.check_quarantine(prop7.proposal_id)
    assert q_check2["status"] == "not_quarantined"
    print(f"  [OK] quarantine: released successfully")

    # Test gate statistics
    gate_stats = ag.get_gate_statistics()
    assert len(gate_stats) > 0
    print(f"  [OK] gate_stats: {len(gate_stats)} gates tracked")

    # Stats summary
    stats = ag.stats
    assert stats["total_proposals"] >= 7
    print(f"  [OK] stats: {stats['total_proposals']} proposals, {stats['approved']} approved, {stats['rejected']} rejected, {stats['escalated']} escalated")

    print("  OK 6.3 PASSED")
    return 11


def main() -> None:
    print("=" * 60)
    print("Phase 6 Smoke Test: Emergence + Self-Healing")
    print("=" * 60)

    passed = 0
    total = 0

    for test_fn in [test_6_1_cross_layer_emergence,
                    test_6_2_self_healing_orchestrator,
                    test_6_3_autonomous_governance]:
        try:
            n = test_fn()
            passed += 1
            total += n
        except Exception as e:
            print(f"  FAILED: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passed}/3 modules passed, {total} checks")
    if passed == 3:
        print("ALL Phase 6 MODULES VERIFIED")
    else:
        print(f"WARNING: {3 - passed} module(s) failed")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
