"""Neutrosophic Validator — 真/假/不确定三段验证 (L3)。

生命体的"判断能力" — 不只看"对或错"，
而是评估: 有多大可能是真的? 多大可能是假的? 多大程度不确定?

三段值 (T, F, I):
  - T (Truth): 为真的程度 [0, 1]
  - F (Falsity): 为假的程度 [0, 1]
  - I (Indeterminacy): 不确定的程度 [0, 1]
  - 约束: T + F + I ≤ 3 (中智逻辑)

使用方式:
    validator = NeutrosophicValidator()
    result = validator.validate(
        claim="用户喜欢在深夜工作",
        evidence_for=["连续3天23:00后活跃"],
        evidence_against=["周末从未深夜工作"],
    )
    print(f"真={result.T}, 假={result.F}, 不确定={result.I}")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.neutrosophic")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class NeutrosophicResult:
    """中智逻辑评估结果。"""
    claim: str
    T: float = 0.33              # 为真的程度 [0, 1]
    F: float = 0.33              # 为假的程度 [0, 1]
    I: float = 0.34              # 不确定的程度 [0, 1]
    verdict: str = "uncertain"   # "true" / "false" / "uncertain"
    confidence: float = 0.0      # 整体置信度
    timestamp: float = field(default_factory=time.time)

    @property
    def is_true(self) -> bool:
        return self.T > self.F and self.T > self.I

    @property
    def is_false(self) -> bool:
        return self.F > self.T and self.F > self.I

    @property
    def is_uncertain(self) -> bool:
        return self.I >= self.T and self.I >= self.F


# ═══════════════════════════════════════════════════════════════
# NeutrosophicValidator
# ═══════════════════════════════════════════════════════════════

class NeutrosophicValidator:
    """中智逻辑三段验证器。

    使用方式:
        validator = NeutrosophicValidator()
        result = validator.validate(
            claim="用户的技术栈正在从Python迁移到TypeScript",
            evidence_for=["最近10个文件中有7个.ts", "ts依赖增加了50%"],
            evidence_against=["核心模块仍是.py", "最近还提交了新的.py文件"],
        )
    """

    def __init__(self) -> None:
        self._history: list[NeutrosophicResult] = []

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def validate(
        self,
        claim: str,
        evidence_for: list[str] | None = None,
        evidence_against: list[str] | None = None,
        unknowns: list[str] | None = None,
    ) -> NeutrosophicResult:
        """中智逻辑三段验证。

        Args:
            claim: 待验证的声明
            evidence_for: 支持证据列表
            evidence_against: 反对证据列表
            unknowns: 不确定因素列表

        Returns:
            NeutrosophicResult
        """
        ev_for = evidence_for or []
        ev_against = evidence_against or []
        unk = unknowns or []

        n_for = len(ev_for)
        n_against = len(ev_against)
        n_unk = len(unk)
        total = n_for + n_against + n_unk

        if total == 0:
            result = NeutrosophicResult(
                claim=claim, T=0.33, F=0.33, I=0.34,
                verdict="uncertain", confidence=0.0,
            )
            self._history.append(result)
            return result

        # 计算三段值
        base = max(total, 1)
        T = min(1.0, n_for / base + 0.1)
        F = min(1.0, n_against / base + 0.1)
        I = max(0.0, 1.0 - abs(T - F))

        # 基于证据质量调整
        if ev_for:
            avg_quality = self._estimate_quality(ev_for)
            T *= (0.5 + avg_quality * 0.5)
        if ev_against:
            avg_quality = self._estimate_quality(ev_against)
            F *= (0.5 + avg_quality * 0.5)

        # 裁决
        if T > F + 0.2:
            verdict = "true"
        elif F > T + 0.2:
            verdict = "false"
        else:
            verdict = "uncertain"

        confidence = max(T, F) if verdict != "uncertain" else (1.0 - I)

        result = NeutrosophicResult(
            claim=claim,
            T=round(T, 3), F=round(F, 3), I=round(I, 3),
            verdict=verdict, confidence=round(confidence, 3),
        )
        self._history.append(result)
        if len(self._history) > 200:
            self._history = self._history[-200:]
        return result

    def get_history(self, limit: int = 20) -> list[NeutrosophicResult]:
        return self._history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        if not self._history:
            return {"total": 0}
        true_count = sum(1 for r in self._history if r.verdict == "true")
        return {
            "total": len(self._history),
            "true_rate": round(true_count / len(self._history), 3),
            "avg_confidence": round(
                sum(r.confidence for r in self._history) / len(self._history), 3
            ),
        }

    @staticmethod
    def _estimate_quality(evidence: list[str]) -> float:
        """简单评估证据质量 (基于长度和关键词)。"""
        if not evidence:
            return 0.5
        scores = []
        for e in evidence:
            score = 0.3
            # 具体数字 → 高质量
            if any(c.isdigit() for c in e):
                score += 0.2
            # 有时间信息 → 高质量
            if any(kw in e for kw in ["天", "小时", "次", "最近", "年份"]):
                score += 0.1
            # 长度适中 → 中质量
            if 10 < len(e) < 200:
                score += 0.1
            scores.append(min(1.0, score))
        return sum(scores) / len(scores)
