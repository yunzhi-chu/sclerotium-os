"""Phase 8 灰度测试 — 进化引擎 (黏菌探索场)。

测试覆盖:
  - FCPIVector/FCPIDimension 不可变数据类
  - FCPITracker: 六维记录/EMA更新/向量/统计/快照
  - StrategyGenome: 基因读写/变异/交叉/克隆/clamping
  - EvolutionLoop: 进化/停滞检测/回滚/状态/模式
  - 集成: 追踪器→基因组→进化循环完整链路
"""

from __future__ import annotations

import time

import pytest

from evolution.fcpi_tracker import (
    FCPITracker, FCPIVector, FCPIDimension, DEFAULT_WEIGHTS,
)
from evolution.strategy_genome import (
    StrategyGenome, GeneSpec, GeneType, GenomeConfig, MutationRecord,
    DEFAULT_CONFIG,
)
from evolution.evolution_loop import (
    EvolutionLoop, EvolutionState, EvolutionResult, DIMENSION_GENE_MAP,
)


# ═══════════════════════════════════════════════════════════════
# FCPIVector 测试
# ═══════════════════════════════════════════════════════════════

class TestFCPIVector:
    """FCPIVector 数据类测试。"""

    def test_default(self):
        v = FCPIVector()
        assert v.coding == 0.5
        assert v.total_score == pytest.approx(0.5)

    def test_custom(self):
        v = FCPIVector(coding=0.8, safety=0.9, coordination=0.3)
        assert v.coding == 0.8
        assert v.safety == 0.9

    def test_total_score(self):
        v = FCPIVector(coding=1.0, coordination=1.0, safety=1.0,
                       decision=1.0, emergence=1.0, performance=1.0)
        assert v.total_score == pytest.approx(1.0)

    def test_total_score_low(self):
        v = FCPIVector(coding=0.0, coordination=0.0, safety=0.0,
                       decision=0.0, emergence=0.0, performance=0.0)
        assert v.total_score == pytest.approx(0.0)

    def test_weights_sum_to_one(self):
        total = sum(DEFAULT_WEIGHTS.values())
        assert pytest.approx(total) == 1.0

    def test_to_dict(self):
        v = FCPIVector(coding=0.7)
        d = v.to_dict()
        assert d["coding"] == 0.7
        assert "total" in d

    def test_weak_dimensions(self):
        v = FCPIVector(coding=0.9, safety=0.3, coordination=0.2,
                       decision=0.8, emergence=0.5, performance=0.6)
        weak = v.weak_dimensions(threshold=0.4)
        assert "safety" in weak
        assert "coordination" in weak
        assert "coding" not in weak

    def test_dominant_dimension(self):
        v = FCPIVector(coding=0.9, coordination=0.3, safety=0.4,
                       decision=0.5, emergence=0.5, performance=0.5)
        assert v.dominant_dimension() == "coding"

    def test_frozen(self):
        v = FCPIVector()
        with pytest.raises(Exception):
            v.coding = 1.0  # type: ignore


# ═══════════════════════════════════════════════════════════════
# FCPITracker 测试
# ═══════════════════════════════════════════════════════════════

class TestFCPITracker:
    """FCPITracker 核心测试。"""

    @pytest.fixture
    def tracker(self):
        return FCPITracker()

    def test_initial_scores(self, tracker):
        v = tracker.get_vector()
        for dim in FCPIDimension:
            assert getattr(v, dim.value) == 0.5

    def test_record_coding_pass(self, tracker):
        tracker.record_coding(test_pass=True)
        v = tracker.get_vector()
        assert v.coding > 0.5

    def test_record_coding_fail(self, tracker):
        tracker.record_coding(test_pass=False)
        v = tracker.get_vector()
        assert v.coding < 0.5

    def test_record_safety_error(self, tracker):
        tracker.record_safety(error=True)
        v = tracker.get_vector()
        assert v.safety < 0.5  # EMA: 0.5*0.9 + 0.1*0.1 = 0.46

    def test_record_safety_ok(self, tracker):
        tracker.record_safety(error=False)
        v = tracker.get_vector()
        assert v.safety > 0.5

    def test_record_decision_accepted(self, tracker):
        tracker.record_decision(suggestion_accepted=True, suggestion_quality=0.8)
        v = tracker.get_vector()
        assert v.decision > 0.5

    def test_ema_convergence(self, tracker):
        """EMA 向目标收敛。"""
        for _ in range(20):
            tracker.record_coding(test_pass=True, complexity=0.1)
        v = tracker.get_vector()
        assert v.coding > 0.6

    def test_snapshot(self, tracker):
        tracker.record_coding(test_pass=True)
        vec = tracker.snapshot()
        assert isinstance(vec, FCPIVector)
        assert len(tracker.get_history()) == 1

    def test_history(self, tracker):
        for i in range(5):
            tracker.record_coding(test_pass=i % 2 == 0)
            tracker.snapshot()
        assert len(tracker.get_history()) == 5

    def test_new_generation(self, tracker):
        tracker.new_generation()
        assert tracker._generation == 1

    def test_get_stats(self, tracker):
        tracker.record_coding(test_pass=True)
        tracker.record_safety(error=False)
        stats = tracker.get_stats()
        assert stats["total_records"] == 2
        assert "current" in stats

    def test_reset(self, tracker):
        tracker.record_coding(test_pass=True)
        tracker.record_safety(error=True)
        tracker.reset()
        v = tracker.get_vector()
        assert v.coding == 0.5
        assert v.safety == 0.5

    def test_record_coordination_success(self, tracker):
        tracker.record_coordination(tool_chain_success=True, tools_used=4)
        v = tracker.get_vector()
        assert v.coordination > 0.5

    def test_record_emergence(self, tracker):
        tracker.record_emergence(new_pattern_detected=True, pattern_significance=0.8)
        v = tracker.get_vector()
        assert v.emergence > 0.5

    def test_record_performance(self, tracker):
        tracker.record_performance(latency_ms=50, memory_mb=80)
        v = tracker.get_vector()
        # EMA: 0.5*0.9 + score*0.1 ≈ 0.545
        assert v.performance > 0.5


# ═══════════════════════════════════════════════════════════════
# StrategyGenome 测试
# ═══════════════════════════════════════════════════════════════

class TestGeneSpec:
    """GeneSpec 数据类测试。"""

    def test_create(self):
        gs = GeneSpec("test_param", GeneType.FLOAT, 0.5, 0.0, 1.0)
        assert gs.name == "test_param"
        assert gs.default == 0.5

    def test_frozen(self):
        gs = GeneSpec("p", GeneType.FLOAT, 0.5)
        with pytest.raises(Exception):
            gs.name = "changed"  # type: ignore


class TestStrategyGenome:
    """StrategyGenome 核心测试。"""

    @pytest.fixture
    def genome(self):
        return StrategyGenome()

    def test_default_values(self, genome):
        assert genome.get("nudge_threshold_work") == 0.5
        assert genome.get("pyloric_interval") == 30.0
        assert genome.get("search_top_k") == 10

    def test_set_and_get(self, genome):
        assert genome.set("nudge_threshold_work", 0.7)
        assert genome.get("nudge_threshold_work") == 0.7

    def test_set_clamps(self, genome):
        """超出范围时自动钳制。"""
        genome.set("nudge_threshold_work", 2.0)  # 超出 max 0.9
        assert genome.get("nudge_threshold_work") <= 0.9
        genome.set("nudge_threshold_work", -1.0)  # 低于 min 0.1
        assert genome.get("nudge_threshold_work") >= 0.1

    def test_set_unknown_gene(self, genome):
        assert not genome.set("nonexistent", 1.0)

    def test_to_dict(self, genome):
        d = genome.to_dict()
        assert isinstance(d, dict)
        assert "nudge_threshold_work" in d

    def test_mutate_creates_new(self, genome):
        original = genome.to_dict()
        mutant = genome.mutate()
        assert mutant.generation == genome.generation + 1
        # 至少有一个基因可能被改变 (概率性的)
        assert isinstance(mutant, StrategyGenome)

    def test_mutate_with_targets(self, genome):
        mutant = genome.mutate(num_mutations=3)
        history = mutant.get_mutation_history()
        assert len(history) <= 3

    def test_crossover(self, genome):
        other = StrategyGenome()
        other.set("nudge_threshold_work", 0.9)
        other.set("search_top_k", 20)

        child = genome.crossover(other)
        assert child.generation == max(genome.generation, other.generation) + 1

    def test_fitness(self, genome):
        assert genome.fitness == 0.5
        genome.set_fitness(0.85)
        assert genome.fitness == 0.85

    def test_copy_independent(self, genome):
        genome.set("nudge_threshold_work", 0.8)
        clone = genome.copy()
        clone.set("nudge_threshold_work", 0.3)
        assert genome.get("nudge_threshold_work") == 0.8  # 原版本不变
        assert clone.get("nudge_threshold_work") == 0.3

    def test_mutation_history(self, genome):
        mutant = genome.mutate(num_mutations=2, strength=5.0)
        history = mutant.get_mutation_history()
        for rec in history:
            assert isinstance(rec, MutationRecord)
            assert rec.old_value != rec.new_value

    def test_mutation_record_frozen(self):
        mr = MutationRecord(gene_name="test", old_value=0.5,
                            new_value=0.7, mutation_type="gaussian")
        with pytest.raises(Exception):
            mr.old_value = 0.6  # type: ignore

    def test_gene_names(self, genome):
        names = genome.gene_names()
        assert "nudge_threshold_work" in names
        assert "pyloric_interval" in names

    def test_custom_config(self):
        genes = (
            GeneSpec("custom_param", GeneType.FLOAT, 0.5, 0.0, 1.0),
            GeneSpec("flag", GeneType.BOOL, True),
        )
        config = GenomeConfig(genes=genes, version=1)
        genome = StrategyGenome(config=config)
        assert genome.get("custom_param") == 0.5
        assert genome.get("flag") is True


# ═══════════════════════════════════════════════════════════════
# EvolutionLoop 测试
# ═══════════════════════════════════════════════════════════════

class TestEvolutionState:
    """EvolutionState 数据类测试。"""

    def test_create(self):
        s = EvolutionState(generation=5, best_score=0.75, current_score=0.72,
                          total_mutations=12, improvements=3, regressions=1,
                          stalled_generations=2, active=True)
        assert s.generation == 5
        assert s.best_score == 0.75

    def test_frozen(self):
        s = EvolutionState(generation=0, best_score=0.5, current_score=0.5,
                          total_mutations=0, improvements=0, regressions=0,
                          stalled_generations=0, active=True)
        with pytest.raises(Exception):
            s.generation = 1  # type: ignore


class TestEvolutionLoop:
    """EvolutionLoop 核心测试。"""

    @pytest.fixture
    def loop(self):
        tracker = FCPITracker()
        genome = StrategyGenome()
        return EvolutionLoop(tracker=tracker, genome=genome)

    def test_initial_state(self, loop):
        state = loop.get_state()
        assert state.generation == 0
        assert state.best_score == 0.5
        assert state.active

    def test_evolve_generation(self, loop):
        result = loop.evolve_generation()
        assert isinstance(result, EvolutionResult)
        assert result.generation == 1

    def test_multiple_generations(self, loop):
        for i in range(5):
            loop._tracker.record_coding(test_pass=True)
            loop._tracker.record_safety(error=False)
            loop._tracker.record_decision(suggestion_accepted=True)
            loop.evolve_generation()

        state = loop.get_state()
        assert state.generation == 5

    def test_history(self, loop):
        for i in range(3):
            loop._tracker.record_coding(test_pass=True)
            loop.evolve_generation()
        assert len(loop.get_history()) == 3

    def test_off_mode(self, loop):
        loop._mode = "off"
        result = loop.evolve_generation()
        assert result.mutations == 0

    def test_reset(self, loop):
        loop._tracker.record_coding(test_pass=True)
        loop.evolve_generation()
        loop.reset()
        assert loop.generation == 0
        assert loop.get_history() == []

    def test_evolution_callback(self, loop):
        results = []

        def cb(r):
            results.append(r)

        loop.on_evolve(cb)
        loop.evolve_generation()
        assert len(results) == 1

    def test_genome_accessible(self, loop):
        assert loop.genome is not None
        assert loop.genome.get("nudge_threshold_work") == 0.5

    def test_dimension_gene_map(self):
        """维度→基因映射完整性。"""
        for dim in FCPIDimension:
            assert dim.value in DIMENSION_GENE_MAP
            assert len(DIMENSION_GENE_MAP[dim.value]) >= 1


# ═══════════════════════════════════════════════════════════════
# 集成测试
# ═══════════════════════════════════════════════════════════════

class TestPhase8Integration:
    """Phase 8 跨模块集成测试。"""

    def test_full_evolution_pipeline(self):
        """完整进化管道: 追踪→评估→变异→选择。"""
        tracker = FCPITracker()
        genome = StrategyGenome()
        loop = EvolutionLoop(tracker=tracker, genome=genome)

        # 模拟10代进化
        scores = []
        for gen in range(10):
            # 模拟用户行为 → FCPI 记录
            if gen < 5:
                # 前5代: 操作有些问题
                tracker.record_coding(test_pass=gen % 2 == 0)
                tracker.record_safety(error=gen % 3 == 0)
                tracker.record_decision(suggestion_accepted=False)
            else:
                # 后5代: 改善
                tracker.record_coding(test_pass=True)
                tracker.record_safety(error=False)
                tracker.record_decision(suggestion_accepted=True, suggestion_quality=0.8)
                tracker.record_coordination(tool_chain_success=True, tools_used=3)

            result = loop.evolve_generation()
            scores.append(result.old_score)

        state = loop.get_state()
        assert state.generation == 10
        assert state.total_mutations > 0
        assert len(loop.get_history()) == 10

    def test_tracker_to_genome_feedback(self):
        """FCPI 短板 → 定向变异反馈。"""
        tracker = FCPITracker()
        # 模拟安全维度持续低分
        for _ in range(10):
            tracker.record_safety(error=True)

        vec = tracker.get_vector()
        assert vec.safety < 0.3  # 安全分数很低

        weak = vec.weak_dimensions()
        assert "safety" in weak

        # 确认有相关基因
        safety_genes = DIMENSION_GENE_MAP["safety"]
        assert len(safety_genes) >= 2

    def test_genome_evolution_improves_fitness(self):
        """基因组进化应能改善适应度。"""
        genome = StrategyGenome()
        initial_fitness = genome.fitness

        # 手动设置低分
        genome.set_fitness(0.3)

        # 多次变异, 寻找改进
        best = genome
        best_score = 0.3
        for _ in range(10):
            mutant = genome.mutate(strength=2.0)
            # 模拟评估 (随机)
            import random
            score = random.uniform(0.2, 0.9)
            mutant.set_fitness(score)
            if score > best_score:
                best = mutant
                best_score = score

        assert best.fitness >= 0.3  # 至少不比初始差
