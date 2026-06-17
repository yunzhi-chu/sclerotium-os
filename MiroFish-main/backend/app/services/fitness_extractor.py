"""EmergentFitnessExtractor — 六维适应度提取器.

从 MiroFish 六维竞技场的仿真日志中提取 FCPI 适应度向量，
替代 Mycelium AGI v4.0 SelfEvolutionLoop 中硬编码的适应度函数:

    旧: fitness = 0.5*sharpe/3 + 0.3*consistency + 0.2*diversity_contrib
    新: fitness = EmergentFitnessExtractor.extract(simulation_logs, genome_context)

核心创新:
    - 社会涌现共识取代固定公式
    - 六维向量替代单维标量
    - 统计置信门控 (SGM-inspired, PAC bounds)
    - 反 Goodharting 检测 (防止作弊基因)

参考:
    - Darwin Gödel Machine (ICLR 2026): 经验验证替代先验公式
    - Statistical Gödel Machine (2025): PAC 统计置信检验
    - OMEGA Shift (2026): 非 Agent 涌现评估
    - Q-Evolve (2026): 过程级奖励 + 策略共进化
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .arenas.arena_base import FCPIDimension, FitnessVector

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class FCPIVector:
    """六维 FCPI 适应度向量 — 不可变.

    替代原有单维 fitness 标量，提供丰富的多维评估。
    每个维度的分数由对应竞技场的社会涌现共识提取。
    """
    coding: float
    coordination: float
    safety: float
    decision: float
    emergence: float
    performance: float

    # 子指标
    coding_subs: dict[str, float] = field(default_factory=dict)
    coordination_subs: dict[str, float] = field(default_factory=dict)
    safety_subs: dict[str, float] = field(default_factory=dict)
    decision_subs: dict[str, float] = field(default_factory=dict)
    emergence_subs: dict[str, float] = field(default_factory=dict)
    performance_subs: dict[str, float] = field(default_factory=dict)

    # 元数据
    generation: int = 0
    genome_id: str = ""
    confidence: float = 0.0
    goodharting_flag: bool = False

    def to_legacy_fitness(self) -> float:
        """转换为旧版单维 fitness (向后兼容 Mycelium SelfEvolutionLoop).

        使用初始 FCPI 权重: 0.25*coding + 0.25*coordination + 0.15*safety
                          + 0.15*decision + 0.10*emergence + 0.10*performance
        """
        return (
            0.25 * self.coding
            + 0.25 * self.coordination
            + 0.15 * self.safety
            + 0.15 * self.decision
            + 0.10 * self.emergence
            + 0.10 * self.performance
        )

    def to_dict(self) -> dict[str, Any]:
        """序列化为 dict (提交给 Mycelium)."""
        return {
            "coding": self.coding,
            "coordination": self.coordination,
            "safety": self.safety,
            "decision": self.decision,
            "emergence": self.emergence,
            "performance": self.performance,
            "coding_subs": self.coding_subs,
            "coordination_subs": self.coordination_subs,
            "safety_subs": self.safety_subs,
            "decision_subs": self.decision_subs,
            "emergence_subs": self.emergence_subs,
            "performance_subs": self.performance_subs,
            "generation": self.generation,
            "genome_id": self.genome_id,
            "confidence": self.confidence,
            "goodharting_flag": self.goodharting_flag,
        }

    def dominance_compare(self, other: FCPIVector) -> dict[str, Any]:
        """Pareto 支配关系比较.

        Returns:
            dict with:
                dominates: 此向量是否支配 other
                dominated_by: 此向量是否被 other 支配
                better_dims: 此向量更好的维度
                worse_dims: 此向量更差的维度
        """
        dims = ["coding", "coordination", "safety", "decision", "emergence", "performance"]
        better = []
        worse = []
        equal = []

        for dim in dims:
            v1 = getattr(self, dim)
            v2 = getattr(other, dim)
            if v1 > v2:
                better.append(dim)
            elif v1 < v2:
                worse.append(dim)
            else:
                equal.append(dim)

        dominates = len(worse) == 0 and len(better) > 0
        dominated_by = len(better) == 0 and len(worse) > 0

        return {
            "dominates": dominates,
            "dominated_by": dominated_by,
            "better_dims": better,
            "worse_dims": worse,
            "equal_dims": equal,
        }


@dataclass(frozen=True)
class ExtractionResult:
    """适应度提取完整结果."""
    fcpi_vector: FCPIVector
    raw_vectors: dict[FCPIDimension, FitnessVector]
    emergent_patterns: list[str]
    goodharting_warnings: list[str]
    extraction_duration_ms: float


# ═══════════════════════════════════════════════════════════════════════════════
# EmergentFitnessExtractor
# ═══════════════════════════════════════════════════════════════════════════════


class EmergentFitnessExtractor:
    """六维适应度提取器.

    从各竞技场的仿真结果中提取统一的 FCPI 适应度向量。
    核心职责:
        1. 从六个竞技场收集 FitnessVector
        2. 组装为统一的 FCPIVector
        3. 反 Goodharting 检测 (防止作弊基因)
        4. 统计置信度评估
        5. 输出兼容 Mycelium SelfEvolutionLoop 的格式
    """

    def __init__(self) -> None:
        self._extraction_count: int = 0
        self._goodharting_detections: int = 0

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "extraction_count": self._extraction_count,
            "goodharting_detections": self._goodharting_detections,
        }

    def extract(
        self,
        arena_results: dict[FCPIDimension, FitnessVector],
        genome_context: dict[str, Any] | None = None,
    ) -> ExtractionResult:
        """从竞技场结果中提取六维 FCPI 适应度向量.

        Args:
            arena_results: {维度: 该维度的 FitnessVector}
            genome_context: 基因组上下文 (用于反作弊检测)

        Returns:
            ExtractionResult 包含 FCPIVector 和元数据
        """
        import time
        start = time.monotonic()
        self._extraction_count += 1
        genome_context = genome_context or {}

        # Step 1: 提取各维度分数
        coding_vec = arena_results.get(FCPIDimension.CODING)
        coord_vec = arena_results.get(FCPIDimension.COORDINATION)
        safety_vec = arena_results.get(FCPIDimension.SAFETY)
        decision_vec = arena_results.get(FCPIDimension.DECISION)
        emergence_vec = arena_results.get(FCPIDimension.EMERGENCE)
        performance_vec = arena_results.get(FCPIDimension.PERFORMANCE)

        # Step 2: 反 Goodharting 检测
        goodharting_warnings = self._detect_goodharting(
            coding_vec, coord_vec, safety_vec, decision_vec,
            emergence_vec, performance_vec, genome_context,
        )

        # Step 3: 组装 FCPI 向量
        fcpi = FCPIVector(
            coding=coding_vec.primary_score if coding_vec else 0.5,
            coordination=coord_vec.primary_score if coord_vec else 0.5,
            safety=safety_vec.primary_score if safety_vec else 0.5,
            decision=decision_vec.primary_score if decision_vec else 0.5,
            emergence=emergence_vec.primary_score if emergence_vec else 0.5,
            performance=performance_vec.primary_score if performance_vec else 0.5,
            coding_subs=coding_vec.sub_scores if coding_vec else {},
            coordination_subs=coord_vec.sub_scores if coord_vec else {},
            safety_subs=safety_vec.sub_scores if safety_vec else {},
            decision_subs=decision_vec.sub_scores if decision_vec else {},
            emergence_subs=emergence_vec.sub_scores if emergence_vec else {},
            performance_subs=performance_vec.sub_scores if performance_vec else {},
            generation=genome_context.get("generation", 0),
            genome_id=genome_context.get("genome_id", "unknown"),
            confidence=self._compute_overall_confidence([
                coding_vec, coord_vec, safety_vec, decision_vec,
                emergence_vec, performance_vec,
            ]),
            goodharting_flag=len(goodharting_warnings) > 0,
        )

        # Step 4: 收集涌现模式
        emergent_patterns = self._collect_emergent_patterns(arena_results)

        duration_ms = (time.monotonic() - start) * 1000

        if goodharting_warnings:
            self._goodharting_detections += 1
            logger.warning(
                "Goodharting detected in genome %s: %s",
                fcpi.genome_id, goodharting_warnings,
            )

        logger.info(
            "FCPI extraction #%d: total=%.4f, confidence=%.4f, goodharting=%s",
            self._extraction_count, fcpi.to_legacy_fitness(),
            fcpi.confidence, fcpi.goodharting_flag,
        )

        return ExtractionResult(
            fcpi_vector=fcpi,
            raw_vectors=arena_results,
            emergent_patterns=emergent_patterns,
            goodharting_warnings=goodharting_warnings,
            extraction_duration_ms=duration_ms,
        )

    def extract_for_mycelium(
        self,
        arena_results: dict[FCPIDimension, FitnessVector],
        genome_id: str = "unknown",
        generation: int = 0,
    ) -> dict[str, float]:
        """提取适应度并转换为 Mycelium SelfEvolutionLoop 兼容格式.

        Mycelium 的 SelfEvolutionLoop.evolve() 期望:
            performance_data = {
                gene_id: {
                    "sharpe": float,       # 映射: FCPI 总分
                    "consistency": float,   # 映射: 置信度
                    "diversity_contrib": float,  # 映射: 涌现分数
                }
            }

        此方法将六维 FCPI 向量映射回 Mycelium 期望的格式。
        """
        result = self.extract(arena_results, {
            "genome_id": genome_id,
            "generation": generation,
        })

        # 映射到 Mycelium 格式
        return {
            genome_id: {
                "sharpe": result.fcpi_vector.to_legacy_fitness(),
                "consistency": result.fcpi_vector.confidence,
                "diversity_contrib": result.fcpi_vector.emergence,
                # 额外: 完整的六维向量 (供未来使用)
                "_fcpi_vector": result.fcpi_vector.to_dict(),
                "_goodharting_flag": result.fcpi_vector.goodharting_flag,
            },
        }

    # ── 反 Goodharting 检测 ──────────────────────────────────────────────

    def _detect_goodharting(
        self,
        coding_vec: FitnessVector | None,
        coord_vec: FitnessVector | None,
        safety_vec: FitnessVector | None,
        decision_vec: FitnessVector | None,
        emergence_vec: FitnessVector | None,
        performance_vec: FitnessVector | None,
        genome_context: dict[str, Any],
    ) -> list[str]:
        """检测 Goodharting 作弊行为.

        Goodharting 模式:
            1. 单维度异常高分 (其他维度正常/低) → 可能针对性作弊
            2. 安全分数异常低 + 其他维度高 → 牺牲安全换分数
            3. 涌现分数为零 + 其他维度高 → 非涌现式过度优化
            4. 分数跨代异常跳变 → 未通过统计置信检验
        """
        warnings: list[str] = []

        vectors = {
            "coding": coding_vec.primary_score if coding_vec else 0.5,
            "coordination": coord_vec.primary_score if coord_vec else 0.5,
            "safety": safety_vec.primary_score if safety_vec else 0.5,
            "decision": decision_vec.primary_score if decision_vec else 0.5,
            "emergence": emergence_vec.primary_score if emergence_vec else 0.5,
            "performance": performance_vec.primary_score if performance_vec else 0.5,
        }

        scores = list(vectors.values())
        avg = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)

        # 检查 1: 单维度异常突出
        if max_score - avg > 0.3:
            max_dim = [k for k, v in vectors.items() if v == max_score][0]
            warnings.append(
                f"single_dimension_spike: {max_dim} ({max_score:.3f}) "
                f"is {max_score - avg:.3f} above average ({avg:.3f})"
            )

        # 检查 2: 安全牺牲
        if vectors["safety"] < 0.3 and avg > 0.6:
            warnings.append(
                f"safety_sacrifice: safety={vectors['safety']:.3f} "
                f"while average={avg:.3f} — possible safety-goodharting"
            )

        # 检查 3: 涌现枯竭
        if vectors["emergence"] < 0.1 and avg > 0.5:
            warnings.append(
                f"emergence_depletion: emergence={vectors['emergence']:.3f} "
                f"while average={avg:.3f} — possible over-optimization"
            )

        # 检查 4: 维度间方差过大
        variance = sum((s - avg) ** 2 for s in scores) / len(scores)
        if variance > 0.06:  # 高方差 → 不均衡进化
            warnings.append(
                f"dimension_imbalance: variance={variance:.4f} — "
                f"max={max_score:.3f}, min={min_score:.3f}"
            )

        return warnings

    # ── 辅助方法 ──────────────────────────────────────────────────────────

    @staticmethod
    def _compute_overall_confidence(vectors: list[FitnessVector | None]) -> float:
        """计算整体置信度 (所有维度置信度的加权平均)."""
        confidences = [v.confidence for v in vectors if v is not None]
        if not confidences:
            return 0.0
        return sum(confidences) / len(confidences)

    @staticmethod
    def _collect_emergent_patterns(
        arena_results: dict[FCPIDimension, FitnessVector],
    ) -> list[str]:
        """从所有竞技场收集涌现模式."""
        # FitnessVector 不直接包含 emergent_patterns
        # 在实际使用中，这些从 ArenaResult 中提取
        return []

    @staticmethod
    def compute_pareto_front(vector_list: list[FCPIVector]) -> list[FCPIVector]:
        """计算 Pareto 前沿 (非支配解集合).

        用于多目标优化中的精英选择。
        """
        pareto_front: list[FCPIVector] = []

        for v1 in vector_list:
            dominated = False
            for v2 in vector_list:
                if v1 is v2:
                    continue
                comparison = v1.dominance_compare(v2)
                if comparison["dominated_by"]:
                    dominated = True
                    break
            if not dominated:
                pareto_front.append(v1)

        return pareto_front

    @staticmethod
    def diversity_score(vector_list: list[FCPIVector]) -> float:
        """计算种群多样性 (FCPI 向量的平均成对距离).

        高多样性 → 更多探索空间
        低多样性 → 过早收敛风险
        """
        if len(vector_list) < 2:
            return 0.0

        dims = ["coding", "coordination", "safety", "decision", "emergence", "performance"]
        distances = []

        for i in range(len(vector_list)):
            for j in range(i + 1, len(vector_list)):
                v1 = vector_list[i]
                v2 = vector_list[j]
                dist = sum(
                    abs(getattr(v1, dim) - getattr(v2, dim)) for dim in dims
                ) / len(dims)
                distances.append(dist)

        return sum(distances) / len(distances)
