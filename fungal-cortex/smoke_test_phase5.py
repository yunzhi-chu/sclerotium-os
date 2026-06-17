"""Phase 5 Smoke Test: 五座跨层级桥梁.

Tests all 5 cross-layer bridges:
  5.1 AdaptiveDebateBridge — L0 regime → L3 debate parameters (HPA↔Immune)
  5.2 ImmuneAuditBridge — L3 claims → L4 audit + KG (Spleen)
  5.3 DAGClusterBridge — L4 TaskDAG → L5 cluster (Neuromuscular Junction)
  5.4 ClusterFeedbackBridge — L5 cluster → L0 adaptive (Proprioception)
  5.5 UnifiedEventBus — Cross-layer circulatory system (upgraded EventBus)
"""

from __future__ import annotations

import asyncio
import time


def test_5_1_adaptive_debate_bridge() -> int:
    """Test L0→L3 HPA↔Immune bridge."""
    print("\n-- 5.1 AdaptiveDebateBridge (HPA<->Immune) --")
    from src.adaptive.debate_adaptive_bridge import (
        AdaptiveDebateBridge, ImmuneState, DebateParams,
    )

    bridge = AdaptiveDebateBridge()

    # Test bear trend → immunosuppression
    params_bear = bridge.adapt_from_regime("bear", 0, 0.9, 0.3)
    assert params_bear.debate_rounds >= 2, f"Bear should have >=2 rounds, got {params_bear.debate_rounds}"
    assert params_bear.bear_weight > params_bear.bull_weight, "Bear weight should > bull weight"
    assert params_bear.confidence_threshold >= 0.65, f"Bear threshold should be high, got {params_bear.confidence_threshold}"
    print(f"  [OK] bear_trend -> suppressed: rounds={params_bear.debate_rounds}, bear_w={params_bear.bear_weight}, bull_w={params_bear.bull_weight}, threshold={params_bear.confidence_threshold}")

    # Test bull trend → immune activation
    params_bull = bridge.adapt_from_regime("bull", 1, 0.85, 0.2)
    assert params_bull.debate_rounds <= 2, f"Bull should have <=2 rounds, got {params_bull.debate_rounds}"
    assert params_bull.bull_weight >= 1.0, f"Bull weight should be high, got {params_bull.bull_weight}"
    print(f"  [OK] bull_trend → activated: rounds={params_bull.debate_rounds}, bear_w={params_bull.bear_weight}, bull_w={params_bull.bull_weight}, threshold={params_bull.confidence_threshold}")

    # Test equilibrium → normal
    params_eq = bridge.adapt_from_regime("equilibrium", 2, 0.6, 1.0)
    assert bridge.get_immune_state() == ImmuneState.NORMAL
    print(f"  [OK] equilibrium → normal: rounds={params_eq.debate_rounds}, threshold={params_eq.confidence_threshold}")

    # Test crash → strong suppression (highest cortisol)
    params_crash = bridge.adapt_from_regime("crash", 0, 0.95, 0.1)
    assert bridge.get_immune_state() == ImmuneState.SUPPRESSED
    assert params_crash.debate_rounds >= 3
    print(f"  [OK] crash → suppressed: rounds={params_crash.debate_rounds}, bear_w={params_crash.bear_weight}")

    # Test feedback: debate outcome → regime adjustment
    feedback = bridge.feedback_to_regime(verified_claims=2, refuted_claims=8, total_claims=10)
    assert feedback["direction"] == "tighten", f"High refute rate should tighten, got {feedback['direction']}"
    print(f"  [OK] feedback: {feedback['direction']} (refute={feedback['refute_rate']:.1%})")

    # Test convenience method
    params_from_report = bridge.adapt_from_regime_report({
        "regime_label": "bear_volatile",
        "regime_index": 0,
        "confidence": 0.8,
        "entropy": 0.5,
    })
    assert params_from_report.debate_rounds >= 2
    print(f"  [OK] adapt_from_regime_report: rounds={params_from_report.debate_rounds}")

    # Stats
    stats = bridge.stats
    assert stats["immune_state"] is not None
    print(f"  [OK] stats: {stats}")

    print("  ✅ 5.1 PASSED")
    return 6


def test_5_2_immune_audit_bridge() -> int:
    """Test L3→L4 Spleen bridge."""
    print("\n── 5.2 ImmuneAuditBridge (Immune↔Audit) ──")
    from src.autonomous.immune_audit_bridge import ImmuneAuditBridge, ClaimFate

    bridge = ImmuneAuditBridge()

    # Test verified claim → KG
    verified = bridge.process_claim("claim-001", "MACD bullish cross", bull_votes=5, bear_votes=1, confidence=0.85, debate_round=2)
    assert verified.fate == ClaimFate.VERIFIED_TO_KG, f"Expected VERIFIED_TO_KG, got {verified.fate}"
    assert verified.net_price > 0
    print(f"  [OK] verified → KG: net_price={verified.net_price:.3f}, fate={verified.fate.value}")

    # Test refuted claim → causal
    refuted = bridge.process_claim("claim-002", "RSI overbought sell", bull_votes=1, bear_votes=6, confidence=0.3, debate_round=3)
    assert refuted.fate == ClaimFate.REFUTED_TO_CAUSAL, f"Expected REFUTED_TO_CAUSAL, got {refuted.fate}"
    assert refuted.net_price < 0
    print(f"  [OK] refuted → causal: net_price={refuted.net_price:.3f}, fate={refuted.fate.value}")

    # Test pending claim
    pending = bridge.process_claim("claim-003", "Uncertain signal", bull_votes=3, bear_votes=3, confidence=0.5, debate_round=1)
    assert pending.fate == ClaimFate.PENDING
    print(f"  [OK] pending: net_price={pending.net_price:.3f}, fate={pending.fate.value}")

    # Test batch processing
    batch = [
        {"claim_id": "c1", "summary": "Signal A", "bull_votes": 4, "bear_votes": 1, "confidence": 0.8},
        {"claim_id": "c2", "summary": "Signal B", "bull_votes": 1, "bear_votes": 4, "confidence": 0.3},
        {"claim_id": "c3", "summary": "Signal C", "bull_votes": 2, "bear_votes": 2, "confidence": 0.5},
    ]
    results = bridge.process_claims_batch(batch)
    assert len(results) == 3
    fates = [r.fate for r in results]
    assert ClaimFate.VERIFIED_TO_KG in fates
    assert ClaimFate.REFUTED_TO_CAUSAL in fates
    print(f"  [OK] batch={len(results)}: fates={[f.value for f in fates]}")

    # Test audit record generation
    audit_rec = bridge.generate_audit_record(verified)
    assert audit_rec["severity"] == "INFO"
    assert audit_rec["claim_id"] == "claim-001"
    print(f"  [OK] audit_record: severity={audit_rec['severity']}")

    # Test causal link generation
    causal_link = bridge.generate_causal_link(refuted)
    assert causal_link["link_type"] == "immune_refutation"
    print(f"  [OK] causal_link: type={causal_link['link_type']}")

    # Test KG input generation
    kg_input = bridge.generate_kg_input(verified)
    assert kg_input["entity_type"] == "immune_claim"
    print(f"  [OK] kg_input: entity_type={kg_input['entity_type']}")

    # Test pending resolution
    resolved = bridge.resolve_pending(pending.record_id, ClaimFate.VERIFIED_TO_KG)
    assert resolved is not None
    assert resolved.fate == ClaimFate.VERIFIED_TO_KG
    print(f"  [OK] resolved pending → {resolved.fate.value}")

    # Test statistics
    stats = bridge.get_statistics()
    assert stats.total_processed > 0
    print(f"  [OK] stats: total={stats.total_processed}, verified={stats.verified_count}, refuted={stats.refuted_count}, rate={stats.verify_rate:.1%}")

    print("  ✅ 5.2 PASSED")
    return 9


def test_5_3_dag_cluster_bridge() -> int:
    """Test L4→L5 Neuromuscular Junction bridge."""
    print("\n── 5.3 DAGClusterBridge (Neuromuscular Junction) ──")
    from src.autonomous.dag_cluster_bridge import (
        DAGClusterBridge, TaskPhase, RedundancyLevel, ClusterTask,
    )

    bridge = DAGClusterBridge(critical_path_redundancy=2)

    # Build a test DAG
    dag = {
        "dag_id": "test-dag-001",
        "nodes": [
            {"node_id": "n1", "skill": "regime_detect", "critical": True, "params": {"lookback": 60}},
            {"node_id": "n2", "skill": "signal_generate", "important": True, "params": {"strategy": "MACD"}},
            {"node_id": "n3", "skill": "risk_assess", "params": {"max_position": 0.1}},
            {"node_id": "n4", "skill": "backtest", "params": {"period": "90d"}},
            {"node_id": "n5", "skill": "order_execute", "optional": True, "params": {"amount": 1000}},
        ],
        "edges": [
            {"from": "n1", "to": "n2"},
            {"from": "n1", "to": "n3"},
            {"from": "n2", "to": "n4"},
            {"from": "n3", "to": "n4"},
            {"from": "n4", "to": "n5"},
        ],
    }

    # Test decomposition
    decomp = bridge.decompose_dag(dag, "test-dag-001")
    assert decomp.total_nodes == 5
    assert len(decomp.cluster_tasks) == 5
    assert len(decomp.parallel_groups) > 0, "Should have at least 1 parallel group"
    print(f"  [OK] decomposed: nodes={decomp.total_nodes}, tasks={len(decomp.cluster_tasks)}, groups={len(decomp.parallel_groups)}, cp_len={len(decomp.critical_path)}")

    # Test specialty mapping
    n1_task = bridge.get_task(f"task-test-dag-001-n1")
    assert n1_task is not None, "n1 task should exist"
    assert n1_task.specialty == "regime", f"n1 should be 'regime', got '{n1_task.specialty}'"
    assert n1_task.redundancy == RedundancyLevel.DUPLICATE, f"Critical task should be DUPLICATE, got {n1_task.redundancy}"
    print(f"  [OK] specialty mapping: n1→{n1_task.specialty}, redundancy={n1_task.redundancy.value}")

    # Test priority assignment
    assert n1_task.priority <= 3, f"Critical task priority should be high, got {n1_task.priority}"
    n5_task = bridge.get_task(f"task-test-dag-001-n5")
    assert n5_task is not None
    assert n5_task.priority >= 5, f"Optional task priority should be low, got {n5_task.priority}"
    print(f"  [OK] priority: critical={n1_task.priority}, optional={n5_task.priority}")

    # Test batch input conversion
    batch = bridge.to_batch_input(decomp)
    assert len(batch) > 5, f"Batch should include redundant copies (>5), got {len(batch)}"
    redundant_copies = [b for b in batch if "redundant_copy" in str(b.get("payload", {}).get("redundant_copy", False))]
    print(f"  [OK] batch_input: {len(batch)} entries (includes {len([b for b in batch if '-r' in b.get('task_id', '')])} redundant)")

    # Test lifecycle tracking
    for task in decomp.cluster_tasks[:3]:
        bridge.mark_started(task.task_id)
    phase_stats = bridge.get_phase_stats()
    assert phase_stats.get("contracting", 0) >= 3
    print(f"  [OK] started 3 tasks: phases={phase_stats}")

    for task in decomp.cluster_tasks[:2]:
        bridge.mark_completed(task.task_id)
    phase_stats = bridge.get_phase_stats()
    assert phase_stats.get("relaxing", 0) >= 2
    print(f"  [OK] completed 2 tasks: phases={phase_stats}")

    # Test critical path tasks
    cp_tasks = bridge.get_critical_path_tasks(decomp.decomposition_id)
    assert len(cp_tasks) > 0
    print(f"  [OK] critical_path: {len(cp_tasks)} tasks, redundant={decomp.redundant_tasks}")

    # Stats
    stats = bridge.stats
    assert stats["decompositions"] >= 1
    print(f"  [OK] stats: {stats}")

    print("  ✅ 5.3 PASSED")
    return 7


def test_5_4_cluster_feedback_bridge() -> int:
    """Test L5→L0 Proprioception bridge."""
    print("\n── 5.4 ClusterFeedbackBridge (Proprioception) ──")
    from src.cluster.feedback_adaptive_bridge import (
        ClusterFeedbackBridge, ProprioceptiveReading,
        FeedbackSignal, MuscleTone,
    )

    bridge = ClusterFeedbackBridge(
        sharpe_danger_threshold=0.0,
        failure_rate_threshold=0.3,
        cooldown_period=0.0,  # No cooldown for testing
    )

    # Test danger scenario: negative Sharpe → tighten safety
    danger_reading = ProprioceptiveReading(
        reading_id="r001", source="test",
        sharpe_ratio=-0.5, win_rate=0.35, success_rate=0.5,
        agent_count=10, failure_count=5,
        specialty_performance={"strategy": 0.3, "risk": 0.5},
        specialty_failures={"strategy": 4, "risk": 1},
    )
    actions = bridge.sense(danger_reading)
    signals = [a.signal for a in actions]
    assert FeedbackSignal.SAFETY_TIGHTEN in signals, f"Should contain SAFETY_TIGHTEN, got {[s.value for s in signals]}"
    assert FeedbackSignal.WEIGHT_DECREASE in signals, f"Should contain WEIGHT_DECREASE for failing specialty"
    print(f"  [OK] danger scenario: {len(actions)} actions: {[s.value for s in signals]}")

    # Verify safety tightening magnitude
    safety_action = next(a for a in actions if a.signal == FeedbackSignal.SAFETY_TIGHTEN)
    assert safety_action.target == "safety_gate"
    assert safety_action.recommended_value < safety_action.current_value
    print(f"  [OK] safety_tighten: {safety_action.current_value}→{safety_action.recommended_value:.2f}, magnitude={safety_action.adjustment_magnitude:.2f}")

    # Test healthy scenario: good Sharpe → relax
    healthy_reading = ProprioceptiveReading(
        reading_id="r002", source="test",
        sharpe_ratio=1.5, win_rate=0.65, success_rate=0.95,
        agent_count=10, failure_count=0,
        specialty_performance={"strategy": 0.85, "risk": 0.9},
        specialty_failures={"strategy": 0, "risk": 0},
    )
    # Force muscle tone to hypertonic to trigger relax
    bridge._muscle_tone = MuscleTone.HYPERTONIC
    actions2 = bridge.sense(healthy_reading)
    signals2 = [a.signal for a in actions2]
    print(f"  [OK] healthy scenario: {len(actions2)} actions: {[s.value for s in signals2]}")

    # Test convenience method
    actions3 = bridge.sense_from_stats(
        sharpe=-0.3, win_rate=0.4, success_rate=0.5,
        agent_count=8, failure_count=4,
        specialty_perf={"strategy": 0.3},
        specialty_fail={"strategy": 4},
    )
    assert len(actions3) > 0
    print(f"  [OK] sense_from_stats: {len(actions3)} actions")

    # Test muscle tone
    tone = bridge.get_muscle_tone()
    assert tone is not None
    print(f"  [OK] muscle_tone: {tone.value}")

    # Test L0 adjustment summary
    summary = bridge.get_l0_adjustment_summary()
    assert "muscle_tone" in summary
    assert "adjustments" in summary
    print(f"  [OK] l0_summary: tone={summary['muscle_tone']}, targets={list(summary['adjustments'].keys())}")

    # Test emergence detection
    emerge_reading = ProprioceptiveReading(
        reading_id="r003", source="test",
        sharpe_ratio=0.5, win_rate=0.55, success_rate=0.8,
        agent_count=10, failure_count=1,
        emergent_patterns=[
            {"name": "new_momentum_regime", "confidence": 0.7},
            {"name": "new_momentum_regime", "confidence": 0.8},
            {"name": "new_momentum_regime", "confidence": 0.75},
        ],
    )
    actions4 = bridge.sense(emerge_reading)
    regime_signals = [a for a in actions4 if a.signal == FeedbackSignal.REGIME_CANDIDATE]
    print(f"  [OK] emergence detection: {len(regime_signals)} regime candidates among {len(actions4)} actions")

    print("  ✅ 5.4 PASSED")
    return 6


async def test_5_5_unified_event_bus() -> int:
    """Test UnifiedEventBus (Circulatory System)."""
    print("\n── 5.5 UnifiedEventBus (Circulatory System) ──")
    from src.core.unified_event_bus import (
        UnifiedEventBus, UnifiedEvent, EventPriority, StandardEventType,
    )

    bus = UnifiedEventBus(
        db_path="data/test_event_backlog.db",
        enable_persistence=True,
    )

    # Collect dispatched events for verification
    received: list[dict[str, Any]] = []

    async def test_handler(topic: str, data: dict[str, Any]) -> None:
        received.append({"topic": topic, "data": data})

    # Subscribe to various layers
    bus.subscribe("L0.*", test_handler)
    bus.subscribe("L3.*", test_handler)
    bus.subscribe("L4.*", test_handler)
    bus.subscribe("L5.*", test_handler)

    # Test publishing standard events
    trace_id = bus.generate_trace_id()

    # L0 regime change (HIGH priority)
    ok = await bus.publish_regime_change("equilibrium", "bear", 0.85, source="hmm_detector")
    assert ok
    print(f"  [OK] publish_regime_change: ok={ok}")

    # L3 claim resolved (HIGH priority)
    ok = await bus.publish_claim_resolved("claim-abc", "verified", 0.72, trace_id=trace_id)
    assert ok
    print(f"  [OK] publish_claim_resolved: ok={ok}")

    # L4 task completed (NORMAL priority)
    ok = await bus.publish_task_completed("task-xyz", "dag-001", True, trace_id=trace_id)
    assert ok
    print(f"  [OK] publish_task_completed: ok={ok}")

    # L5 agent apoptosed (LOW priority)
    ok = await bus.publish_agent_apoptosed("agent-005", "low_performance", trace_id=trace_id)
    assert ok
    print(f"  [OK] publish_agent_apoptosed: ok={ok}")

    # Start and stop dispatch loop to flush events
    await bus.start()
    await asyncio.sleep(0.2)
    await bus.stop()

    # Verify events were dispatched
    assert len(received) >= 4, f"Should have received >=4 events, got {len(received)}"
    topics = [r["topic"] for r in received]
    assert "L0.regime_change" in topics
    assert "L3.claim_resolved" in topics
    assert "L4.task_completed" in topics
    assert "L5.agent_apoptosed" in topics
    print(f"  [OK] all 4 standard event types dispatched: {topics}")

    # Test causal trace
    trace = bus.get_causal_trace(trace_id)
    assert len(trace) >= 3, f"Trace should have >=3 events, got {len(trace)}"
    print(f"  [OK] causal_trace: {len(trace)} events for trace_id={trace_id}")

    # Test history filtering
    history = bus.get_history(limit=10, layer="L3")
    assert len(history) > 0
    print(f"  [OK] history filtered by L3: {len(history)} records")

    # Test layer stats
    layer_stats = bus.get_layer_stats()
    print(f"  [OK] layer_stats: {layer_stats}")

    # Test active traces
    active = bus.get_active_traces()
    assert trace_id in active
    print(f"  [OK] active_traces includes our trace: {len(active)} active")

    # Test persistence
    if bus._backlog:
        count = bus._backlog.count()
        assert count >= 4, f"Backlog should have >=4 events, got {count}"
        print(f"  [OK] backlog persistence: {count} events stored")

    # Test event priority auto-assignment
    assert bus._DEFAULT_PRIORITY_MAP["L0.circuit_breaker_trip"] == EventPriority.CRITICAL
    assert bus._DEFAULT_PRIORITY_MAP["L0.regime_change"] == EventPriority.HIGH
    print(f"  [OK] priority mapping: CRITICAL={EventPriority.CRITICAL.value}, HIGH={EventPriority.HIGH.value}, NORMAL={EventPriority.NORMAL.value}")

    # Clean up test DB
    import os
    try:
        os.remove("data/test_event_backlog.db")
    except OSError:
        pass

    print("  ✅ 5.5 PASSED")
    return 8


def main() -> None:
    print("=" * 60)
    print("Phase 5 Smoke Test: 五座跨层级桥梁")
    print("=" * 60)

    passed = 0
    total = 0

    # Sync tests
    for test_fn in [test_5_1_adaptive_debate_bridge, test_5_2_immune_audit_bridge,
                    test_5_3_dag_cluster_bridge, test_5_4_cluster_feedback_bridge]:
        try:
            n = test_fn()
            passed += 1
            total += n
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            import traceback
            traceback.print_exc()

    # Async test
    try:
        n = asyncio.run(test_5_5_unified_event_bus())
        passed += 1
        total += n
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passed}/5 bridges passed, {total} checks")
    if passed == 5:
        print("✅ ALL Phase 5 BRIDGES VERIFIED")
    else:
        print(f"⚠️  {5 - passed} bridge(s) failed")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
