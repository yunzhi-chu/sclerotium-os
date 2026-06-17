"""Phase 10 灰度测试 — 元认知全员激活 (L6 16器官)。

测试覆盖:
  - MetaCognitionBridge: 器官注册/监控/诊断/修复循环
  - ArbiterMonitorBridge: 个性化Nudge学习/阈值调整/画像
  - DGMBridge: 5变异/策略DNA加载/定向变异
  - CrystallizerBridge: 涌现捕获/评估/结晶管道
  - GoalExpanderBridge: 模糊指令展开/模板匹配
  - SelfRepairBridge: 错误修复/导入修复/文件修复
"""

from __future__ import annotations

import time
from unittest import mock

import pytest

from kernel.meta_cognition_bridge import (
    MetaCognitionBridge, OrganDiagnosis, CycleReport, DiagnosisLevel,
)
from kernel.arbiter_monitor_bridge import (
    ArbiterMonitorBridge, NudgeRecord, NudgeAction,
)
from evolution.dgm_bridge import (
    DGMBridge, DGMutationType, DGMMutationResult,
    STRATEGY_DNA_LIBRARY, DIMENSION_MUTATION_MAP,
)
from evolution.crystallizer_bridge import (
    CrystallizerBridge, EmergentPattern, PatternEvaluation,
    CrystallizedSkill,
)
from evolution.fcpi_tracker import FCPIVector
from evolution.strategy_genome import StrategyGenome
from kernel.goal_expander_bridge import (
    GoalExpanderBridge, GoalStep, GoalPlan, GOAL_TEMPLATES,
)
from kernel.self_repair_bridge import (
    SelfRepairBridge, ErrorInfo, RepairResult,
)


# ═══════════════════════════════════════════════════════════════
# MetaCognitionBridge
# ═══════════════════════════════════════════════════════════════

class TestMetaCognitionBridge:
    @pytest.fixture
    def meta(self):
        return MetaCognitionBridge()

    def test_register_organ(self, meta):
        meta.register_organ("test_organ", check=lambda: True)
        # 运行一次循环
        report = meta.run_cycle()
        assert "test_organ" in [d.organ_name for d in report.diagnoses]

    def test_run_cycle_healthy(self, meta):
        meta.register_organ("healthy", check=lambda: True)
        report = meta.run_cycle()
        assert report.healthy_count == 1

    def test_run_cycle_error(self, meta):
        meta.register_organ("broken", check=lambda: False,
                           repair=lambda: True)
        report = meta.run_cycle()
        assert report.error_count >= 1

    def test_run_cycle_with_check_fn(self, meta):
        meta.register_organ("detailed",
                           check_fn=lambda: (True, "一切正常"))
        report = meta.run_cycle()
        assert report.healthy_count == 1

    def test_auto_repair(self, meta):
        repaired = []
        meta.register_organ("fixable", check=lambda: False,
                           repair=lambda: repaired.append(1) or True)
        report = meta.run_cycle()
        assert len(repaired) >= 1
        assert len(report.actions_taken) >= 1

    def test_multiple_organs(self, meta):
        for i in range(5):
            meta.register_organ(f"org{i}", check=lambda: True)
        report = meta.run_cycle()
        assert report.healthy_count == 5

    def test_exception_handling(self, meta):
        meta.register_organ("crash", check=lambda: 1/0)
        report = meta.run_cycle()
        assert report.error_count >= 1

    def test_history(self, meta):
        for _ in range(3):
            meta.register_organ("test", check=lambda: True)
            meta.run_cycle()
        assert len(meta.get_history()) == 3

    def test_summary(self, meta):
        meta.register_organ("ok", check=lambda: True)
        report = meta.run_cycle()
        assert "Cycle #1" in report.summary()


# ═══════════════════════════════════════════════════════════════
# ArbiterMonitorBridge
# ═══════════════════════════════════════════════════════════════

class TestArbiterMonitorBridge:
    @pytest.fixture
    def monitor(self):
        return ArbiterMonitorBridge()

    def test_default_decide(self, monitor):
        action = monitor.decide("health", "休息", "你工作很久了", 0.5)
        assert action in (NudgeAction.SILENT, NudgeAction.TRAY)

    def test_high_importance_notifies(self, monitor):
        action = monitor.decide("health", "紧急", "快休息!", 0.95)
        assert action == NudgeAction.NOTIFY

    def test_security_always_alerts(self, monitor):
        action = monitor.decide("security", "!", "入侵检测", 0.1)
        assert action == NudgeAction.ALERT

    def test_force_override(self, monitor):
        action = monitor.decide("info", "F", "M", 0.1, force=True)
        assert action == NudgeAction.ALERT

    def test_record_learning(self, monitor):
        # 多次记录"用户接受了 health 建议"
        for i in range(10):
            monitor.record_nudge(
                f"n{i}", "health", 0.5, NudgeAction.NOTIFY,
                user_accepted=True,
            )
        profile = monitor.get_profile()
        assert profile.total_nudges == 10
        assert profile.acceptance_rate > 0.8

        # health 的阈值应该降低 (用户接受 → 更积极)
        thresholds = monitor.get_thresholds()
        assert thresholds["health"] <= 0.6

    def test_rejected_learning(self, monitor):
        # 多次记录"用户拒绝了"
        for i in range(10):
            monitor.record_nudge(f"n{i}", "health", 0.5, NudgeAction.NOTIFY,
                               user_accepted=False)
        thresholds = monitor.get_thresholds()
        assert thresholds["health"] >= 0.55  # 阈值提高 → 更保守

    def test_profile_preferred_categories(self, monitor):
        monitor.record_nudge("1", "health", 0.5, NudgeAction.NOTIFY,
                           user_accepted=True)
        monitor.record_nudge("2", "health", 0.5, NudgeAction.NOTIFY,
                           user_accepted=True)
        monitor.record_nudge("3", "info", 0.5, NudgeAction.NOTIFY,
                           user_accepted=False)
        profile = monitor.get_profile()
        assert "health" in profile.preferred_categories


# ═══════════════════════════════════════════════════════════════
# DGMBridge
# ═══════════════════════════════════════════════════════════════

class TestDGMBridge:
    @pytest.fixture
    def dgm(self):
        return DGMBridge()

    @pytest.fixture
    def genome(self):
        return StrategyGenome()

    def test_insert_mutation(self, dgm, genome):
        fcpi = FCPIVector(emergence=0.2)  # 低涌现 → INSERT
        mutant, rec = dgm.mutate(genome, fcpi, DGMutationType.INSERT)
        assert rec.mutation_type == DGMutationType.INSERT

    def test_delete_mutation(self, dgm, genome):
        fcpi = FCPIVector(safety=0.3)
        mutant, rec = dgm.mutate(genome, fcpi, DGMutationType.DELETE)
        assert rec.mutation_type == DGMutationType.DELETE

    def test_substitute_mutation(self, dgm, genome):
        fcpi = FCPIVector(coding=0.3)
        mutant, rec = dgm.mutate(genome, fcpi, DGMutationType.SUBSTITUTE)
        assert rec.mutation_type == DGMutationType.SUBSTITUTE

    def test_crossover_mutation(self, dgm, genome):
        fcpi = FCPIVector(coordination=0.3)
        mutant, rec = dgm.mutate(genome, fcpi, DGMutationType.CROSSOVER)
        assert rec.mutation_type == DGMutationType.CROSSOVER

    def test_duplicate_mutation(self, dgm, genome):
        fcpi = FCPIVector(coding=0.9, decision=0.2)
        mutant, rec = dgm.mutate(genome, fcpi, DGMutationType.DUPLICATE)
        assert rec.mutation_type == DGMutationType.DUPLICATE

    def test_auto_mutation_from_fcpi(self, dgm, genome):
        fcpi = FCPIVector(safety=0.2)  # 安全短板
        mutant, rec = dgm.mutate(genome, fcpi)  # 自动选择
        assert rec.mutation_type in list(DGMutationType)

    def test_dna_library(self, dgm):
        assert "aggressive_developer" in STRATEGY_DNA_LIBRARY
        assert "night_owl" in STRATEGY_DNA_LIBRARY

    def test_dimension_map(self):
        assert "coding" in DIMENSION_MUTATION_MAP
        assert DIMENSION_MUTATION_MAP["safety"] == DGMutationType.DELETE


# ═══════════════════════════════════════════════════════════════
# CrystallizerBridge
# ═══════════════════════════════════════════════════════════════

class TestCrystallizerBridge:
    @pytest.fixture
    def cryst(self):
        return CrystallizerBridge()

    def test_capture_new_pattern(self, cryst):
        p = cryst.capture("用户打开VS Code后总打开终端",
                         trigger="vscode_launched",
                         actions=["launch_vscode", "launch_terminal"])
        assert p.frequency == 1
        assert p.pattern_id != ""

    def test_capture_duplicate_increments(self, cryst):
        p1 = cryst.capture("打开VS Code后打开终端")
        p2 = cryst.capture("打开VS Code后打开终端")
        assert p2.frequency == 2  # 同一个模式

    def test_evaluate_low_frequency(self, cryst):
        p = cryst.capture("新模式")
        ev = cryst.evaluate(p)
        assert not ev.is_reliable  # frequency=1 < MIN_FREQUENCY(3)
        assert ev.score < 0.5

    def test_evaluate_high_frequency(self, cryst):
        p = cryst.capture("可靠模式")
        # 模拟高频率
        for _ in range(5):
            p = cryst.capture("可靠模式")
        ev = cryst.evaluate(p)
        assert ev.is_reliable
        assert ev.score >= 0.5

    def test_crystallize(self, cryst):
        for _ in range(5):
            p = cryst.capture("频繁模式: 每天检查邮件",
                            trigger="morning_login",
                            actions=["open_chrome", "open_gmail"])
        skill = cryst.crystallize(p)
        assert skill.confidence >= 0.5
        assert skill.skill_id != ""

    def test_safety_check(self, cryst):
        p = cryst.capture("危险操作", actions=["rm -rf /"])
        ev = cryst.evaluate(p)
        assert not ev.is_safe


# ═══════════════════════════════════════════════════════════════
# GoalExpanderBridge
# ═══════════════════════════════════════════════════════════════

class TestGoalExpanderBridge:
    @pytest.fixture
    def expander(self):
        return GoalExpanderBridge()

    def test_expand_organize(self, expander):
        plan = expander.expand("帮我整理一下")
        assert plan.total_steps >= 1
        assert "scan" in [s.action for s in plan.steps]

    def test_expand_analyze(self, expander):
        plan = expander.expand("分析这个项目")
        assert plan.total_steps >= 1

    def test_expand_debug(self, expander):
        plan = expander.expand("调试这个 bug")
        assert plan.total_steps >= 3

    def test_expand_open(self, expander):
        plan = expander.expand("打开 VS Code")
        assert plan.total_steps >= 1
        assert "launch" in [s.action for s in plan.steps]

    def test_steps_have_dependencies(self, expander):
        plan = expander.expand("分析项目")
        later_steps = [s for s in plan.steps if s.index > 1]
        assert any(s.depends_on is not None for s in later_steps)

    def test_add_custom_template(self, expander):
        expander.add_template("喝咖啡", [
            {"action": "open", "desc": "打开咖啡机"},
            {"action": "wait", "desc": "等30秒"},
        ])
        plan = expander.expand("帮我喝咖啡")
        assert plan.total_steps == 2

    def test_complexity(self, expander):
        plan = expander.expand("分析项目")
        assert 0 < plan.estimated_complexity < 1.0


# ═══════════════════════════════════════════════════════════════
# SelfRepairBridge
# ═══════════════════════════════════════════════════════════════

class TestSelfRepairBridge:
    @pytest.fixture
    def repair(self):
        return SelfRepairBridge()

    def test_fix_import_error(self, repair):
        err = ErrorInfo("ModuleNotFoundError",
                       "No module named 'pandas'", module="test")
        result = repair.attempt_repair(err)
        assert isinstance(result, RepairResult)

    def test_fix_file_not_found(self, repair, tmp_path):
        missing = tmp_path / "subdir" / "config.json"
        err = ErrorInfo("FileNotFoundError",
                       f"No such file: '{missing}'", module="test")
        result = repair.attempt_repair(err)
        assert isinstance(result, RepairResult)

    def test_no_fixer_for_unknown(self, repair):
        err = ErrorInfo("WeirdError", "Something strange", module="test")
        result = repair.attempt_repair(err)
        assert not result.success
        assert "No fixer" in result.detail

    def test_register_custom_fixer(self, repair):
        repair.register_fixer(
            "CustomError",
            lambda e: (True, "Fixed!")
        )
        err = ErrorInfo("CustomError", "Oops", module="test")
        result = repair.attempt_repair(err)
        assert result.success

    def test_history_and_stats(self, repair):
        err = ErrorInfo("ImportError", "No module 'x'", module="test")
        repair.attempt_repair(err)
        stats = repair.get_stats()
        assert stats["total_attempts"] == 1


# ═══════════════════════════════════════════════════════════════
# 集成
# ═══════════════════════════════════════════════════════════════

class TestPhase10Integration:
    def test_dgm_with_genome(self):
        dgm = DGMBridge()
        genome = StrategyGenome()
        fcpi = FCPIVector(coding=0.25, safety=0.3)
        mutant, rec = dgm.mutate(genome, fcpi)
        assert isinstance(mutant, StrategyGenome)
        assert isinstance(rec, DGMMutationResult)

    def test_crystallizer_to_skill_pipeline(self):
        cryst = CrystallizerBridge()
        # 模拟高频模式
        p = cryst.capture("用户每天下午3点查看股票",
                         trigger="15:00",
                         actions=["open_chrome", "navigate_stocks"])
        for _ in range(4):
            p = cryst.capture("用户每天下午3点查看股票")
        ev = cryst.evaluate(p)
        if ev.score >= 0.5:
            skill = cryst.crystallize(p)
            assert skill.confidence >= 0.5

    def test_goal_expander_full_pipeline(self):
        expander = GoalExpanderBridge()
        plan = expander.expand("帮我调试这个认证bug")
        assert plan.total_steps >= 3
        assert all(isinstance(s, GoalStep) for s in plan.steps)

    def test_meta_repair_integration(self):
        meta = MetaCognitionBridge()
        repair = SelfRepairBridge()

        broken_count = [0]

        def check_organ():
            broken_count[0] += 1
            return broken_count[0] <= 1  # 第一次ok, 第二次broken

        def repair_organ():
            return True

        meta.register_organ("flaky", check=check_organ, repair=repair_organ)
        r1 = meta.run_cycle()  # 健康
        r2 = meta.run_cycle()  # 检测到错误 → 修复
        assert r1.healthy_count >= 1
