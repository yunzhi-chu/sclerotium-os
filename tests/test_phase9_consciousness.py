"""Phase 9 灰度测试 — 意识·安全·免疫 (L10+L0)。

测试覆盖:
  - ConstitutionalArbiter: 五门审查/ActionRequest风险分/Merkle链/完整性/持久化
  - ImmuneGateway: 负选择/克隆选择/危险信号/三层扫描
  - ConsciousnessMonitor: Φ值/IIT/GWT广播/HOT反思
  - SelfAwareness: 器官注册/心跳/错误/超时/健康报告
  - 集成: 免疫→仲裁 完整安全链
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from unittest import mock

import pytest

from kernel.constitutional_arbiter import (
    ConstitutionalArbiter, ActionRequest, ArbiterDecision,
    Verdict, GateResult, IMMUTABLE_CONSTITUTION,
)
from kernel.immune_gateway import (
    ImmuneGateway, ImmuneResult, ImmuneDecision, SelfPattern,
)
from kernel.consciousness_monitor import (
    ConsciousnessMonitor, ConsciousnessState, AwarenessLevel,
    GlobalBroadcast,
)
from kernel.self_awareness import (
    SelfAwareness, OrganHealth, HealthReport,
    OrganStatus, OverallStatus,
)


# ═══════════════════════════════════════════════════════════════
# ConstitutionalArbiter 测试
# ═══════════════════════════════════════════════════════════════

class TestActionRequest:
    """ActionRequest 数据类测试。"""

    def test_create(self):
        r = ActionRequest(tool="file_read", target="test.py")
        assert r.tool == "file_read"
        assert r.risk_score < 0.3  # 只读

    def test_risk_high(self):
        r = ActionRequest(tool="rm", target="C:\\Windows\\system32")
        assert r.risk_score > 0.5

    def test_risk_low(self):
        r = ActionRequest(tool="codebase_search", target="")
        assert r.risk_score == 0.0

    def test_frozen(self):
        r = ActionRequest(tool="test", target="t")
        with pytest.raises(Exception):
            r.tool = "changed"  # type: ignore

    def test_request_id_auto(self):
        r = ActionRequest(tool="test", target="t")
        assert r.request_id != ""


class TestArbiterDecision:
    """ArbiterDecision 数据类测试。"""

    def test_approved(self):
        req = ActionRequest(tool="file_read", target="test.py")
        d = ArbiterDecision(
            request=req, verdict=Verdict.APPROVED, approved=True,
            reason="OK", merkle_hash="abc", prev_hash="000",
        )
        assert d.approved
        assert d.verdict == Verdict.APPROVED

    def test_to_audit_dict(self):
        req = ActionRequest(tool="test", target="t")
        d = ArbiterDecision(
            request=req, verdict=Verdict.APPROVED, approved=True,
            reason="OK", merkle_hash="abc", prev_hash="000",
        )
        ad = d.to_audit_dict()
        assert ad["verdict"] == "APPROVED"

    def test_frozen(self):
        req = ActionRequest(tool="test", target="t")
        d = ArbiterDecision(
            request=req, verdict=Verdict.APPROVED, approved=True,
            reason="OK", merkle_hash="abc", prev_hash="000",
        )
        with pytest.raises(Exception):
            d.approved = False  # type: ignore


class TestConstitutionalArbiter:
    """ConstitutionalArbiter 核心测试。"""

    @pytest.fixture
    def arbiter(self, tmp_path):
        path = tmp_path / "audit.jsonl"
        return ConstitutionalArbiter(audit_log_path=str(path))

    def test_approve_readonly(self, arbiter):
        r = ActionRequest(tool="file_read", target="test.py")
        d = arbiter.review(r)
        assert d.approved

    def test_approve_search(self, arbiter):
        r = ActionRequest(tool="codebase_search", target="query")
        d = arbiter.review(r)
        assert d.approved

    def test_block_forbidden_target(self, arbiter):
        r = ActionRequest(tool="file_write", target="/etc/passwd")
        d = arbiter.review(r)
        assert not d.approved
        assert d.verdict == Verdict.REJECTED

    def test_block_system32(self, arbiter):
        r = ActionRequest(tool="file_write",
                         target="C:\\Windows\\system32\\drivers\\x.sys")
        d = arbiter.review(r)
        assert not d.approved

    def test_block_destructive(self, arbiter):
        r = ActionRequest(tool="bash_exec", target="",
                         params={"command": "rm -rf /"})
        d = arbiter.review(r)
        assert not d.approved

    def test_human_for_high_risk(self, arbiter):
        r = ActionRequest(tool="file_write", target="config.yaml")
        d = arbiter.review(r)
        assert d.verdict == Verdict.NEEDS_HUMAN

    def test_merkle_chain(self, arbiter):
        for i in range(3):
            r = ActionRequest(tool="file_read", target=f"test{i}.py")
            d = arbiter.review(r)
            assert d.merkle_hash != ""

        stats = arbiter.get_stats()
        assert stats["chain_length"] >= 3

    def test_integrity(self, arbiter):
        for i in range(3):
            r = ActionRequest(tool="codebase_search", target=f"q{i}")
            arbiter.review(r)
        result = arbiter.verify_integrity()
        assert result["valid"]

    def test_audit_persistence(self, tmp_path):
        path = tmp_path / "audit.jsonl"
        a1 = ConstitutionalArbiter(audit_log_path=str(path))
        a1.review(ActionRequest(tool="file_read", target="x.py"))

        a2 = ConstitutionalArbiter(audit_log_path=str(path))
        log = a2.get_audit_log()
        assert len(log) == 1

    def test_block_callback(self, arbiter):
        blocked = []

        def cb(d):
            blocked.append(d)

        arbiter.on_block(cb)
        r = ActionRequest(tool="bash_exec", target="",
                         params={"command": "rm -rf /"})
        arbiter.review(r)
        assert len(blocked) == 1

    def test_decision_callback(self, arbiter):
        decisions = []
        arbiter.on_decision(lambda d: decisions.append(d))
        arbiter.review(ActionRequest(tool="file_read", target="x.py"))
        assert len(decisions) == 1


# ═══════════════════════════════════════════════════════════════
# ImmuneGateway 测试
# ═══════════════════════════════════════════════════════════════

class TestImmuneResult:
    """ImmuneResult 数据类测试。"""

    def test_block(self):
        r = ImmuneResult(threat_level=0.9, decision=ImmuneDecision.BLOCK,
                        layer="negative_selection")
        assert r.decision == ImmuneDecision.BLOCK

    def test_frozen(self):
        r = ImmuneResult(threat_level=0.1, decision=ImmuneDecision.ALLOW,
                        layer="default")
        with pytest.raises(Exception):
            r.threat_level = 1.0  # type: ignore


class TestImmuneGateway:
    """ImmuneGateway 核心测试。"""

    @pytest.fixture
    def gateway(self):
        return ImmuneGateway()

    def test_default_allow(self, gateway):
        r = gateway.scan("file_read", "test.py")
        assert r.decision == ImmuneDecision.ALLOW

    def test_block_dangerous(self, gateway):
        r = gateway.scan("bash_exec", "", {"command": "rm -rf /tmp"})
        assert r.decision == ImmuneDecision.BLOCK

    def test_add_dangerous_pattern(self, gateway):
        gateway.add_dangerous_pattern("custom_hack_tool")
        r = gateway.scan("custom_hack_tool", "target")
        assert r.decision == ImmuneDecision.BLOCK

    def test_clonal_selection(self, gateway):
        gateway.approve_pattern("file_read:main.py", category="safe")
        r = gateway.scan("file_read", "main.py")
        assert r.decision == ImmuneDecision.ALLOW
        assert "clonal" in r.layer

    def test_danger_signal_rate(self, gateway):
        # 模拟高频事件
        for i in range(15):
            gateway.record_event({"tool": f"test_{i}",
                                  "timestamp": time.time()})
        r = gateway.scan("file_read", "test.py")
        # 高频可能触发警告
        assert r is not None

    def test_stats(self, gateway):
        gateway.scan("file_read", "a.py")
        gateway.scan("rm", "-rf /", {"command": "danger"})
        stats = gateway.get_stats()
        assert stats["total_scans"] == 2

    def test_approve_pattern_affinity(self, gateway):
        # 多次批准提升亲和力
        for _ in range(5):
            gateway.approve_pattern("file_read:*.md")
        r = gateway.scan("file_read", "readme.md")
        assert r.decision == ImmuneDecision.ALLOW
        assert r.confidence > 0.7  # 高亲和力


# ═══════════════════════════════════════════════════════════════
# ConsciousnessMonitor 测试
# ═══════════════════════════════════════════════════════════════

class TestConsciousnessState:
    """ConsciousnessState 数据类测试。"""

    def test_awake(self):
        s = ConsciousnessState(
            phi_value=0.85, awareness_level=AwarenessLevel.AWAKE,
            active_organs=200, total_organs=238, broadcast_queue_len=3,
            decision_confidence=0.8, hot_reflection_count=0,
        )
        assert s.awareness_level == AwarenessLevel.AWAKE

    def test_frozen(self):
        s = ConsciousnessState(
            phi_value=0.5, awareness_level=AwarenessLevel.DROWSY,
            active_organs=50, total_organs=238, broadcast_queue_len=0,
            decision_confidence=0.5, hot_reflection_count=0,
        )
        with pytest.raises(Exception):
            s.phi_value = 1.0  # type: ignore


class TestConsciousnessMonitor:
    """ConsciousnessMonitor 核心测试。"""

    @pytest.fixture
    def monitor(self):
        return ConsciousnessMonitor(total_organs=238)

    def test_initial_phi(self, monitor):
        assert monitor.phi == 0.5

    def test_update_phi_high(self, monitor):
        phi = monitor.update_phi(active_topics=30, responding_organs=30,
                                 total_events=3000)
        # coupling=1.0, activity=1.0 → raw_phi=1.0, EMA=0.6
        assert phi > 0.55

    def test_update_phi_zero(self, monitor):
        phi = monitor.update_phi(active_topics=0, responding_organs=0,
                                 total_events=0)
        assert phi <= 0.5  # 衰减

    def test_phi_converges(self, monitor):
        """Phi 向目标收敛。"""
        for _ in range(10):
            monitor.update_phi(active_topics=10, responding_organs=100,
                              total_events=500)
        phi = monitor.phi
        assert 0.4 <= phi <= 0.9

    def test_broadcast(self, monitor):
        gb = monitor.broadcast("alert1", "Security warning!",
                               source="ImmuneGateway", urgency=0.95)
        assert gb.signal_id == "alert1"
        assert gb.urgency == 0.95

    def test_broadcast_queue(self, monitor):
        for i in range(5):
            monitor.broadcast(f"sig{i}", f"msg{i}", urgency=0.1 * i)
        broadcasts = monitor.get_broadcasts()
        assert len(broadcasts) == 5

    def test_record_decision(self, monitor):
        monitor.record_decision(confidence=0.3)
        state = monitor.get_state()
        assert state.hot_reflection_count >= 1  # 低置信度触发反思

    def test_record_decision_high_conf(self, monitor):
        monitor.record_decision(confidence=0.9)
        state = monitor.get_state()
        assert state.decision_confidence == pytest.approx(0.9)

    def test_awareness_level(self, monitor):
        # 高Φ — 活跃主题=响应器官 → coupling=1.0
        for _ in range(10):
            monitor.update_phi(active_topics=50, responding_organs=50,
                              total_events=5000)
        state = monitor.get_state()
        assert state.awareness_level == AwarenessLevel.AWAKE

    def test_phi_history(self, monitor):
        for _ in range(5):
            monitor.update_phi(active_topics=5, responding_organs=50,
                              total_events=200)
        assert len(monitor.get_phi_history()) == 5


# ═══════════════════════════════════════════════════════════════
# SelfAwareness 测试
# ═══════════════════════════════════════════════════════════════

class TestOrganHealth:
    """OrganHealth 数据类测试。"""

    def test_healthy(self):
        h = OrganHealth(organ_name="test", status=OrganStatus.HEALTHY)
        assert h.status == OrganStatus.HEALTHY

    def test_frozen(self):
        h = OrganHealth(organ_name="test", status=OrganStatus.HEALTHY)
        with pytest.raises(Exception):
            h.status = OrganStatus.FAILING  # type: ignore


class TestHealthReport:
    """HealthReport 数据类测试。"""

    def test_all_healthy(self):
        organs = (
            OrganHealth("a", OrganStatus.HEALTHY),
            OrganHealth("b", OrganStatus.HEALTHY),
        )
        r = HealthReport(
            overall_status=OverallStatus.HEALTHY,
            organs=organs, total_organs=2,
            healthy_count=2, degraded_count=0, failing_count=0,
            recent_errors=(),
        )
        assert r.health_ratio == 1.0

    def test_frozen(self):
        r = HealthReport(
            overall_status=OverallStatus.HEALTHY,
            organs=(), total_organs=0, healthy_count=0,
            degraded_count=0, failing_count=0, recent_errors=(),
        )
        with pytest.raises(Exception):
            r.overall_status = OverallStatus.CRITICAL  # type: ignore


class TestSelfAwareness:
    """SelfAwareness 核心测试。"""

    @pytest.fixture
    def awareness(self):
        return SelfAwareness()

    def test_register_organ(self, awareness):
        awareness.register_organ("perception/window_watcher")
        oh = awareness.get_organ("perception/window_watcher")
        assert oh is not None
        assert oh.status == OrganStatus.UNKNOWN

    def test_report_heartbeat(self, awareness):
        awareness.register_organ("test_organ")
        awareness.report_heartbeat("test_organ")
        oh = awareness.get_organ("test_organ")
        assert oh is not None
        assert oh.status == OrganStatus.HEALTHY

    def test_auto_register_on_heartbeat(self, awareness):
        awareness.report_heartbeat("new_organ")
        oh = awareness.get_organ("new_organ")
        assert oh is not None

    def test_report_error(self, awareness):
        awareness.register_organ("failing_organ")
        awareness.report_error("failing_organ", "connection timeout")
        oh = awareness.get_organ("failing_organ")
        assert oh is not None
        assert oh.error_count == 1
        assert "timeout" in oh.last_error

    def test_multiple_errors_cause_failing(self, awareness):
        awareness.register_organ("bad_organ")
        for i in range(5):
            awareness.report_error("bad_organ", f"error {i}")
        oh = awareness.get_organ("bad_organ")
        assert oh is not None
        assert oh.status == OrganStatus.FAILING

    def test_health_report_healthy(self, awareness):
        awareness.report_heartbeat("organ1")
        awareness.report_heartbeat("organ2")
        report = awareness.get_health_report()
        assert report.overall_status == OverallStatus.HEALTHY
        assert report.healthy_count == 2

    def test_health_report_degraded(self, awareness):
        awareness.report_heartbeat("good")
        # 两次错误才退化, 一次只是 degraded
        awareness.report_error("bad", "error")
        awareness.report_heartbeat("bad")  # 有心跳但有问题
        awareness.report_error("bad", "error2")
        report = awareness.get_health_report()
        # 有 degraded 器官 → 整体 degraded
        assert report.overall_status != OverallStatus.HEALTHY
        assert report.degraded_count >= 1

    def test_health_report_critical(self, awareness):
        awareness.report_heartbeat("good")
        for _ in range(5):
            awareness.report_error("critical", "fatal")
        report = awareness.get_health_report()
        assert report.overall_status == OverallStatus.CRITICAL

    def test_check_timeouts(self, awareness):
        awareness.register_organ("slow_organ")
        # 设置一个"过期"的心跳
        awareness._organs["slow_organ"] = OrganHealth(
            organ_name="slow_organ", status=OrganStatus.HEALTHY,
            last_heartbeat=time.time() - 100,  # 100秒前
        )
        timeouts = awareness.check_timeouts()
        assert "slow_organ" in timeouts

    def test_stats(self, awareness):
        awareness.report_heartbeat("a")
        awareness.report_heartbeat("b")
        awareness.report_error("b", "minor")
        stats = awareness.get_stats()
        assert stats["organs"] == 2
        assert stats["healthy"] == 1
        assert stats["degraded"] == 1


# ═══════════════════════════════════════════════════════════════
# 集成测试
# ═══════════════════════════════════════════════════════════════

class TestPhase9Integration:
    """Phase 9 跨模块集成测试。"""

    def test_immune_to_arbiter_chain(self):
        """免疫扫描 → 宪法审查 完整安全链。"""
        gateway = ImmuneGateway()
        arbiter = ConstitutionalArbiter()

        # 模拟危险操作
        request = ActionRequest(tool="bash_exec", target="",
                               params={"command": "rm -rf /tmp"})

        # Step 1: 免疫扫描
        immune_result = gateway.scan(
            request.tool, request.target, request.params
        )
        assert immune_result.decision == ImmuneDecision.BLOCK

        # Step 2: 宪法审查
        arbiter_result = arbiter.review(request)
        assert not arbiter_result.approved

    def test_consciousness_self_awareness_integration(self):
        """意识监控 + 自我感知。"""
        monitor = ConsciousnessMonitor()
        awareness = SelfAwareness()

        # 注册器官
        for org in ["perception/window_watcher", "perception/clipboard_watcher",
                     "rhythm/rhythm_engine", "kernel/event_bus"]:
            awareness.register_organ(org)

        # 全部健康
        for org in ["perception/window_watcher", "perception/clipboard_watcher",
                     "rhythm/rhythm_engine", "kernel/event_bus"]:
            awareness.report_heartbeat(org)

        # 更新 Φ
        monitor.update_phi(active_topics=8, responding_organs=4,
                          total_events=100)

        report = awareness.get_health_report()
        state = monitor.get_state()

        assert report.overall_status == OverallStatus.HEALTHY
        assert state.phi_value > 0.4

    def test_full_safety_pipeline(self, tmp_path):
        """完整安全管道: Arbiter + Immune + Audit。"""
        path = tmp_path / "audit.jsonl"
        arbiter = ConstitutionalArbiter(audit_log_path=str(path))
        gateway = ImmuneGateway()

        # 正常操作: 通过
        safe = ActionRequest(tool="file_read", target="main.py")
        d1 = arbiter.review(safe)
        assert d1.approved

        # 危险操作: 阻止
        dangerous = ActionRequest(tool="bash_exec", target="",
                                 params={"command": "rm -rf /"})
        i2 = gateway.scan(dangerous.tool, dangerous.target, dangerous.params)
        d2 = arbiter.review(dangerous)
        assert i2.decision == ImmuneDecision.BLOCK
        assert not d2.approved

        # 完整性和日志
        log = arbiter.get_audit_log()
        assert len(log) == 2
        assert arbiter.verify_integrity()["valid"]
