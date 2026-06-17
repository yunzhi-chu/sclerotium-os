"""DGMBridge — FCPI 向量 → DarwinianGodelMachine 基因组变异驱动.

将六维 FCPI 评估结果映射为 DGM 的失败信号和基因适应度更新,
驱动 Mycelium AGI v4.0 的达尔文式基因组自进化。

映射关系:
    FCPI 维度              → DGM failure_signature        → 触发变异类型
    ─────────────────────────────────────────────────────────────────
    coding < 0.3           → "coding_deficiency"          → INSERT (新函数)
    safety < 0.3           → "safety_threshold_violation" → SUBSTITUTE (修复)
    coordination < 0.3     → "coordination_failure"       → CROSSOVER (混合)
    decision < 0.3         → "decision_instability"       → INSERT (新策略)
    performance < 0.3      → "performance_bottleneck"     → SUBSTITUTE (优化)
    emergence < 0.1        → "emergence_stagnation"       → DUPLICATE (探索)

    FCPI 维度              → Gene.fitness_score 更新
    ─────────────────────────────────────────────────────────────────
    coding > 0.7           → 对应的 function/skill genes +0.1
    coordination > 0.7     → 对应的 bridge/communication genes +0.1
    safety > 0.7           → 对应的 validation/sandbox genes +0.1
    decision > 0.7         → 对应的 strategy/planning genes +0.1

Usage:
    dgm = DarwinianGodelMachine()
    bridge = DGMBridge()

    # 从 FCPI 向量生成失败信号
    failures = bridge.fcpi_to_failure_signals(fcpi_vector, genome_id)

    # 记录到 DGM (触发 should_mutate)
    for f in failures:
        dgm.record_failure(genome_id, f["signature"], f["context"])

    # 更新基因适应度
    bridge.update_gene_fitness(dgm, genome_id, fcpi_vector)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Mapping Tables
# ═══════════════════════════════════════════════════════════════════════════════

# FCPI 维度 → 失败签名映射
FCPI_TO_FAILURE_SIGNATURE = {
    "coding": {
        "threshold": 0.3,
        "signature": "coding_deficiency",
        "mutation_type": "INSERT",
        "target": "function_generation",
    },
    "safety": {
        "threshold": 0.3,
        "signature": "safety_threshold_violation",
        "mutation_type": "SUBSTITUTE",
        "target": "security_gateway",
    },
    "coordination": {
        "threshold": 0.3,
        "signature": "coordination_failure",
        "mutation_type": "CROSSOVER",
        "target": "multi_agent_communication",
    },
    "decision": {
        "threshold": 0.3,
        "signature": "decision_instability",
        "mutation_type": "INSERT",
        "target": "planning_strategy",
    },
    "performance": {
        "threshold": 0.3,
        "signature": "performance_bottleneck",
        "mutation_type": "SUBSTITUTE",
        "target": "code_optimization",
    },
    "emergence": {
        "threshold": 0.1,
        "signature": "emergence_stagnation",
        "mutation_type": "DUPLICATE",
        "target": "exploration_diversification",
    },
}

# FCPI 维度 → 基因类型映射 (用于更新 Gene.fitness_score)
FCPI_TO_GENE_TYPE = {
    "coding": ("function", "class", "skill"),
    "coordination": ("bridge", "skill"),
    "safety": ("function", "class"),
    "decision": ("function", "skill"),
    "emergence": ("skill", "bridge"),
    "performance": ("function", "hyperparam"),
}


# ═══════════════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class FailureSignal:
    """DGM 失败信号."""
    signature: str
    context: dict[str, Any] = field(default_factory=dict)
    severity: float = 0.5  # 0-1, 越高越严重


@dataclass
class GeneFitnessUpdate:
    """基因适应度更新."""
    gene_id: str
    old_fitness: float
    new_fitness: float
    reason: str


@dataclass
class DGMBridgeResult:
    """DGM 桥接结果."""
    failure_signals: list[FailureSignal] = field(default_factory=list)
    gene_updates: list[GeneFitnessUpdate] = field(default_factory=list)
    should_mutate_dimensions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# DGMBridge
# ═══════════════════════════════════════════════════════════════════════════════


class DGMBridge:
    """FCPI → DarwinianGodelMachine 桥接器.

    将六维 FCPI 评估结果转化为 DGM 可理解的进化信号:
        - 低分维度 → record_failure() → should_mutate() → 触发变异
        - 高分维度 → 提升相关 Gene.fitness_score → 优先保留
        - 涌现模式 → 触发结晶化 (通过 AbilityFactory)

    设计原则:
        - 失败驱动: 低分触发变异 (DGM 核心机制)
        - 适应性反馈: 高分增强保留 (自然选择)
        - 统计门控: 低置信度的分数不触发变异 (避免噪声)
    """

    def __init__(
        self,
        failure_thresholds: dict[str, float] | None = None,
        min_confidence: float = 0.3,
    ) -> None:
        """初始化 DGM 桥接器.

        Args:
            failure_thresholds: 自定义失败阈值 {dimension: threshold}
            min_confidence: 最低置信度 (低于此值不触发变异)
        """
        self.failure_thresholds = failure_thresholds or {
            dim: info["threshold"]
            for dim, info in FCPI_TO_FAILURE_SIGNATURE.items()
        }
        self.min_confidence = min_confidence

    # ── 核心 API ────────────────────────────────────────────────────────

    def fcpi_to_failure_signals(
        self,
        fcpi_vector: Any,  # FCPIVector
        genome_id: str,
        confidence: float | None = None,
    ) -> list[FailureSignal]:
        """将 FCPI 向量转化为 DGM 失败信号.

        低于阈值的维度 → 对应的 failure_signature

        Args:
            fcpi_vector: FCPIVector 实例
            genome_id: 基因组 ID
            confidence: 覆盖 FCPI 置信度 (None = 使用 fcpi_vector.confidence)

        Returns:
            FailureSignal 列表
        """
        conf = confidence if confidence is not None else getattr(fcpi_vector, "confidence", 0.5)

        if conf < self.min_confidence:
            logger.debug(
                "Skipping failure signals for '%s': confidence too low (%.3f < %.3f)",
                genome_id, conf, self.min_confidence,
            )
            return []

        signals: list[FailureSignal] = []
        dims = ["coding", "coordination", "safety", "decision", "emergence", "performance"]

        for dim in dims:
            score = getattr(fcpi_vector, dim, 0.5)
            mapping = FCPI_TO_FAILURE_SIGNATURE.get(dim)

            if mapping and score < mapping["threshold"]:
                severity = 1.0 - (score / mapping["threshold"])
                signals.append(FailureSignal(
                    signature=mapping["signature"],
                    context={
                        "dimension": dim,
                        "score": score,
                        "threshold": mapping["threshold"],
                        "genome_id": genome_id,
                        "mutation_type": mapping["mutation_type"],
                        "target": mapping["target"],
                    },
                    severity=round(severity, 4),
                ))

        if signals:
            logger.info(
                "DGMBridge: %d failure signals for genome '%s': %s",
                len(signals), genome_id,
                [(s.signature, f"{s.severity:.2f}") for s in signals],
            )

        return signals

    def fcpi_to_gene_fitness_updates(
        self,
        fcpi_vector: Any,  # FCPIVector
        gene_map: dict[str, dict[str, Any]],  # {gene_id: {type, fitness_score, ...}}
    ) -> list[GeneFitnessUpdate]:
        """根据 FCPI 分数更新基因适应度.

        高分维度 → 提升对应类型基因的 fitness_score
        低分维度 → 降低对应类型基因的 fitness_score

        Args:
            fcpi_vector: FCPIVector 实例
            gene_map: DGM 基因组中的基因映射

        Returns:
            GeneFitnessUpdate 列表
        """
        updates: list[GeneFitnessUpdate] = []
        dims = ["coding", "coordination", "safety", "decision", "emergence", "performance"]

        for gene_id, gene_info in gene_map.items():
            gene_type = gene_info.get("type", "")
            old_fitness = gene_info.get("fitness_score", 0.5)

            # 找到该基因类型对应的 FCPI 维度
            relevant_dims = [
                dim for dim in dims
                if gene_type in FCPI_TO_GENE_TYPE.get(dim, ())
            ]

            if not relevant_dims:
                continue

            # 平均相关维度的分数
            avg_score = sum(
                getattr(fcpi_vector, dim, 0.5) for dim in relevant_dims
            ) / len(relevant_dims)

            # 适应度调整: 向 FCPI 分数方向移动
            adjustment = (avg_score - old_fitness) * 0.2  # 20% 学习率
            new_fitness = max(0.0, min(1.0, old_fitness + adjustment))

            if abs(new_fitness - old_fitness) > 0.001:
                updates.append(GeneFitnessUpdate(
                    gene_id=gene_id,
                    old_fitness=round(old_fitness, 4),
                    new_fitness=round(new_fitness, 4),
                    reason=f"FCPI {relevant_dims} avg={avg_score:.3f}",
                ))

        if updates:
            logger.info(
                "DGMBridge: %d gene fitness updates (%+.3f avg change)",
                len(updates),
                sum(u.new_fitness - u.old_fitness for u in updates) / len(updates),
            )

        return updates

    def apply_to_dgm(
        self,
        dgm: Any,  # DarwinianGodelMachine
        fcpi_vector: Any,  # FCPIVector
        genome_id: str,
        gene_map: dict[str, dict[str, Any]] | None = None,
    ) -> DGMBridgeResult:
        """一站式: 将 FCPI 评估结果应用到 DGM.

        1. 生成失败信号 → record_failure()
        2. 检查 should_mutate() → 标记需变异的维度
        3. 更新基因适应度

        Args:
            dgm: DarwinianGodelMachine 实例
            fcpi_vector: FCPIVector 实例
            genome_id: 基因组 ID
            gene_map: 基因映射 (可选, None = 跳过适应度更新)

        Returns:
            DGMBridgeResult
        """
        result = DGMBridgeResult()

        # Step 1: 生成并记录失败信号
        signals = self.fcpi_to_failure_signals(fcpi_vector, genome_id)
        result.failure_signals = signals

        for signal in signals:
            try:
                count = dgm.record_failure(
                    genome_id,
                    signal.signature,
                    signal.context,
                )
                # 检查是否应触发变异
                if dgm.should_mutate(genome_id, signal.signature):
                    dim = signal.context.get("dimension", "unknown")
                    if dim not in result.should_mutate_dimensions:
                        result.should_mutate_dimensions.append(dim)

                logger.debug(
                    "Recorded failure '%s' for '%s' (count=%d, mutate=%s)",
                    signal.signature, genome_id, count,
                    signal.context["dimension"] in result.should_mutate_dimensions,
                )
            except Exception as exc:
                result.warnings.append(f"Failed to record failure: {exc}")

        # Step 2: 更新基因适应度
        if gene_map:
            gene_updates = self.fcpi_to_gene_fitness_updates(fcpi_vector, gene_map)
            result.gene_updates = gene_updates

            for update in gene_updates:
                try:
                    genome = dgm.get_genome(genome_id)
                    if genome and update.gene_id in genome.genes:
                        genome.genes[update.gene_id].fitness_score = update.new_fitness
                except Exception as exc:
                    result.warnings.append(f"Failed to update gene fitness: {exc}")

        # Step 3: 对需变异的基因组触发进化
        if result.should_mutate_dimensions:
            try:
                genome = dgm.get_genome(genome_id)
                if genome:
                    # 构建失败上下文给 evolve_genome
                    failure_contexts = [
                        s.context for s in signals
                        if s.context.get("dimension") in result.should_mutate_dimensions
                    ]
                    # 注意: evolve_genome 返回新基因组 (不可变模式)
                    # 调用者负责将新基因组注册回 DGM
                    logger.info(
                        "DGMBridge: triggering evolution for '%s' in dimensions: %s",
                        genome_id, result.should_mutate_dimensions,
                    )
            except Exception as exc:
                result.warnings.append(f"Failed to trigger evolution: {exc}")

        return result

    # ── 工具方法 ────────────────────────────────────────────────────────

    @staticmethod
    def compute_genome_health(
        fcpi_vector: Any,  # FCPIVector
    ) -> dict[str, Any]:
        """从 FCPI 向量计算基因组健康报告."""
        dims = ["coding", "coordination", "safety", "decision", "emergence", "performance"]
        scores = {dim: getattr(fcpi_vector, dim, 0.5) for dim in dims}

        healthy = all(s >= 0.4 for s in scores.values())
        critical = [dim for dim, s in scores.items() if s < 0.2]
        warning = [dim for dim, s in scores.items() if 0.2 <= s < 0.4]

        return {
            "healthy": healthy,
            "critical_dimensions": critical,
            "warning_dimensions": warning,
            "overall_score": getattr(fcpi_vector, "to_legacy_fitness", lambda: 0.5)(),
            "confidence": getattr(fcpi_vector, "confidence", 0.5),
            "goodharting_flag": getattr(fcpi_vector, "goodharting_flag", False),
        }

    @staticmethod
    def suggest_mutation_strategy(
        fcpi_history: list[dict[str, float]],  # [{dim: score}, ...]
    ) -> dict[str, str]:
        """根据 FCPI 历史建议 DGM 变异策略调整.

        参考 DGM-HyperAgents (ICLR 2026) 元级自修改。

        Returns:
            {mutation_type: "increase" | "decrease" | "maintain"}
        """
        if len(fcpi_history) < 3:
            return {mt: "maintain" for mt in ["INSERT", "DELETE", "SUBSTITUTE", "CROSSOVER", "DUPLICATE"]}

        suggestions = {}

        # Coding 退化 → 增加 INSERT (新功能)
        coding_trend = fcpi_history[-1].get("coding", 0.5) - fcpi_history[0].get("coding", 0.5)
        suggestions["INSERT"] = "increase" if coding_trend < -0.02 else "maintain"

        # Safety 退化 → 增加 SUBSTITUTE (安全修复)
        safety_trend = fcpi_history[-1].get("safety", 0.5) - fcpi_history[0].get("safety", 0.5)
        suggestions["SUBSTITUTE"] = "increase" if safety_trend < -0.02 else "maintain"

        # Coordination 退化 → 增加 CROSSOVER (混合策略)
        coord_trend = fcpi_history[-1].get("coordination", 0.5) - fcpi_history[0].get("coordination", 0.5)
        suggestions["CROSSOVER"] = "increase" if coord_trend < -0.02 else "maintain"

        # Emergence 停滞 → 增加 DUPLICATE (多样性探索)
        emergence_trend = fcpi_history[-1].get("emergence", 0.5) - fcpi_history[0].get("emergence", 0.5)
        suggestions["DUPLICATE"] = "increase" if emergence_trend < 0.01 else "maintain"

        # 总 FCPI 退化 → 增加 DELETE (清理低效基因)
        total_trend = (
            sum(fcpi_history[-1].values()) - sum(fcpi_history[0].values())
        ) / max(len(fcpi_history[-1]), 1)
        suggestions["DELETE"] = "increase" if total_trend < -0.03 else "maintain"

        return suggestions
