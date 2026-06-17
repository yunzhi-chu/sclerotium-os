"""L4 M4b: StrategyAutoValidator — "朊病毒PrP^Sc检测"(Prion Strain Detection) 策略验证器.

Biological Metaphor:
  朊病毒(Prion)检测——区分正常PrP^C(细胞型)和致病PrP^Sc(瘙痒病型):
  两者氨基酸序列相同, 但构象不同(α-helix vs β-sheet)
  如同两个策略代码相同但参数不同→截然不同的表现

  三个检测标准:
    1. 蛋白酶K抗性(正常PrP^C会被消化, PrP^Sc不会)→Sharpe阈值
    2. 刚果红染色(β-sheet特异性染色)→回撤阈值
    3. 感染性测试(是否能在动物模型中传播)→胜率阈值

Reference:
  Maury (2025), FEBS Letters; Igel-Egalon et al. (2019/2025)
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class ValidationStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class ValidationReport:
    """Validation report — like a prion strain typing result."""

    report_id: str
    strategy_name: str
    overall_status: ValidationStatus
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    overfit_score: float = 0.0
    recommendations: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


class StrategyAutoValidator:
    """Prion-detection-like strategy validation with three criteria.

    Config:
      - min_sharpe: minimum Sharpe ratio (PK resistance)
      - max_drawdown: maximum allowable drawdown (Congo red)
      - min_win_rate: minimum win rate (infectivity)
    """

    def __init__(
        self, min_sharpe: float = 0.5, max_drawdown: float = 0.15, min_win_rate: float = 0.45
    ) -> None:
        self._min_sharpe = min_sharpe
        self._max_drawdown = max_drawdown
        self._min_win_rate = min_win_rate
        self._reports: dict[str, ValidationReport] = {}
        self._logger = CortexLogger("strategy_validator")

    def validate(
        self, strategy_name: str, returns: list[float],
        benchmark_returns: list[float] | None = None,
    ) -> ValidationReport:
        """Run the three-prion-detection-test suite."""
        sharpe = self._compute_sharpe(returns)
        max_dd = self._compute_max_drawdown(returns)
        win_rate = sum(1 for r in returns if r > 0) / max(len(returns), 1)

        recommendations: list[str] = []
        failures = 0

        # Test 1: Protease K resistance (Sharpe)
        if sharpe < self._min_sharpe:
            failures += 1
            recommendations.append(f"Sharpe {sharpe:.2f} < {self._min_sharpe}. Improve risk-adjusted return.")

        # Test 2: Congo red staining (max drawdown)
        if max_dd > self._max_drawdown:
            failures += 1
            recommendations.append(f"MaxDD {max_dd:.1%} > {self._max_drawdown:.0%}. Add stop-loss protection.")

        # Test 3: Infectivity (win rate)
        if win_rate < self._min_win_rate:
            failures += 1
            recommendations.append(f"WinRate {win_rate:.1%} < {self._min_win_rate:.0%}. Improve signal accuracy.")

        # Overfitting: compare with benchmark
        overfit = 0.0
        if benchmark_returns:
            bench_sharpe = self._compute_sharpe(benchmark_returns)
            if sharpe > bench_sharpe * 3:
                overfit = 1.0
                recommendations.append("IS Sharpe >> benchmark — possible overfitting.")

        status = ValidationStatus.PASS if failures == 0 else (ValidationStatus.WARN if failures == 1 else ValidationStatus.FAIL)
        report = ValidationReport(
            report_id=self._gen_id(strategy_name),
            strategy_name=strategy_name,
            overall_status=status,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            win_rate=win_rate,
            overfit_score=overfit,
            recommendations=recommendations,
        )
        self._reports[report.report_id] = report
        return report

    def compare(self, reports: list[ValidationReport]) -> list[dict[str, Any]]:
        ranked = []
        for r in reports:
            score = r.sharpe_ratio * 0.4 + (1 - r.max_drawdown) * 0.3 + r.win_rate * 0.3 - r.overfit_score * 0.5
            ranked.append({"strategy": r.strategy_name, "status": r.overall_status.value, "score": round(score, 3)})
        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked

    @staticmethod
    def _compute_sharpe(returns: list[float], rf: float = 0.02) -> float:
        n = len(returns)
        if n < 2:
            return 0.0
        mean = sum(returns) / n
        excess = mean - rf / 252
        std = math.sqrt(sum((r - mean) ** 2 for r in returns) / (n - 1))
        return (excess / std) * math.sqrt(252) if std > 1e-10 else 0.0

    @staticmethod
    def _compute_max_drawdown(returns: list[float]) -> float:
        peak = float("-inf")
        max_dd = 0.0
        cum = 0.0
        for r in returns:
            cum += r
            peak = max(peak, cum)
            max_dd = max(max_dd, (peak - cum) / max(peak, 0.01))
        return max_dd

    @staticmethod
    def _gen_id(name: str) -> str:
        return hashlib.md5(f"{name}|{time.time()}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, int]:
        return {
            "reports": len(self._reports),
            "pass": sum(1 for r in self._reports.values() if r.overall_status == ValidationStatus.PASS),
            "fail": sum(1 for r in self._reports.values() if r.overall_status == ValidationStatus.FAIL),
        }
