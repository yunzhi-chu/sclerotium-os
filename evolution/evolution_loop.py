"""Evolution Loop — 评估→变异→选择闭环。

生命体的"新陈代谢" — 持续用真实用户行为数据评估当前策略,
变异低分参数, 保留优胜策略。

进化闭环:
  1. 快照当前 FCPI 向量 (评估)
  2. 识别短板维度
  3. 变异相关基因 (DGM 定向变异)
  4. 产生候选基因组
  5. 等待下一轮评估
  6. 比较新旧适应度 → 保留 / 淘汰

使用方式:
    tracker = FCPITracker()
    genome = StrategyGenome()
    loop = EvolutionLoop(tracker=tracker, genome=genome)

    # 每次胃磨节律触发:
    loop.evolve_generation()

    # 查看进化状态:
    state = loop.get_state()
    print(f"第 {state.generation} 代, 最佳 FCPI: {state.best_score}")

参考:
  - MiroFish evolution_generation_manager.py — 进化状态机
  - MiroFish fitness_extractor.py — FCPI→DGM 失败信号
  - fungal-cortex l6/darwinian_godel_machine.py — 基因组操作
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from evolution.fcpi_tracker import FCPITracker, FCPIVector, FCPIDimension
from evolution.strategy_genome import StrategyGenome

logger = logging.getLogger("sclerotium.evolution")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class EvolutionState:
    """进化状态快照 (不可变)。"""
    generation: int
    best_score: float
    current_score: float
    total_mutations: int
    improvements: int          # 改善次数
    regressions: int           # 退化次数
    stalled_generations: int   # 停滞代数
    active: bool
    started_at: float = 0.0
    last_evolution: float = field(default_factory=time.time)


@dataclass(frozen=True)
class EvolutionResult:
    """单代进化结果 (不可变)。"""
    generation: int
    old_score: float
    new_score: float
    improved: bool
    mutations: int
    candidate_survived: bool    # 候选基因组是否保留
    weak_dimensions: tuple[str, ...] = ()
    timestamp: float = field(default_factory=time.time)


# 维度 → 相关基因映射
DIMENSION_GENE_MAP: dict[str, list[str]] = {
    "coding": ["nudge_threshold_work", "search_top_k"],
    "coordination": ["nudge_cooldown_work", "pyloric_interval"],
    "safety": ["nudge_threshold_sleep", "nudge_threshold_game", "notify_max_per_hour"],
    "decision": ["ema_learning_rate", "insight_min_confidence", "nudge_threshold_work"],
    "emergence": ["consolidation_threshold_episodic", "insight_min_confidence"],
    "performance": ["pyloric_interval", "gastric_interval", "search_top_k"],
}


# ═══════════════════════════════════════════════════════════════
# EvolutionLoop
# ═══════════════════════════════════════════════════════════════

class EvolutionLoop:
    """评估→变异→选择进化闭环。

    使用方式:
        tracker = FCPITracker()
        genome = StrategyGenome()
        loop = EvolutionLoop(tracker=tracker, genome=genome, mode="auto")

        # 每次胃磨触发:
        result = loop.evolve_generation()
        print(f"Generation {result.generation}: "
              f"{'improved' if result.improved else 'no change'}")

        # 获取进化状态
        state = loop.get_state()
    """

    def __init__(
        self,
        genome: Any = None,           # FullBodyGenome (8D)
        mode: str = "auto",
        min_generations_between: int = 3,
        stagnation_threshold: int = 5,
        improvement_threshold: float = 0.001,  # 8D fitness changes are small
    ) -> None:
        self._genome = genome
        self._mode = mode
        self._min_generations_between = min_generations_between
        self._stagnation_threshold = stagnation_threshold
        self._improvement_threshold = improvement_threshold

        # 进化状态
        self._generation: int = 0
        self._best_score: float = 0.5
        self._best_genome: StrategyGenome = self._genome.copy()
        self._history: list[EvolutionResult] = []
        self._improvements: int = 0
        self._regressions: int = 0
        self._stalled: int = 0
        self._total_mutations: int = 0
        self._active: bool = True
        self._started_at: float = time.time()
        self._last_evolution: float = 0.0

        # 快照计数 (手动进化用)
        self._snapshots_since_last: int = 0

        # 回调
        self._on_evolve: list[Callable[[EvolutionResult], None]] = []

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def evolve_generation(self) -> EvolutionResult:
        """执行一代8D进化 (基于FullBodyGenome)。

        流程:
          1. 获取当前8D基因组适应度
          2. 识别弱势维度
          3. 定向变异
          4. 候选 vs 当前 → 优胜劣汰
        """
        if self._mode == "off" or not self._active:
            return EvolutionResult(
                generation=self._generation,
                old_score=0.0, new_score=0.0,
                improved=False, mutations=0,
                candidate_survived=False,
            )

        # Use FullBodyGenome's 8D fitness (not just 6D FCPI)
        old_score = self._genome.fitness

        # Identify weak dimensions from the genome
        weak_dims = self._get_weak_8d_dimensions()

        mutation_strength = 1.0
        if self._stalled >= self._stagnation_threshold:
            mutation_strength = 2.0
            logger.debug("Stagnation — boosted mutation")

        # Create mutated candidate
        candidate = self._genome.mutate(
            num_mutations=max(3, len(weak_dims)),
            strength=mutation_strength,
        )
        new_score = candidate.fitness

        mutations = 3
        self._total_mutations += 3

        # 8D fitness comparison: candidate vs current
        improved = new_score > old_score + self._improvement_threshold
        if improved:
            self._best_score = new_score
            self._best_genome = candidate.copy()
            self._genome = candidate
            self._improvements += 1
            self._stalled = 0
        elif new_score < old_score - self._improvement_threshold:
            self._stalled += 1
            self._regressions += 1
        else:
            self._stalled += 1
            new_score = old_score

        # 持久化: 每代进化后保存检查点 (重启不丢)
        try:
            if hasattr(self._genome, 'save_checkpoint'):
                self._genome.save_checkpoint()
        except Exception as e:
            logger.debug("Checkpoint save skipped: %s", e)

        self._generation += 1
        self._last_evolution = time.time()

        result = EvolutionResult(
            generation=self._generation,
            old_score=old_score,
            new_score=new_score,
            improved=improved,
            mutations=mutations,
            candidate_survived=candidate.fitness >= old_score,
            weak_dimensions=tuple(weak_dims),
        )

        self._history.append(result)

        # 通知回调
        for cb in self._on_evolve:
            try:
                cb(result)
            except Exception:
                pass

        return result

    def _get_weak_8d_dimensions(self) -> list[str]:
        """Identify weak 8D genome dimensions below threshold."""
        weak = []
        dims = {
            "tools": sum(self._genome._tool_genes.values()) / max(len(self._genome._tool_genes), 1),
            "prompts": sum(self._genome._prompt_genes.values()) / max(len(self._genome._prompt_genes), 1),
            "personalities": sum(self._genome._personality_genes.values()) / max(len(self._genome._personality_genes), 1),
            "memories": sum(self._genome._memory_genes.values()) / max(len(self._genome._memory_genes), 1),
            "providers": sum(self._genome._provider_genes.values()) / max(len(self._genome._provider_genes), 1),
            "skills": sum(self._genome._skill_genes.values()) / max(len(self._genome._skill_genes), 1),
            "organs": sum(self._genome._organ_genes.values()) / max(len(self._genome._organ_genes), 1),
            "arbiters": sum(self._genome._arbiter_genes.values()) / max(len(self._genome._arbiter_genes), 1),
        }
        for dim, avg in dims.items():
            if avg < 0.35:
                weak.append(dim)
        return weak

    def get_state(self) -> EvolutionState:
        """获取当前8D进化状态。"""
        return EvolutionState(
            generation=self._generation,
            best_score=self._best_score,
            current_score=self._genome.fitness if self._genome else 0.5,
            total_mutations=self._total_mutations,
            improvements=self._improvements,
            regressions=self._regressions,
            stalled_generations=self._stalled,
            active=self._active,
            started_at=self._started_at,
            last_evolution=self._last_evolution,
        )

    def get_history(self, limit: int = 20) -> list[EvolutionResult]:
        """获取进化历史。"""
        return self._history[-limit:]

    def reset(self) -> None:
        """重置进化状态。"""
        self._generation = 0
        self._best_score = 0.5
        self._best_genome = self._genome.copy()
        self._history.clear()
        self._improvements = 0
        self._regressions = 0
        self._stalled = 0
        self._total_mutations = 0
        self._started_at = time.time()

    def on_evolve(self, callback: Callable[[EvolutionResult], None]) -> None:
        """注册进化完成回调。"""
        self._on_evolve.append(callback)

    # ═══════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def best_score(self) -> float:
        return self._best_score

    @property
    def genome(self) -> StrategyGenome:
        return self._genome

    @property
    def mode(self) -> str:
        return self._mode

    # ═══════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════

    def _select_target_genes(self, weak_dimensions: list[str]) -> list[str]:
        """根据短板维度选择目标基因。"""
        if not weak_dimensions:
            # 随机选一个维度
            import random
            weak_dimensions = [random.choice(list(FCPIDimension)).value]

        target_genes = []
        for dim in weak_dimensions:
            genes = DIMENSION_GENE_MAP.get(dim, [])
            for g in genes:
                if g not in target_genes:
                    target_genes.append(g)

        # 添加一些随机基因 (探索)
        all_genes = self._genome.gene_names()
        import random
        for g in random.sample(all_genes, min(2, len(all_genes))):
            if g not in target_genes:
                target_genes.append(g)

        return target_genes[:5]  # 最多5个
