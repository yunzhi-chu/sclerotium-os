"""Tests for Phase 5.2-5.3: ImmuneAuditBridge + DAGClusterBridge."""
import pytest
from src.autonomous.immune_audit_bridge import ImmuneAuditBridge, ClaimFate
from src.autonomous.dag_cluster_bridge import (
    DAGClusterBridge, TaskPhase, RedundancyLevel,
)


class TestImmuneAuditBridge:
    def test_verified_claim_to_kg(self):
        bridge = ImmuneAuditBridge()
        record = bridge.process_claim("c1", "MACD cross", bull_votes=5, bear_votes=1, confidence=0.85)
        assert record.fate == ClaimFate.VERIFIED_TO_KG

    def test_refuted_claim_to_causal(self):
        bridge = ImmuneAuditBridge()
        record = bridge.process_claim("c2", "Bad signal", bull_votes=1, bear_votes=6, confidence=0.3)
        assert record.fate == ClaimFate.REFUTED_TO_CAUSAL

    def test_pending_claim(self):
        bridge = ImmuneAuditBridge()
        record = bridge.process_claim("c3", "Uncertain", bull_votes=3, bear_votes=3, confidence=0.5)
        assert record.fate == ClaimFate.PENDING

    def test_batch_processing(self):
        bridge = ImmuneAuditBridge()
        batch = [
            {"claim_id": "a", "summary": "A", "bull_votes": 4, "bear_votes": 1, "confidence": 0.8},
            {"claim_id": "b", "summary": "B", "bull_votes": 1, "bear_votes": 4, "confidence": 0.3},
        ]
        results = bridge.process_claims_batch(batch)
        assert len(results) == 2

    def test_resolve_pending(self):
        bridge = ImmuneAuditBridge()
        record = bridge.process_claim("c4", "Pending", bull_votes=2, bear_votes=2, confidence=0.5)
        resolved = bridge.resolve_pending(record.record_id, ClaimFate.VERIFIED_TO_KG)
        assert resolved is not None
        assert resolved.fate == ClaimFate.VERIFIED_TO_KG

    def test_audit_record_generation(self):
        bridge = ImmuneAuditBridge()
        record = bridge.process_claim("c5", "Test", bull_votes=5, bear_votes=1, confidence=0.9)
        audit = bridge.generate_audit_record(record)
        assert audit["severity"] == "INFO"

    def test_statistics(self):
        bridge = ImmuneAuditBridge()
        bridge.process_claim("c6", "Test", bull_votes=4, bear_votes=1, confidence=0.8)
        stats = bridge.get_statistics()
        assert stats.total_processed > 0


class TestDAGClusterBridge:
    def test_decompose_dag(self):
        bridge = DAGClusterBridge()
        dag = {
            "dag_id": "test-1",
            "nodes": [
                {"node_id": "n1", "skill": "regime_detect", "critical": True},
                {"node_id": "n2", "skill": "signal_generate"},
                {"node_id": "n3", "skill": "backtest"},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
                {"from": "n2", "to": "n3"},
            ],
        }
        decomp = bridge.decompose_dag(dag, "test-1")
        assert decomp.total_nodes == 3
        assert len(decomp.cluster_tasks) == 3
        assert len(decomp.critical_path) > 0

    def test_specialty_mapping(self):
        bridge = DAGClusterBridge()
        dag = {
            "nodes": [{"node_id": "n1", "skill": "regime_detect", "critical": True}],
            "edges": [],
        }
        decomp = bridge.decompose_dag(dag, "t")
        task = decomp.cluster_tasks[0]
        assert task.specialty == "regime"

    def test_batch_input_generation(self):
        bridge = DAGClusterBridge()
        dag = {
            "nodes": [
                {"node_id": "n1", "skill": "regime_detect", "critical": True},
                {"node_id": "n2", "skill": "signal_generate"},
            ],
            "edges": [{"from": "n1", "to": "n2"}],
        }
        decomp = bridge.decompose_dag(dag, "t")
        batch = bridge.to_batch_input(decomp)
        assert len(batch) >= 2  # Includes redundant copies

    def test_lifecycle_tracking(self):
        bridge = DAGClusterBridge()
        dag = {
            "nodes": [{"node_id": "n1", "skill": "backtest"}],
            "edges": [],
        }
        decomp = bridge.decompose_dag(dag, "t")
        task = decomp.cluster_tasks[0]
        bridge.mark_started(task.task_id)
        assert task.phase == TaskPhase.CONTRACTING
        bridge.mark_completed(task.task_id)
        assert task.phase == TaskPhase.RELAXING
