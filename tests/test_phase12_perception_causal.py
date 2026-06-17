"""Phase 12 灰度测试 — 液态感知·辩论·因果 (L1-L4)。"""

from __future__ import annotations

import time
import pytest

from perception.liquid_perceptor import LiquidPerceptor, LiquidState
from kernel.debate_engine import DebateEngine, DebateVerdict, Argument
from kernel.causal_debug_bridge import CausalDebugBridge, CausalDiagnosis, RootCause
from kernel.neutrosophic_validator import NeutrosophicValidator, NeutrosophicResult
from rhythm.ltc_rhythm import LTCRhythm, LTCRhythmState


# ═══════════════════════════════════════════════════════════════
# LiquidPerceptor
# ═══════════════════════════════════════════════════════════════

class TestLiquidPerceptor:
    @pytest.fixture
    def lp(self):
        return LiquidPerceptor(tau=10.0)

    def test_initial_state(self, lp):
        s = lp.get_state()
        assert s.activity_level > 0

    def test_update_changes_state(self, lp):
        old = lp.get_state().activity_level
        lp.update("code.exe", 0.9)
        new = lp.get_state().activity_level
        assert new != old

    def test_multiple_updates(self, lp):
        lp.update("code.exe", 0.8)
        lp.update("chrome.exe", 0.4)
        lp.update("terminal.exe", 0.6)
        s = lp.get_state()
        assert s.current_app == "terminal.exe"

    def test_focus_depth(self, lp):
        lp.update("code.exe", 0.8)
        time.sleep(0.05)
        s = lp.get_state()
        assert s.focus_depth >= 0

    def test_app_usage(self, lp):
        lp.update("code.exe", 0.8)
        lp.update("chrome.exe", 0.4)
        lp.update("code.exe", 0.8)
        usage = lp.get_app_usage()
        assert "code.exe" in usage

    def test_idle_probability(self, lp):
        lp.update("idle", 0.1)
        s = lp.get_state()
        assert s.idle_probability > 0

    def test_high_activity(self, lp):
        lp.update("code.exe", 0.95)
        time.sleep(0.02)  # 让 ODE 有时间响应
        lp.update("code.exe", 0.95)  # 再次确认高活跃
        s = lp.get_state()
        assert s.activity_level > 0.5


# ═══════════════════════════════════════════════════════════════
# DebateEngine
# ═══════════════════════════════════════════════════════════════

class TestDebateEngine:
    @pytest.fixture
    def engine(self):
        return DebateEngine(agents=6, threshold=0.67)

    def test_add_argument(self, engine):
        engine.add_argument("pro", "应该提醒用户休息", 0.8)
        assert len(engine._pro_args) == 1

    def test_debate_with_evidence(self, engine):
        engine.add_argument("pro", "用户连续工作3小时", 0.9)
        engine.add_argument("pro", "系统检测到疲劳信号", 0.7)
        engine.add_argument("con", "用户设置了免打扰模式", 0.6)
        verdict = engine.debate()
        assert isinstance(verdict, DebateVerdict)
        assert verdict.total_agents == 6

    def test_strong_pro_passes(self, engine):
        for i in range(5):
            engine.add_argument("pro", f"支持理由{i}", 0.9)
        verdict = engine.debate()
        assert verdict.pro_votes >= verdict.con_votes

    def test_empty_debate(self, engine):
        verdict = engine.debate()
        assert isinstance(verdict, DebateVerdict)

    def test_consensus_ratio(self, engine):
        engine.add_argument("pro", "强证据", 0.95)
        verdict = engine.debate()
        assert 0 <= verdict.consensus_ratio <= 1.0

    def test_history(self, engine):
        for _ in range(3):
            engine.add_argument("pro", "test", 0.5)
            engine.debate()
        assert len(engine.get_history()) == 3


# ═══════════════════════════════════════════════════════════════
# CausalDebugBridge
# ═══════════════════════════════════════════════════════════════

class TestCausalDebugBridge:
    @pytest.fixture
    def causal(self):
        return CausalDebugBridge()

    def test_add_dependency(self, causal):
        causal.add_dependency("rhythm_engine", "nudge_engine", 0.8)
        graph = causal.get_dependency_graph()
        assert "rhythm_engine" in graph.get("nudge_engine", [])

    def test_diagnose(self, causal):
        causal.add_dependency("rhythm_engine", "nudge_engine", 0.8,
                             "节律异常导致通知延迟")
        causal.add_dependency("user_model", "nudge_engine", 0.6)
        causal.update_status("rhythm_engine", "degraded")
        diagnosis = causal.diagnose("nudge_engine", "通知延迟")
        assert diagnosis.total_candidates >= 1

    def test_diagnose_unknown(self, causal):
        diagnosis = causal.diagnose("unknown_organ")
        assert diagnosis.total_candidates == 0

    def test_root_cause_ranking(self, causal):
        causal.add_dependency("root", "symptom", 0.9)
        causal.add_dependency("minor", "symptom", 0.3)
        causal.update_status("root", "failing")
        causal.update_status("minor", "healthy")
        diagnosis = causal.diagnose("symptom")
        if diagnosis.root_causes:
            assert diagnosis.root_causes[0].organ == "root"

    def test_depth_limit(self, causal):
        # 创建长链
        for i in range(10):
            causal.add_dependency(f"organ_{i}", f"organ_{i+1}")
        diagnosis = causal.diagnose("organ_9")
        assert len(diagnosis.root_causes) <= 5


# ═══════════════════════════════════════════════════════════════
# NeutrosophicValidator
# ═══════════════════════════════════════════════════════════════

class TestNeutrosophicValidator:
    @pytest.fixture
    def validator(self):
        return NeutrosophicValidator()

    def test_validate_true(self, validator):
        result = validator.validate(
            "用户喜欢Python",
            evidence_for=["10个项目中9个用Python", "最近100次提交都是.py"],
            evidence_against=["用户提及过想学Rust"],
        )
        assert result.verdict in ("true", "uncertain")

    def test_validate_empty(self, validator):
        result = validator.validate("无证据声明")
        assert result.verdict == "uncertain"

    def test_validate_balanced(self, validator):
        result = validator.validate(
            "用户在迁移到TypeScript",
            evidence_for=["新增5个.ts文件", "安装了ts相关依赖"],
            evidence_against=["核心模块仍是.py", "未删除任何.py文件"],
        )
        assert result.T >= 0 or result.F >= 0  # 三段值有效

    def test_tfi_constraint(self, validator):
        result = validator.validate("test", ["证据1"], ["反证1"])
        # T + F + I 应为合理范围
        assert result.T + result.F + result.I <= 3.0

    def test_history(self, validator):
        validator.validate("A", ["支持"])
        validator.validate("B", ["支持"])
        assert len(validator.get_history()) == 2


# ═══════════════════════════════════════════════════════════════
# LTCRhythm
# ═══════════════════════════════════════════════════════════════

class TestLTCRhythm:
    @pytest.fixture
    def ltc(self):
        return LTCRhythm()

    def test_default_interval(self, ltc):
        assert ltc.get_pyloric_interval() == 30.0
        assert ltc.get_gastric_interval() == 3600.0

    def test_high_activity_shortens(self, ltc):
        for _ in range(10):
            ltc.update_activity(1.0)
        assert ltc.get_pyloric_interval() < 30.0  # EMA 收敛后 < 30

    def test_low_activity_lengthens(self, ltc):
        for _ in range(10):
            ltc.update_activity(0.0)
        assert ltc.get_pyloric_interval() > 80.0  # EMA 收敛后 > 80

    def test_mode_sleep(self, ltc):
        ltc.update_activity(0.5)
        ltc.set_mode("sleep")
        assert ltc.get_pyloric_interval() > 60.0

    def test_ema_smoothing(self, ltc):
        ltc.update_activity(1.0)
        ltc.update_activity(0.0)
        # EMA 平滑: 不会立即降到最低
        assert ltc.activity > 0.3

    def test_state(self, ltc):
        s = ltc.get_state()
        assert isinstance(s, LTCRhythmState)


# ═══════════════════════════════════════════════════════════════
# 集成
# ═══════════════════════════════════════════════════════════════

class TestPhase12Integration:
    def test_debate_to_validator_pipeline(self):
        """辩论→中智验证 完整管道"""
        debate = DebateEngine()
        validator = NeutrosophicValidator()

        # 模拟 Insight 生成
        claim = "用户的Python技能水平很高"
        debate.add_argument("pro", "用户写了10000行Python代码", 0.9)
        debate.add_argument("pro", "代码质量评分A", 0.8)
        debate.add_argument("con", "用户最近在学TypeScript", 0.5)
        verdict = debate.debate()

        result = validator.validate(
            claim,
            evidence_for=["10000行Python代码", "代码质量A"],
            evidence_against=["最近在学TypeScript"],
        )
        assert result is not None

    def test_causal_to_ltc_pipeline(self):
        """因果诊断→节律调整"""
        causal = CausalDebugBridge()
        ltc = LTCRhythm()

        causal.add_dependency("activity_tracker", "rhythm_engine", 0.9)
        causal.add_dependency("window_watcher", "activity_tracker", 0.7)
        causal.update_status("window_watcher", "failing")
        diagnosis = causal.diagnose("rhythm_engine", "节律异常")

        if diagnosis.root_causes:
            ltc.update_activity(0.2)  # 降低活动频率
            assert ltc.get_pyloric_interval() > 50.0
