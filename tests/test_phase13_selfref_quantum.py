"""Phase 13 灰度测试 — 自指涉·量子·P2P (L8+L9)。"""

import json
import time
import pytest

from kernel.self_referential import (
    SelfReferentialCompiler, GenomeSnapshot, SnapshotDiff,
)
from kernel.quantum_bridge import QuantumBridge, QuantumResult
from kernel.p2p_bridge import (
    P2PBridge, NodeInfo, KnowledgeSignature, SyncRequest,
)


# ═══════════════════════════════════════════════════════════════
# SelfReferentialCompiler
# ═══════════════════════════════════════════════════════════════

class TestSelfReferentialCompiler:
    @pytest.fixture
    def compiler(self, tmp_path):
        return SelfReferentialCompiler(snapshot_dir=str(tmp_path / "snapshots"))

    def test_checkpoint_empty(self, compiler):
        snap = compiler.checkpoint()
        assert snap.snapshot_id != ""
        assert snap.version == "4.0"

    def test_checkpoint_with_genome(self, compiler):
        class MockGenome:
            def to_dict(self):
                return {"nudge_threshold": 0.7}
        snap = compiler.checkpoint(genome=MockGenome())
        assert snap.genome["nudge_threshold"] == 0.7

    def test_checkpoint_with_fcpi(self, compiler):
        class MockTracker:
            def get_vector(self):
                class V:
                    def to_dict(self):
                        return {"coding": 0.8, "total": 0.75}
                return V()
        snap = compiler.checkpoint(fcpi_tracker=MockTracker())
        assert snap.fcpi["coding"] == 0.8

    def test_list_checkpoints(self, compiler):
        compiler.checkpoint(label="test1")
        compiler.checkpoint(label="test2")
        cps = compiler.list_checkpoints()
        assert len(cps) == 2

    def test_restore(self, compiler):
        compiler.checkpoint(label="restore_test")
        restored = compiler.restore("restore_test")
        assert restored is not None
        assert restored.version == "4.0"

    def test_restore_nonexistent(self, compiler):
        assert compiler.restore("nonexistent") is None

    def test_diff(self, compiler):
        compiler.checkpoint(label="v1")
        time.sleep(0.01)
        compiler.checkpoint(label="v2")
        diff = compiler.diff("v1", "v2")
        assert diff is not None

    def test_cleanup(self, compiler):
        for i in range(15):
            compiler.checkpoint(label=f"old_{i}")
        removed = compiler.cleanup(keep=5)
        assert removed == 10

    def test_genome_snapshot_frozen(self):
        s = GenomeSnapshot(snapshot_id="test")
        with pytest.raises(Exception):
            s.version = "5.0"  # type: ignore


# ═══════════════════════════════════════════════════════════════
# QuantumBridge
# ═══════════════════════════════════════════════════════════════

class TestQuantumBridge:
    @pytest.fixture
    def qb(self):
        return QuantumBridge()

    def test_gpu_detection(self, qb):
        assert isinstance(qb.gpu_available, bool)

    def test_backend(self, qb):
        assert qb.backend in ("gpu", "cpu")

    def test_optimize_cpu(self, qb):
        params = {"a": 0.5, "b": 0.7, "c": 0.3}
        result = qb.optimize_parameters(params)
        assert result.success
        assert result.backend in ("gpu", "cpu")
        assert len(result.result) == 3

    def test_optimize_with_constraints(self, qb):
        params = {"x": 50.0}
        constraints = {"x": (0.0, 100.0)}
        result = qb.optimize_parameters(params, constraints)
        assert 0.0 <= result.result["x"] <= 100.0

    def test_quantum_result_frozen(self):
        r = QuantumResult(success=True, backend="cpu")
        with pytest.raises(Exception):
            r.success = False  # type: ignore


# ═══════════════════════════════════════════════════════════════
# P2PBridge
# ═══════════════════════════════════════════════════════════════

class TestP2PBridge:
    @pytest.fixture
    def p2p(self):
        return P2PBridge(node_id="test_node")

    def test_sign_knowledge(self, p2p):
        sig = p2p.sign_knowledge("用户偏好函数式编程")
        assert sig.content_hash != ""
        assert sig.node_id == "test_node"

    def test_verify_knowledge(self, p2p):
        sig = p2p.sign_knowledge("测试知识")
        assert p2p.verify_knowledge(sig)

    def test_verify_tampered(self, p2p):
        sig = p2p.sign_knowledge("原内容")
        tampered = KnowledgeSignature(
            knowledge_id=sig.knowledge_id,
            content_hash="fake_hash",
            node_id="attacker",
            signature=sig.signature,
        )
        assert not p2p.verify_knowledge(tampered)

    def test_add_peer(self, p2p):
        p2p.add_peer("laptop", "192.168.1.100:9999",
                    capabilities=("memory", "evolution"))
        peers = p2p.list_peers()
        assert len(peers) == 1
        assert peers[0].node_id == "laptop"

    def test_remove_peer(self, p2p):
        p2p.add_peer("temp")
        assert p2p.remove_peer("temp")
        assert not p2p.remove_peer("temp")

    def test_create_sync_request(self, p2p):
        req = p2p.create_sync_request(["k1", "k2"])
        assert len(req.knowledge_ids) == 2

    def test_stats(self, p2p):
        p2p.add_peer("peer1")
        p2p.sign_knowledge("test")
        stats = p2p.get_stats()
        assert stats["peers"] == 1
        assert stats["knowledge_entries"] == 1


# ═══════════════════════════════════════════════════════════════
# 集成
# ═══════════════════════════════════════════════════════════════

class TestPhase13Integration:
    def test_full_checkpoint_cycle(self, tmp_path):
        compiler = SelfReferentialCompiler(str(tmp_path / "snapshots"))
        qb = QuantumBridge()
        p2p = P2PBridge(node_id="desktop")

        # 签名知识
        sig = p2p.sign_knowledge("FCPI vector: coding=0.8")
        assert p2p.verify_knowledge(sig)

        # 优化参数
        result = qb.optimize_parameters({"threshold": 0.5})
        assert result.success

        # 保存快照
        snap = compiler.checkpoint(
            label="integration_test",
        )
        assert snap.snapshot_id != ""

        # 列出
        cps = compiler.list_checkpoints()
        assert len(cps) == 1
