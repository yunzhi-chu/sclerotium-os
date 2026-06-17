"""EvolutionGenerationManager — 多代进化调度器.

管理 Mycelium AGI v4.0 的跨代进化循环，协调六个竞技场的并行评估，
聚合六维 FCPI 适应度向量，驱动 Panarchy 相变和基因组选择。

状态机:
    PENDING → INITIALIZING → RUNNING_ARENAS → AGGREGATING_FITNESS
    → SELECTING → MUTATING → CRYSTALLIZING → COMPLETE
    ↑                                          ↓
    └────────────── NEXT_GENERATION ←──────────┘

参考:
    - Darwin Gödel Machine (ICLR 2026): 进化档案 + 经验验证
    - DGM-HyperAgents (ICLR 2026): 元级自修改
    - Statistical Gödel Machine (2025): PAC 统计置信门控
    - Group-Evolving Agents (2026): 群体经验共享
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .arenas.arena_base import (
    ArenaBase,
    ArenaConfig,
    ArenaResult,
    FCPIDimension,
    FitnessVector,
)
from .arenas.coding_arena import CodingArena
from .arenas.coordination_arena import CoordinationArena
from .arenas.safety_arena import SafetyArena
from .arenas.decision_arena import DecisionArena
from .arenas.emergence_arena import EmergenceArena
from .arenas.performance_arena import PerformanceArena

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Core Data Types
# ═══════════════════════════════════════════════════════════════════════════════


class EvolutionPhase(Enum):
    """进化循环状态."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING_ARENAS = "running_arenas"
    AGGREGATING_FITNESS = "aggregating_fitness"
    SELECTING = "selecting"
    MUTATING = "mutating"
    CRYSTALLIZING = "crystallizing"
    COMPLETE = "complete"
    FAILED = "failed"
    PAUSED = "paused"


class PanarchyPhase(Enum):
    """Panarchy 自适应循环相."""
    R = "r"          # 增长/开发 (exploitation)
    K = "K"          # 保持/守恒 (conservation)
    OMEGA = "omega"  # 释放/创造性破坏 (release)
    ALPHA = "alpha"  # 重组/更新 (reorganization)


@dataclass
class GenerationSnapshot:
    """单代快照 — 不可变化石记录."""
    generation: int
    timestamp: float
    genome_id: str
    phase: PanarchyPhase
    fcpi_total: float
    fitness_vectors: dict[str, FitnessVector]  # dimension → vector
    fcpi_weights: dict[str, float]  # dimension → weight
    emergent_patterns: list[str]
    duration_seconds: float
    panarchy_connectedness: float
    panarchy_resilience: float
    population_size: int
    errors: list[str] = field(default_factory=list)


@dataclass
class EvolutionConfig:
    """进化管理器配置.

    Attributes:
        max_generations: 最大进化代数
        population_size: 基因组种群大小
        elitism_count: 每代保留的精英数量
        fcpi_weights: 六维 FCPI 权重 (可被 HyperAgents 调整)
        panarchy_thresholds: Panarchy 相变阈值
        safety_gate_enabled: 是否启用安全门控
        crystallization_confidence: 涌现模式结晶化置信度阈值
        snapshot_interval: 快照保存间隔 (代)
        parallel_arenas: 是否并行运行竞技场
    """
    max_generations: int = 100
    population_size: int = 50
    elitism_count: int = 5
    fcpi_weights: dict[str, float] = field(default_factory=lambda: {
        "coding": 0.25,
        "coordination": 0.25,
        "safety": 0.15,
        "decision": 0.15,
        "emergence": 0.10,
        "performance": 0.10,
    })
    panarchy_thresholds: dict[str, float] = field(default_factory=lambda: {
        "r_to_K_connectedness": 0.7,
        "K_to_omega_connectedness": 0.8,
        "K_to_omega_resilience": 0.2,
        "omega_to_alpha_connectedness": 0.4,
        "alpha_to_r_resilience": 0.5,
    })
    safety_gate_enabled: bool = True
    crystallization_confidence: float = 0.6
    snapshot_interval: int = 1
    parallel_arenas: bool = True


# ═══════════════════════════════════════════════════════════════════════════════
# EvolutionGenerationManager
# ═══════════════════════════════════════════════════════════════════════════════


class EvolutionGenerationManager:
    """多代进化调度器.

    核心职责:
        1. 管理进化状态机 (PENDING → ... → COMPLETE)
        2. 协调六个竞技场的并行/串行评估
        3. 聚合六维 FCPI 适应度向量
        4. 驱动 Panarchy 相变 (r→K→Ω→α)
        5. 管理基因组种群 (选择/精英保留/多样性维护)
        6. 保存完整化石记录 (每代快照)
        7. 触发涌现模式结晶化

    Usage:
        manager = EvolutionGenerationManager(work_dir=Path("uploads/evolution"))
        manager.initialize(population_size=50)
        for gen in range(100):
            report = manager.run_generation(genome_contexts)
            if report.phase == PanarchyPhase.OMEGA:
                manager.trigger_extinction_event()
    """

    def __init__(
        self,
        config: EvolutionConfig | None = None,
        work_dir: Path | None = None,
    ) -> None:
        self.config = config or EvolutionConfig()
        self.work_dir = work_dir or Path("uploads/evolution")
        self.work_dir.mkdir(parents=True, exist_ok=True)

        # 状态机
        self._phase: EvolutionPhase = EvolutionPhase.PENDING
        self._panarchy_phase: PanarchyPhase = PanarchyPhase.R
        self._generation: int = 0
        self._connectedness: float = 0.0
        self._resilience: float = 1.0

        # 种群管理
        self._population: list[dict[str, Any]] = []
        self._genome_archive: dict[str, list[GenerationSnapshot]] = {}

        # 竞技场实例
        self._arenas: dict[FCPIDimension, ArenaBase] = {}

        # 历史记录
        self._snapshots: list[GenerationSnapshot] = []
        self._fcpi_history: list[dict[str, float]] = []
        self._emergent_patterns_archive: set[str] = set()

        # 元学习状态
        self._weight_history: list[dict[str, float]] = []
        self._mutation_effectiveness: dict[str, float] = {}

        logger.info(
            "EvolutionGenerationManager initialized (max_generations=%d, population=%d)",
            self.config.max_generations, self.config.population_size,
        )

    # ── 公共 API ──────────────────────────────────────────────────────────

    @property
    def phase(self) -> EvolutionPhase:
        return self._phase

    @property
    def panarchy_phase(self) -> PanarchyPhase:
        return self._panarchy_phase

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def population_size(self) -> int:
        return len(self._population)

    @property
    def snapshots(self) -> tuple[GenerationSnapshot, ...]:
        return tuple(self._snapshots)

    def initialize(
        self,
        population: list[dict[str, Any]] | None = None,
        arena_configs: dict[FCPIDimension, ArenaConfig] | None = None,
    ) -> None:
        """初始化进化管理器.

        Args:
            population: 初始基因组种群 (None = 自动生成种子种群)
            arena_configs: 竞技场配置覆盖
        """
        self._phase = EvolutionPhase.INITIALIZING
        logger.info("Initializing evolution manager...")

        # 初始化竞技场
        self._initialize_arenas(arena_configs)

        # 初始化种群
        if population:
            self._population = population
        else:
            self._population = self._generate_seed_population()

        # 初始化 Panarchy 状态
        self._connectedness = 0.3  # 初始低连接度
        self._resilience = 0.9     # 初始高韧性

        self._phase = EvolutionPhase.PENDING
        logger.info(
            "Evolution manager initialized: %d genomes, %d arenas, phase=%s",
            len(self._population), len(self._arenas), self._panarchy_phase.value,
        )

    def run_generation(
        self,
        genome_contexts: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """运行一代完整进化评估.

        流程:
            1. RUNNING_ARENAS: 并行/串行运行六个竞技场
            2. AGGREGATING_FITNESS: 聚合六维 FCPI 适应度
            3. SELECTING: 选择/淘汰 (基于 FCPI 总分)
            4. MUTATING: 传播高适应度策略 (朊病毒构象催化)
            5. Panarchy 相变检查
            6. CRYSTALLIZING: 涌现模式结晶化
            7. 保存快照

        Args:
            genome_contexts: {genome_id: context_dict} 每个基因组对应的上下文

        Returns:
            代际进化报告
        """
        start_time = time.monotonic()
        self._generation += 1
        self._phase = EvolutionPhase.RUNNING_ARENAS

        # 选取当前种群中需要评估的基因组
        active_genomes = self._select_active_genomes(genome_contexts)
        logger.info(
            "Generation %d: evaluating %d genomes across %d arenas",
            self._generation, len(active_genomes), len(self._arenas),
        )

        # Step 1: 运行竞技场
        all_fitness: dict[str, dict[FCPIDimension, FitnessVector]] = {}
        all_emergent: list[str] = []
        errors: list[str] = []

        for genome_id, context in active_genomes.items():
            genome_fitness: dict[FCPIDimension, FitnessVector] = {}

            if self.config.parallel_arenas:
                # 并行运行 (Phase 1 使用串行模拟，后续 Phase 实现真正并行)
                for dim, arena in self._arenas.items():
                    try:
                        result = arena.run_generation(context)
                        if result.success and result.fitness_vector:
                            genome_fitness[dim] = result.fitness_vector
                            all_emergent.extend(result.emergent_patterns)
                        else:
                            errors.extend(result.errors)
                    except Exception as exc:
                        logger.exception("Arena %s failed for genome %s", dim.value, genome_id)
                        errors.append(str(exc))
            else:
                for dim, arena in self._arenas.items():
                    try:
                        result = arena.run_generation(context)
                        if result.success and result.fitness_vector:
                            genome_fitness[dim] = result.fitness_vector
                            all_emergent.extend(result.emergent_patterns)
                    except Exception as exc:
                        errors.append(str(exc))

            all_fitness[genome_id] = genome_fitness

        # Step 2: 聚合 FCPI 适应度
        self._phase = EvolutionPhase.AGGREGATING_FITNESS
        fcpi_scores = self._aggregate_fcpi(all_fitness)

        # 元学习: 调整 FCPI 权重
        self._meta_learn_weights(fcpi_scores)

        # Step 3: 选择
        self._phase = EvolutionPhase.SELECTING
        ranked = self._rank_genomes(fcpi_scores)
        self._apply_selection(ranked)

        # Step 4: 更新 Panarchy 相
        self._update_panarchy_phase()

        # Step 5: 涌现结晶化
        self._phase = EvolutionPhase.CRYSTALLIZING
        crystallized = self._crystallize_patterns(all_emergent)

        # Step 6: 保存快照
        duration = time.monotonic() - start_time
        snapshot = self._save_snapshot(
            fcpi_scores, all_fitness, all_emergent, duration, errors,
        )

        # 检查终止条件
        if self._generation >= self.config.max_generations:
            self._phase = EvolutionPhase.COMPLETE
        else:
            self._phase = EvolutionPhase.PENDING

        report = {
            "generation": self._generation,
            "phase": self._panarchy_phase.value,
            "evolution_phase": self._phase.value,
            "fcpi_scores": fcpi_scores,
            "weights": self.config.fcpi_weights,
            "population_size": len(self._population),
            "connectedness": self._connectedness,
            "resilience": self._resilience,
            "emergent_patterns": all_emergent,
            "crystallized": crystallized,
            "duration_seconds": duration,
            "errors": errors,
            "snapshot_id": snapshot.generation,
        }

        logger.info(
            "Generation %d complete: phase=%s, FCPI=%.4f, duration=%.1fs",
            self._generation, self._panarchy_phase.value,
            snapshot.fcpi_total, duration,
        )

        return report

    def get_evolution_report(self) -> dict[str, Any]:
        """获取完整进化状态报告."""
        return {
            "generation": self._generation,
            "phase": self._phase.value,
            "panarchy_phase": self._panarchy_phase.value,
            "population_size": len(self._population),
            "connectedness": self._connectedness,
            "resilience": self._resilience,
            "fcpi_weights": self.config.fcpi_weights,
            "snapshot_count": len(self._snapshots),
            "latest_fcpi": (
                self._snapshots[-1].fcpi_total if self._snapshots else None
            ),
            "emergent_pattern_count": len(self._emergent_patterns_archive),
            "arena_reports": {
                dim.value: arena.get_report()
                for dim, arena in self._arenas.items()
            },
        }

    def trigger_extinction_event(self) -> dict[str, Any]:
        """触发 Ω 相大灭绝事件.

        清退低适应度基因，重置进化规则，进入 α 相重组。
        """
        if self._panarchy_phase != PanarchyPhase.OMEGA:
            logger.warning("Extinction event triggered outside OMEGA phase")

        # 清退底部 1/3
        cutoff = len(self._population) // 3
        victims = self._population[-cutoff:] if cutoff > 0 else []
        self._population = self._population[: len(self._population) - cutoff]

        # 重置连接度 → 进入 α 相
        self._connectedness = 0.2
        self._resilience = 0.5
        self._panarchy_phase = PanarchyPhase.ALPHA

        logger.info(
            "OMEGA extinction: %d genomes culled, entering ALPHA reorganization",
            len(victims),
        )

        return {
            "event": "extinction",
            "victims_count": len(victims),
            "survivors_count": len(self._population),
            "new_phase": self._panarchy_phase.value,
            "connectedness": self._connectedness,
            "resilience": self._resilience,
        }

    # ── 私有方法 ──────────────────────────────────────────────────────────

    def _initialize_arenas(
        self, arena_configs: dict[FCPIDimension, ArenaConfig] | None
    ) -> None:
        """初始化六个竞技场实例."""
        arena_work_dir = self.work_dir / "arenas"
        arena_classes: dict[FCPIDimension, type[ArenaBase]] = {
            FCPIDimension.CODING: CodingArena,
            FCPIDimension.COORDINATION: CoordinationArena,
            FCPIDimension.SAFETY: SafetyArena,
            FCPIDimension.DECISION: DecisionArena,
            FCPIDimension.EMERGENCE: EmergenceArena,
            FCPIDimension.PERFORMANCE: PerformanceArena,
        }

        for dim, cls in arena_classes.items():
            config = (
                arena_configs.get(dim) if arena_configs
                else ArenaConfig(
                    arena_id=f"{dim.value}_{self._generation:04d}",
                    dimension=dim,
                )
            )
            arena = cls(config=config, work_dir=arena_work_dir / dim.value)
            self._arenas[dim] = arena

        logger.info("Initialized %d arenas", len(self._arenas))

    def _generate_seed_population(self) -> list[dict[str, Any]]:
        """生成初始种子种群."""
        seeds = []
        for i in range(self.config.population_size):
            genome = {
                "genome_id": f"seed_{i:04d}_{uuid.uuid4().hex[:8]}",
                "generation": 0,
                "parent_ids": [],
                "fcpi_scores": {dim.value: 0.5 for dim in FCPIDimension},
                "fcpi_total": 0.5,
                "mutation_count": 0,
                "birth_generation": 0,
                "status": "active",
                "metadata": {"seed_index": i},
            }
            seeds.append(genome)
        return seeds

    def _select_active_genomes(
        self, genome_contexts: dict[str, dict[str, Any]] | None
    ) -> dict[str, dict[str, Any]]:
        """选择当前代需要评估的基因组."""
        if genome_contexts:
            return genome_contexts

        # 默认: 评估所有活跃基因组
        active = {}
        for genome in self._population:
            if genome.get("status") == "active":
                gid = genome["genome_id"]
                active[gid] = {
                    "genome_id": gid,
                    "generation": self._generation,
                    "genome_metadata": genome.get("metadata", {}),
                    "fcpi_history": genome.get("fcpi_scores", {}),
                }
        return active

    def _aggregate_fcpi(
        self, all_fitness: dict[str, dict[FCPIDimension, FitnessVector]]
    ) -> dict[str, dict[str, float]]:
        """聚合六维 FCPI 适应度.

        FCPI_total = Σ(w_dim × fitness_dim.primary_score)
        """
        scores: dict[str, dict[str, float]] = {}

        for genome_id, dim_fitness in all_fitness.items():
            dim_scores: dict[str, float] = {}
            total = 0.0

            for dim, weight_str in self.config.fcpi_weights.items():
                dim_enum = FCPIDimension(dim)
                if dim_enum in dim_fitness:
                    score = dim_fitness[dim_enum].primary_score
                else:
                    score = 0.5  # 缺失维度默认中等
                dim_scores[dim] = score
                total += weight_str * score

            dim_scores["total"] = total
            scores[genome_id] = dim_scores

        self._fcpi_history.append(
            {gid: s.get("total", 0.5) for gid, s in scores.items()}
        )
        return scores

    def _rank_genomes(
        self, fcpi_scores: dict[str, dict[str, float]]
    ) -> list[tuple[str, float]]:
        """按 FCPI 总分排名基因组."""
        ranked = [
            (gid, scores.get("total", 0.5))
            for gid, scores in fcpi_scores.items()
        ]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def _apply_selection(self, ranked: list[tuple[str, float]]) -> None:
        """应用选择压力: 精英保留 + 多样性维护 + 移民注入."""
        if not ranked:
            return

        # 更新种群中的适应度分数
        score_map = {gid: score for gid, score in ranked}
        for genome in self._population:
            gid = genome["genome_id"]
            if gid in score_map:
                genome["fcpi_total"] = score_map[gid]

        # 精英保留
        elite_ids = {gid for gid, _ in ranked[: self.config.elitism_count]}

        # 多样性奖励: 标记分数接近但维度分布不同的基因组
        diversity_bonus_ids = self._compute_diversity_bonus(ranked, score_map)

        # 温和淘汰: 仅淘汰底部 10% (而非 20%), 且不低于精英数+多样性保留
        min_survivors = max(self.config.elitism_count + 3, int(len(self._population) * 0.9))
        cutoff_idx = max(min_survivors, int(len(self._population) * 0.9))
        keep_ids = {gid for gid, _ in ranked[:cutoff_idx]} | elite_ids | diversity_bonus_ids

        # 标记淘汰
        extinct_count = 0
        for genome in self._population:
            if genome["genome_id"] not in keep_ids:
                genome["status"] = "extinct"
                extinct_count += 1

        # 移除已淘汰的
        self._population = [
            g for g in self._population
            if g.get("status") != "extinct"
        ]

        # 移民注入: 每代注入少量新基因组维持多样性
        self._inject_immigrants(ranked)

        # 种群补充: 如果低于目标大小的50%, 繁殖补充
        target_min = max(self.config.elitism_count * 2, self.config.population_size // 3)
        while len(self._population) < target_min:
            parents = [gid for gid, _ in ranked[:max(2, len(ranked)//4)]]
            new_genome = {
                "genome_id": f"gen_{self._generation:04d}_{uuid.uuid4().hex[:8]}",
                "generation": self._generation,
                "parent_ids": parents[:2],
                "fcpi_scores": {},
                "fcpi_total": 0.5,
                "mutation_count": 0,
                "birth_generation": self._generation,
                "status": "active",
                "metadata": {"origin": "repopulation"},
            }
            self._population.append(new_genome)

        logger.info(
            "Selection: %d survivors (-%d extinct), %d elite, %d diversity_bonus, pop=%d",
            len(self._population), extinct_count, len(elite_ids),
            len(diversity_bonus_ids), len(self._population),
        )

    def _compute_diversity_bonus(
        self, ranked: list[tuple[str, float]], score_map: dict[str, float]
    ) -> set[str]:
        """计算多样性奖励: 保留维度分布独特的基因组."""
        bonus: set[str] = set()
        if len(ranked) < 5:
            return bonus

        # 收集每个基因组的维度分数
        dim_vectors: dict[str, dict[str, float]] = {}
        for genome in self._population:
            gid = genome["genome_id"]
            scores = genome.get("fcpi_scores", {})
            if scores and len(scores) >= 6:
                dim_vectors[gid] = dict(scores)

        if len(dim_vectors) < 3:
            return bonus

        # 找到维度分布最独特的基因组 (离群值检测)
        all_dims = ["coding", "coordination", "safety", "decision", "emergence", "performance"]
        for gid, vec in dim_vectors.items():
            # 计算该基因组与种群平均向量的距离
            distances = []
            for other_gid, other_vec in dim_vectors.items():
                if other_gid != gid:
                    dist = sum(abs(vec.get(d, 0.5) - other_vec.get(d, 0.5)) for d in all_dims) / 6
                    distances.append(dist)
            avg_distance = sum(distances) / len(distances) if distances else 0

            # 如果该基因组与平均种群距离 > 0.1, 且不在淘汰边缘, 给予多样性保护
            if avg_distance > 0.08 and score_map.get(gid, 0) > 0.4:
                bonus.add(gid)

        return bonus

    def _inject_immigrants(self, ranked: list[tuple[str, float]]) -> None:
        """注入移民基因组维持种群多样性.

        每代注入 1-2 个全新随机基因组, 模拟基因流.
        这个机制防止种群陷入单一基因型。
        """
        current_size = len(self._population)
        target_size = min(self.config.population_size, 30)

        # 种群越小, 移民比例越高
        if current_size < 10:
            immigrant_count = 2
        elif current_size < 20:
            immigrant_count = 1
        else:
            immigrant_count = 1 if current_size < target_size else 0

        for i in range(immigrant_count):
            immigrant = {
                "genome_id": f"immigrant_{self._generation:04d}_{uuid.uuid4().hex[:8]}",
                "generation": self._generation,
                "parent_ids": [],
                "fcpi_scores": {dim.value: 0.5 for dim in FCPIDimension},
                "fcpi_total": 0.5,
                "mutation_count": 0,
                "birth_generation": self._generation,
                "status": "active",
                "metadata": {"origin": "immigration", "wave": self._generation},
            }
            self._population.append(immigrant)

        if immigrant_count > 0:
            logger.info("Immigration: %d new genomes injected", immigrant_count)

    def _update_panarchy_phase(self) -> None:
        """更新 Panarchy 自适应循环相.

        相变条件:
            r → K:   connectedness > 0.7
            K → Ω:  connectedness > 0.8 AND resilience < 0.2
            Ω → α:  connectedness < 0.4 (after extinction)
            α → r:   resilience > 0.5
        """
        t = self.config.panarchy_thresholds

        # 更新连接度和韧性
        pop_ratio = len(self._population) / max(self.config.population_size, 1)
        # 连接度增长更慢, 韧性衰减更慢 (防止小种群加速崩溃)
        self._connectedness = min(1.0, self._connectedness + 0.03 * pop_ratio)
        pop_penalty = max(0.0, 1.0 - pop_ratio)
        self._resilience = max(0.05, self._resilience - 0.01 * pop_penalty)

        old_phase = self._panarchy_phase

        if self._panarchy_phase == PanarchyPhase.R:
            if self._connectedness > t["r_to_K_connectedness"]:
                self._panarchy_phase = PanarchyPhase.K
        elif self._panarchy_phase == PanarchyPhase.K:
            if (
                self._connectedness > t["K_to_omega_connectedness"]
                and self._resilience < t["K_to_omega_resilience"]
            ):
                self._panarchy_phase = PanarchyPhase.OMEGA
        elif self._panarchy_phase == PanarchyPhase.OMEGA:
            self.trigger_extinction_event()
        elif self._panarchy_phase == PanarchyPhase.ALPHA:
            if self._resilience > t["alpha_to_r_resilience"]:
                self._panarchy_phase = PanarchyPhase.R

        if old_phase != self._panarchy_phase:
            logger.info(
                "Panarchy phase transition: %s → %s (C=%.2f, R=%.2f)",
                old_phase.value, self._panarchy_phase.value,
                self._connectedness, self._resilience,
            )

    def _crystallize_patterns(self, emergent_patterns: list[str]) -> list[str]:
        """结晶化涌现模式 — 达到置信度阈值的模式被永久保留."""
        crystallized = []
        for pattern in emergent_patterns:
            if pattern not in self._emergent_patterns_archive:
                self._emergent_patterns_archive.add(pattern)
                # 检查是否达到结晶化阈值 (出现频率)
                occurrence_count = sum(
                    1 for s in self._snapshots
                    if pattern in s.emergent_patterns
                )
                if occurrence_count >= self.config.crystallization_confidence * 3:
                    crystallized.append(pattern)
                    logger.info("Pattern crystallized: %s (occurrences=%d)", pattern, occurrence_count)

        return crystallized

    def _save_snapshot(
        self,
        fcpi_scores: dict[str, dict[str, float]],
        all_fitness: dict[str, dict[FCPIDimension, FitnessVector]],
        emergent_patterns: list[str],
        duration: float,
        errors: list[str],
    ) -> GenerationSnapshot:
        """保存代际快照 (化石记录)."""
        # 计算种群平均 FCPI
        avg_fcpi = (
            sum(s.get("total", 0.5) for s in fcpi_scores.values()) / len(fcpi_scores)
            if fcpi_scores
            else 0.5
        )

        # 聚合所有适应度向量 (取平均)
        aggregated_vectors: dict[str, FitnessVector] = {}
        for dim in FCPIDimension:
            vectors = [
                fitness[dim]
                for fitness in all_fitness.values()
                if dim in fitness
            ]
            if vectors:
                avg_score = sum(v.primary_score for v in vectors) / len(vectors)
                avg_subs = {}
                for key in vectors[0].sub_scores:
                    avg_subs[key] = sum(v.sub_scores.get(key, 0) for v in vectors) / len(vectors)
                aggregated_vectors[dim.value] = FitnessVector(
                    dimension=dim,
                    primary_score=avg_score,
                    sub_scores=avg_subs,
                    confidence=sum(v.confidence for v in vectors) / len(vectors),
                    generation=self._generation,
                    genome_id="aggregate",
                    arena_id="evolution_manager",
                )

        snapshot = GenerationSnapshot(
            generation=self._generation,
            timestamp=time.time(),
            genome_id="population_aggregate",
            phase=self._panarchy_phase,
            fcpi_total=avg_fcpi,
            fitness_vectors=aggregated_vectors,
            fcpi_weights=dict(self.config.fcpi_weights),
            emergent_patterns=list(emergent_patterns),
            duration_seconds=duration,
            panarchy_connectedness=self._connectedness,
            panarchy_resilience=self._resilience,
            population_size=len(self._population),
            errors=errors,
        )

        self._snapshots.append(snapshot)

        # 持久化快照
        snap_path = self.work_dir / f"snapshot_gen_{self._generation:04d}.json"
        with open(snap_path, "w", encoding="utf-8") as f:
            json.dump({
                "generation": snapshot.generation,
                "timestamp": snapshot.timestamp,
                "phase": snapshot.phase.value,
                "fcpi_total": snapshot.fcpi_total,
                "weights": snapshot.fcpi_weights,
                "connectedness": snapshot.panarchy_connectedness,
                "resilience": snapshot.panarchy_resilience,
                "population_size": snapshot.population_size,
                "emergent_patterns": snapshot.emergent_patterns,
                "errors": snapshot.errors,
                "fitness_vectors": {
                    dim: {
                        "primary_score": v.primary_score,
                        "sub_scores": v.sub_scores,
                        "confidence": v.confidence,
                    }
                    for dim, v in snapshot.fitness_vectors.items()
                },
            }, f, ensure_ascii=False, indent=2)

        return snapshot

    def _meta_learn_weights(self, fcpi_scores: dict[str, dict[str, float]]) -> None:
        """元学习: 根据多代趋势调整 FCPI 权重.

        参考 DGM-HyperAgents (ICLR 2026):
            - 如果某维度持续退化 → 提升其权重 (更多选择压力)
            - 如果某维度持续饱和 → 降低其权重 (释放资源给其他维度)
        """
        if len(self._fcpi_history) < 5:
            return  # 需要足够的历史数据

        # 计算每个维度的趋势
        recent_scores = self._fcpi_history[-5:]
        for dim in FCPIDimension:
            dim_key = dim.value
            dim_scores = [
                scores.get(dim_key, 0.5)
                for genome_scores in recent_scores
                for scores in [genome_scores] if isinstance(genome_scores, dict)
            ]
            if not dim_scores:
                continue

            # 简单线性趋势
            if len(dim_scores) >= 2:
                trend = dim_scores[-1] - dim_scores[0]
                current_weight = self.config.fcpi_weights[dim_key]

                if trend < -0.05:  # 退化趋势
                    # 提升权重 (最多 2x)
                    self.config.fcpi_weights[dim_key] = min(current_weight * 1.15, 0.40)
                elif trend < 0.01:  # 饱和趋势
                    # 降低权重 (最少 0.05)
                    self.config.fcpi_weights[dim_key] = max(current_weight * 0.95, 0.05)

        # 归一化权重
        total_weight = sum(self.config.fcpi_weights.values())
        if total_weight > 0:
            for dim in self.config.fcpi_weights:
                self.config.fcpi_weights[dim] /= total_weight

        self._weight_history.append(dict(self.config.fcpi_weights))

    def to_fcpi_vector(self, genome_id: str) -> dict[str, float] | None:
        """返回指定基因组的六维 FCPI 向量 (供 Mycelium SelfEvolutionLoop 消费)."""
        for genome in self._population:
            if genome["genome_id"] == genome_id:
                return genome.get("fcpi_scores", None)
        return None
