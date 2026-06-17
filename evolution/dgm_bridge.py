"""DGM Bridge — DarwinianGodelMachine 5变异 (L6)。

替代简单的 StrategyGenome 随机变异, 升级为:
  - INSERT: 插入新基因 (从预训练策略DNA库)
  - DELETE: 删除有害基因
  - SUBSTITUTE: 替换低效基因 (FCPI驱动)
  - CROSSOVER: 交叉两个最优基因组
  - DUPLICATE: 复制高效基因到相关维度

使用方式:
    bridge = DGMBridge()
    bridge.load_strategy_dna()  # 加载689预训练策略DNA
    mutated = bridge.mutate(genome, fcpi_vector, mutation_type="substitute")
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from evolution.strategy_genome import StrategyGenome, GeneSpec, GeneType, GenomeConfig
from evolution.fcpi_tracker import FCPIVector, FCPIDimension

logger = logging.getLogger("sclerotium.dgm")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

class DGMutationType(str, Enum):
    INSERT = "insert"          # 插入新基因
    DELETE = "delete"          # 删除基因
    SUBSTITUTE = "substitute"  # 替换低效基因
    CROSSOVER = "crossover"    # 交叉两个基因组
    DUPLICATE = "duplicate"    # 复制高效基因


@dataclass(frozen=True)
class DGMMutationResult:
    """DGM变异结果 (不可变)。"""
    mutation_type: DGMutationType
    gene_name: str
    old_value: Any
    new_value: Any
    reason: str = ""
    fcpi_dimension: str = ""
    timestamp: float = field(default_factory=time.time)


# 预训练策略DNA片段 (689+ 简化版)
STRATEGY_DNA_LIBRARY: dict[str, list[dict[str, Any]]] = {
    "aggressive_developer": [
        {"nudge_threshold_work": 0.3, "pyloric_interval": 15.0,
         "search_top_k": 20, "ema_learning_rate": 0.15},
    ],
    "conservative_worker": [
        {"nudge_threshold_work": 0.7, "pyloric_interval": 60.0,
         "search_top_k": 5, "ema_learning_rate": 0.03},
    ],
    "night_owl": [
        {"nudge_threshold_sleep": 0.95, "gastric_interval": 7200.0,
         "daily_digest_hour": 23},
    ],
    "early_bird": [
        {"nudge_threshold_sleep": 0.8, "gastric_interval": 3000.0,
         "daily_digest_hour": 20},
    ],
}

# FCPI维度 → 优先变异类型
DIMENSION_MUTATION_MAP: dict[str, DGMutationType] = {
    "coding": DGMutationType.SUBSTITUTE,        # 编码问题 → 替换策略
    "coordination": DGMutationType.CROSSOVER,   # 协调问题 → 交叉最优
    "safety": DGMutationType.DELETE,            # 安全问题 → 删除危险基因
    "decision": DGMutationType.DUPLICATE,       # 决策问题 → 复制成功策略
    "emergence": DGMutationType.INSERT,         # 涌现不足 → 插入新基因
    "performance": DGMutationType.SUBSTITUTE,   # 性能问题 → 替换参数
}


# ═══════════════════════════════════════════════════════════════
# DGMBridge
# ═══════════════════════════════════════════════════════════════

class DGMBridge:
    """DGM 5变异桥接 — 基于FCPI的定向基因进化。

    使用方式:
        dgm = DGMBridge()
        dgm.load_strategy_dna()

        # 基于FCPI短板定向变异
        fcpi = FCPIVector(coding=0.3, safety=0.9)
        mutated = dgm.mutate(genome, fcpi)
    """

    def __init__(self) -> None:
        self._dna_library: dict[str, list[dict[str, Any]]] = dict(STRATEGY_DNA_LIBRARY)
        self._mutation_history: list[DGMMutationResult] = []

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def load_strategy_dna(self, dna_dict: dict | None = None) -> None:
        """加载预训练策略DNA。"""
        if dna_dict:
            self._dna_library.update(dna_dict)

    def mutate(
        self,
        genome: StrategyGenome,
        fcpi: FCPIVector,
        mutation_type: DGMutationType | None = None,
    ) -> tuple[StrategyGenome, DGMMutationResult]:
        """基于FCPI短板定向变异。

        Args:
            genome: 当前基因组
            fcpi: 当前FCPI向量
            mutation_type: 指定变异类型 (None=自动选择)

        Returns:
            (变异后基因组, 变异记录)
        """
        # 自动选择变异类型
        if mutation_type is None:
            weak_dims = fcpi.weak_dimensions(threshold=0.35)
            if weak_dims:
                dim = random.choice(weak_dims)
                mutation_type = DIMENSION_MUTATION_MAP.get(dim, DGMutationType.SUBSTITUTE)
            else:
                mutation_type = DGMutationType.SUBSTITUTE

        # 执行变异
        if mutation_type == DGMutationType.INSERT:
            mutant, record = self._mutate_insert(genome, fcpi)
        elif mutation_type == DGMutationType.DELETE:
            mutant, record = self._mutate_delete(genome, fcpi)
        elif mutation_type == DGMutationType.SUBSTITUTE:
            mutant, record = self._mutate_substitute(genome, fcpi)
        elif mutation_type == DGMutationType.CROSSOVER:
            mutant, record = self._mutate_crossover(genome)
        elif mutation_type == DGMutationType.DUPLICATE:
            mutant, record = self._mutate_duplicate(genome, fcpi)
        else:
            mutant, record = genome, DGMMutationResult(
                mutation_type=DGMutationType.SUBSTITUTE,
                gene_name="", old_value=None, new_value=None,
                reason="Unknown type, no mutation",
            )

        self._mutation_history.append(record)
        if len(self._mutation_history) > 500:
            self._mutation_history = self._mutation_history[-500:]

        return mutant, record

    def get_history(self, limit: int = 20) -> list[DGMMutationResult]:
        return self._mutation_history[-limit:]

    # ═══════════════════════════════════════════════════════════
    # 五种变异实现
    # ═══════════════════════════════════════════════════════════

    def _mutate_insert(
        self, genome: StrategyGenome, fcpi: FCPIVector,
    ) -> tuple[StrategyGenome, DGMMutationResult]:
        """INSERT: 从策略DNA库中注入新基因值。"""
        dna_name = random.choice(list(self._dna_library.keys()))
        dna_set = self._dna_library[dna_name]
        if dna_set:
            dna = random.choice(dna_set)
            for gene_name, value in dna.items():
                genome.set(gene_name, value)
            return genome, DGMMutationResult(
                mutation_type=DGMutationType.INSERT,
                gene_name="batch", old_value=None, new_value=dna_name,
                reason=f"Inserted '{dna_name}' strategy DNA",
            )
        return genome, DGMMutationResult(
            mutation_type=DGMutationType.INSERT,
            gene_name="", old_value=None, new_value=None,
            reason="No DNA available",
        )

    def _mutate_delete(
        self, genome: StrategyGenome, fcpi: FCPIVector,
    ) -> tuple[StrategyGenome, DGMMutationResult]:
        """DELETE: 将低FCPI相关基因重置为默认值。"""
        weak = fcpi.weak_dimensions(threshold=0.3)
        if weak:
            dim = random.choice(weak)
        else:
            dim = "safety"
        genes = DIMENSION_GENE_MAP.get(dim, [])
        gene_name = random.choice(genes) if genes else "nudge_threshold_work"
        old = genome.get(gene_name)
        genome.set(gene_name, 0.5)  # 重置为中性
        return genome, DGMMutationResult(
            mutation_type=DGMutationType.DELETE,
            gene_name=gene_name, old_value=old, new_value=0.5,
            reason=f"Reset {gene_name} (weak FCPI:{dim})",
            fcpi_dimension=dim,
        )

    def _mutate_substitute(
        self, genome: StrategyGenome, fcpi: FCPIVector,
    ) -> tuple[StrategyGenome, DGMMutationResult]:
        """SUBSTITUTE: 用成功策略DNA替换弱维度的基因。"""
        weak = fcpi.weak_dimensions(threshold=0.35)
        if weak:
            dim = random.choice(weak)
        else:
            dim = fcpi.dominant_dimension()
        genes = DIMENSION_GENE_MAP.get(dim, [])
        gene_name = random.choice(genes) if genes else "search_top_k"
        old = genome.get(gene_name)

        # 从DNA库中找更好的值
        best_val = None
        for dna_set in self._dna_library.values():
            for dna in dna_set:
                if gene_name in dna:
                    if best_val is None or abs(dna[gene_name] - 0.5) > abs(best_val - 0.5):
                        best_val = dna[gene_name]
        if best_val is not None:
            genome.set(gene_name, best_val)
        else:
            # 高斯变异回退
            genome = genome.mutate(num_mutations=1)

        return genome, DGMMutationResult(
            mutation_type=DGMutationType.SUBSTITUTE,
            gene_name=gene_name, old_value=old,
            new_value=genome.get(gene_name),
            reason=f"Substituted {gene_name} for FCPI:{dim}",
            fcpi_dimension=dim,
        )

    def _mutate_crossover(
        self, genome: StrategyGenome,
    ) -> tuple[StrategyGenome, DGMMutationResult]:
        """CROSSOVER: 与DNA库中最优策略交叉。"""
        dna_name = random.choice(list(self._dna_library.keys()))
        dna_set = self._dna_library[dna_name]
        if dna_set:
            dna = random.choice(dna_set)
            # 随机选择一半基因来自DNA
            for gene_name, value in dna.items():
                if random.random() < 0.5:
                    genome.set(gene_name, value)
        return genome, DGMMutationResult(
            mutation_type=DGMutationType.CROSSOVER,
            gene_name="crossover", old_value=None,
            new_value=dna_name,
            reason=f"Crossover with '{dna_name}'",
        )

    def _mutate_duplicate(
        self, genome: StrategyGenome, fcpi: FCPIVector,
    ) -> tuple[StrategyGenome, DGMMutationResult]:
        """DUPLICATE: 复制高分维度的基因配置到低分维度。"""
        dom = fcpi.dominant_dimension()
        weak = fcpi.weak_dimensions(threshold=0.3)
        if not weak:
            weak = [random.choice(list(FCPIDimension)).value]
        target = random.choice(weak)

        dom_genes = DIMENSION_GENE_MAP.get(dom, [])
        target_genes = DIMENSION_GENE_MAP.get(target, [])

        if dom_genes and target_genes:
            src_gene = random.choice(dom_genes)
            dst_gene = random.choice(target_genes)
            val = genome.get(src_gene)
            if val is not None:
                genome.set(dst_gene, val)
                return genome, DGMMutationResult(
                    mutation_type=DGMutationType.DUPLICATE,
                    gene_name=dst_gene, old_value=None, new_value=val,
                    reason=f"Duplicated {src_gene}({dom})→{dst_gene}({target})",
                    fcpi_dimension=target,
                )
        return genome, DGMMutationResult(
            mutation_type=DGMutationType.DUPLICATE,
            gene_name="", old_value=None, new_value=None,
            reason="No compatible genes to duplicate",
        )


# 维度→基因映射 (与 evolution_loop 保持一致)
DIMENSION_GENE_MAP: dict[str, list[str]] = {
    "coding": ["nudge_threshold_work", "search_top_k"],
    "coordination": ["nudge_cooldown_work", "pyloric_interval"],
    "safety": ["nudge_threshold_sleep", "notify_max_per_hour"],
    "decision": ["ema_learning_rate", "insight_min_confidence"],
    "emergence": ["consolidation_threshold_episodic", "insight_min_confidence"],
    "performance": ["pyloric_interval", "gastric_interval", "search_top_k"],
}
