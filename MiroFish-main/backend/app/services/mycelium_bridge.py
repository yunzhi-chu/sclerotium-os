"""MyceliumBridge — MiroFish FCPI → Mycelium AGI v4.0 适应度注入.

将 EmergentFitnessExtractor 的六维 FCPI 向量映射为
Mycelium SelfEvolutionLoop.evolve() 期望的 performance_data 格式,
替代原有的硬编码适应度函数 (0.5*sharpe + 0.3*consistency + 0.2*diversity)。

映射关系:
    FCPI.total → sharpe (风险调整后综合能力)
    FCPI.confidence → consistency (评估置信度)
    FCPI.emergence → diversity_contrib (涌现多样性贡献)

扩展字段 (_fcpi_vector):
    完整的六维 FCPI 向量附加在 performance_data 中,
    供 Mycelium 未来的多维适应度函数使用。

Usage:
    bridge = MyceliumBridge()
    extractor = EmergentFitnessExtractor()

    # 从各竞技场提取 FCPI
    extraction = extractor.extract(arena_results, genome_context)

    # 映射为 Mycelium 格式
    mycelium_data = bridge.to_mycelium_format(
        extraction.fcpi_vector, gene_id="genome_001"
    )

    # 注入 Mycelium SelfEvolutionLoop
    loop = SelfEvolutionLoop()
    report = loop.evolve(performance_data=mycelium_data)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class MyceliumPerformanceData:
    """Mycelium SelfEvolutionLoop 期望的单基因数据格式.

    映射自 FCPI 六维向量:
        sharpe            ← FCPI.total (0.25*coding + 0.25*coordination + ...)
        consistency       ← FCPI.confidence (PAC 统计置信度)
        diversity_contrib ← FCPI.emergence (涌现多样性贡献)
    """
    sharpe: float
    consistency: float
    diversity_contrib: float
    _fcpi_vector: dict[str, Any] = field(default_factory=dict)


@dataclass
class BridgeResult:
    """桥接结果 — 包含映射后的数据和元信息."""
    performance_data: dict[str, dict[str, float]]
    genes_processed: int
    mapping_quality: float  # 0-1, 映射质量评分
    warnings: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# MyceliumBridge
# ═══════════════════════════════════════════════════════════════════════════════


class MyceliumBridge:
    """MiroFish → Mycelium AGI v4.0 适应度桥接器.

    核心职责:
        1. 将 FCPIVector 映射为 Mycelium 兼容格式
        2. 批量处理多基因组的适应度映射
        3. 质量控制: 检测映射有效性,标记异常值
        4. 提供向后兼容的 (sharpe, consistency, diversity_contrib) 三元组
        5. 附加完整的六维 FCPI 向量供未来使用
    """

    # 默认 FCPI → Mycelium 权重 (可通过配置覆盖)
    DEFAULT_WEIGHTS = {
        "coding": 0.25,
        "coordination": 0.25,
        "safety": 0.15,
        "decision": 0.15,
        "emergence": 0.10,
        "performance": 0.10,
    }

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        """初始化桥接器.

        Args:
            weights: 自定义 FCPI 维度权重 (None = 使用默认)
        """
        self.weights = weights or dict(self.DEFAULT_WEIGHTS)

    # ── 核心 API ────────────────────────────────────────────────────────

    def to_mycelium_format(
        self,
        fcpi_vector: Any,  # FCPIVector (避免导入依赖)
        gene_id: str | None = None,
        include_extended: bool = True,
    ) -> dict[str, dict[str, float]]:
        """将单个 FCPI 向量映射为 Mycelium performance_data 格式.

        Args:
            fcpi_vector: FCPIVector 实例
            gene_id: 基因组 ID (None = 从 fcpi_vector 推断)
            include_extended: 是否包含 _fcpi_vector 扩展字段

        Returns:
            {gene_id: {sharpe, consistency, diversity_contrib, [_fcpi_vector]}}
        """
        gid = gene_id or getattr(fcpi_vector, "genome_id", "unknown")

        # 计算综合适应度 (向后兼容的 "sharpe" 映射)
        total = (
            self.weights["coding"] * getattr(fcpi_vector, "coding", 0.5)
            + self.weights["coordination"] * getattr(fcpi_vector, "coordination", 0.5)
            + self.weights["safety"] * getattr(fcpi_vector, "safety", 0.5)
            + self.weights["decision"] * getattr(fcpi_vector, "decision", 0.5)
            + self.weights["emergence"] * getattr(fcpi_vector, "emergence", 0.5)
            + self.weights["performance"] * getattr(fcpi_vector, "performance", 0.5)
        )

        # 置信度映射为 consistency
        confidence = getattr(fcpi_vector, "confidence", 0.5)

        # 涌现分数映射为 diversity_contrib
        emergence = getattr(fcpi_vector, "emergence", 0.5)

        data = {
            gid: {
                "sharpe": round(total, 4),
                "consistency": round(confidence, 4),
                "diversity_contrib": round(emergence, 4),
            }
        }

        if include_extended and hasattr(fcpi_vector, "to_dict"):
            data[gid]["_fcpi_vector"] = fcpi_vector.to_dict()

        return data

    def batch_to_mycelium(
        self,
        fcpi_vectors: dict[str, Any],  # {gene_id: FCPIVector}
        include_extended: bool = True,
    ) -> BridgeResult:
        """批量将多个 FCPI 向量映射为 Mycelium 格式.

        Args:
            fcpi_vectors: {gene_id: FCPIVector} 映射
            include_extended: 是否包含扩展字段

        Returns:
            BridgeResult 包含合并后的 performance_data
        """
        combined: dict[str, dict[str, float]] = {}
        warnings: list[str] = []
        genes_processed = 0

        for gene_id, fcpi in fcpi_vectors.items():
            try:
                mapped = self.to_mycelium_format(
                    fcpi, gene_id=gene_id, include_extended=include_extended,
                )
                combined.update(mapped)
                genes_processed += 1

                # 质量检查
                goodharting = getattr(fcpi, "goodharting_flag", False)
                if goodharting:
                    warnings.append(
                        f"Gene '{gene_id}' flagged for Goodharting "
                        f"(FCPI total={mapped[gene_id]['sharpe']:.4f})"
                    )

                confidence = getattr(fcpi, "confidence", 0.0)
                if confidence < 0.3:
                    warnings.append(
                        f"Gene '{gene_id}' has low confidence ({confidence:.3f})"
                    )

            except Exception as exc:
                logger.exception("Failed to map gene '%s'", gene_id)
                warnings.append(f"Gene '{gene_id}' mapping failed: {exc}")
                # 使用默认值
                combined[gene_id] = {
                    "sharpe": 0.5,
                    "consistency": 0.5,
                    "diversity_contrib": 0.5,
                }

        mapping_quality = (
            genes_processed / max(len(fcpi_vectors), 1)
            if fcpi_vectors
            else 0.0
        )
        # 扣减警告影响
        mapping_quality *= max(0.0, 1.0 - len(warnings) * 0.1)

        logger.info(
            "MyceliumBridge: mapped %d genes (quality=%.2f, warnings=%d)",
            genes_processed, mapping_quality, len(warnings),
        )

        return BridgeResult(
            performance_data=combined,
            genes_processed=genes_processed,
            mapping_quality=mapping_quality,
            warnings=warnings,
        )

    def from_extraction_result(
        self,
        extraction: Any,  # ExtractionResult
        gene_id: str | None = None,
    ) -> dict[str, dict[str, float]]:
        """从 EmergentFitnessExtractor 的 ExtractionResult 直接映射.

        Args:
            extraction: EmergentFitnessExtractor.extract() 的返回值
            gene_id: 基因组 ID

        Returns:
            Mycelium 格式的 performance_data
        """
        fcpi = extraction.fcpi_vector
        result = self.to_mycelium_format(fcpi, gene_id=gene_id)

        # 添加 Goodharting 警告标记
        gid = gene_id or fcpi.genome_id
        if fcpi.goodharting_flag:
            result[gid]["_goodharting_flag"] = 1.0
            result[gid]["_goodharting_warnings"] = extraction.goodharting_warnings

        return result

    # ── 工具方法 ────────────────────────────────────────────────────────

    def compute_mycelium_sharpe(
        self,
        coding: float = 0.5,
        coordination: float = 0.5,
        safety: float = 0.5,
        decision: float = 0.5,
        emergence: float = 0.5,
        performance: float = 0.5,
    ) -> float:
        """直接从六维分数计算 Mycelium sharpe (便捷方法)."""
        return (
            self.weights["coding"] * coding
            + self.weights["coordination"] * coordination
            + self.weights["safety"] * safety
            + self.weights["decision"] * decision
            + self.weights["emergence"] * emergence
            + self.weights["performance"] * performance
        )

    def update_weights_from_meta_learning(
        self, fcpi_history: list[dict[str, float]]
    ) -> dict[str, float]:
        """根据 FCPI 历史趋势更新权重 (DGM-HyperAgents 风格).

        如果某维度持续退化 → 提升权重 (增加选择压力)
        如果某维度持续饱和 → 降低权重

        Args:
            fcpi_history: [{coding, coordination, ...}, ...] 历史 FCPI

        Returns:
            更新后的权重 dict
        """
        if len(fcpi_history) < 3:
            return dict(self.weights)

        for dim in self.weights:
            dim_values = [h.get(dim, 0.5) for h in fcpi_history[-5:]]
            if len(dim_values) < 2:
                continue

            trend = dim_values[-1] - dim_values[0]

            if trend < -0.05:  # 退化 → 提升权重
                self.weights[dim] = min(self.weights[dim] * 1.15, 0.40)
            elif abs(trend) < 0.01:  # 饱和 → 降低权重
                self.weights[dim] = max(self.weights[dim] * 0.95, 0.05)

        # 归一化
        total = sum(self.weights.values())
        if total > 0:
            for dim in self.weights:
                self.weights[dim] /= total

        return dict(self.weights)
