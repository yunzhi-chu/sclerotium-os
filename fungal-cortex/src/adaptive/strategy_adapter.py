"""L0/L2b: StrategyAdapter — "甲状腺" (Thyroid Gland).

Biological Metaphor:
  甲状腺——根据TSH(促甲状腺激素)调节全身代谢速率(T3/T4)

  6体制×8策略基权重矩阵 = 甲状腺在不同环境温度下预设的代谢基线
  融合: 70%基权重(遗传预设) + 30%HyperNetwork动态(HPA调控)

  8类策略 = 8种代谢模式:
    multi_factor = 糖代谢(快速能量) / timing = 脂代谢(持续能量)
    arbitrage = 蛋白质代谢(结构修复) / dragon_head = 应急糖原分解
    small_cap = 微量元素代谢 / mean_reversion = 基础代谢
    momentum = 运动代谢 / event_driven = 应激代谢

Reference:
  Schuler et al. (2026), "Energy Allocation System", IJMS 27(3):1345
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class StrategyAllocation:
    """Weight allocation across 8 strategy types for a given regime."""

    regime_label: str
    weights: list[float]  # 8-dim strategy weight distribution
    confidence: float  # how confident the adapter is in this allocation
    base_contribution: float  # fraction from base weights (vs HyperNetwork)
    timestamp: float = field(default_factory=time.time)


class StrategyAdapter:
    """Regime-aware strategy weight adapter — the "thyroid" of the system.

    Maps regime distributions → strategy type weights using:
      - 70% base weight matrix (genetic preset — like inherent metabolic baseline)
      - 30% HyperNetwork dynamic modulation (HPA hormonal regulation)

    The 8 strategy types correspond to 8 metabolic modes:
      0: multi_factor   → glucose metabolism (fast energy)
      1: timing          → lipid metabolism (sustained energy)
      2: arbitrage       → protein metabolism (structural repair)
      3: dragon_head     → emergency glycogenolysis
      4: small_cap       → trace element metabolism
      5: mean_reversion  → basal metabolism
      6: momentum        → exercise metabolism
      7: event_driven    → stress metabolism
    """

    N_REGIMES = 6
    N_STRATEGIES = 8
    BASE_RATIO = 0.70  # 70% base weight, 30% HyperNetwork

    STRATEGY_NAMES = [
        "multi_factor", "timing", "arbitrage", "dragon_head",
        "small_cap", "mean_reversion", "momentum", "event_driven",
    ]

    REGIME_NAMES = [
        "trending_up", "trending_down", "high_volatility",
        "low_volatility", "sideways", "transition",
    ]

    def __init__(self) -> None:
        self._logger = CortexLogger("strategy_adapter")

        # Base weight matrix: 6 regimes × 8 strategies
        # These are the "genetic preset" metabolic baselines
        # Rows sum to 1 (like thyroid hormone levels sum to a regulatory target)
        self._base_weights: list[list[float]] = [
            # multi  timing  arb    dragon small  mean   mom    event
            [0.15,  0.15,  0.05,  0.10,  0.10,  0.05,  0.25,  0.15],  # trending_up
            [0.10,  0.20,  0.05,  0.20,  0.05,  0.10,  0.05,  0.25],  # trending_down
            [0.05,  0.15,  0.15,  0.05,  0.10,  0.15,  0.10,  0.25],  # high_volatility
            [0.15,  0.10,  0.10,  0.05,  0.20,  0.20,  0.10,  0.10],  # low_volatility
            [0.10,  0.10,  0.15,  0.05,  0.15,  0.20,  0.10,  0.15],  # sideways
            [0.15,  0.10,  0.10,  0.15,  0.10,  0.10,  0.15,  0.15],  # transition
        ]

        # Historical performance per strategy (for adaptive adjustment)
        self._performance_memory: dict[int, list[float]] = {
            i: [] for i in range(self.N_STRATEGIES)
        }

        self._last_allocation: StrategyAllocation | None = None
        self._call_count: int = 0

    # ── Weight Adaptation ─────────────────────────────────────────────

    def adapt(
        self,
        regime_distribution: list[float],
        hypernetwork_weights: list[float] | None = None,
    ) -> StrategyAllocation:
        """Compute strategy weight allocation for current regime.

        Args:
            regime_distribution: 6-dim regime probabilities [t_up, t_down, high_v, low_v, side, trans]
            hypernetwork_weights: 8-dim dynamic modulation from HyperNetwork (TSH-like)

        Returns:
            StrategyAllocation with final strategy weights
        """
        self._call_count += 1

        r = list(regime_distribution[:self.N_REGIMES])
        while len(r) < self.N_REGIMES:
            r.append(0.0)

        # 1. Base weights: weighted average across regimes
        base = [0.0] * self.N_STRATEGIES
        for i in range(self.N_STRATEGIES):
            for j in range(self.N_REGIMES):
                base[i] += r[j] * self._base_weights[j][i]

        # Normalize base weights
        base_total = sum(base)
        if base_total > 0:
            base = [w / base_total for w in base]

        # 2. HyperNetwork modulation (TSH→T3/T4 conversion)
        if hypernetwork_weights and len(hypernetwork_weights) >= self.N_STRATEGIES:
            hn = hypernetwork_weights[:self.N_STRATEGIES]
            hn_total = sum(hn)
            if hn_total > 0:
                hn = [w / hn_total for w in hn]
        else:
            hn = [1.0 / self.N_STRATEGIES] * self.N_STRATEGIES

        # 3. Fuse: 70% base + 30% HyperNetwork
        fused = [0.0] * self.N_STRATEGIES
        for i in range(self.N_STRATEGIES):
            fused[i] = self.BASE_RATIO * base[i] + (1 - self.BASE_RATIO) * hn[i]

        # Normalize
        total = sum(fused)
        if total > 0:
            fused = [w / total for w in fused]
        else:
            fused = [1.0 / self.N_STRATEGIES] * self.N_STRATEGIES

        # 4. Apply performance memory adjustment
        fused = self._apply_performance_bias(fused)

        # 5. Dominant strategy and confidence
        dominant = max(range(self.N_STRATEGIES), key=lambda i: fused[i])
        confidence = fused[dominant] / (sum(fused) / self.N_STRATEGIES)  # relative to uniform

        allocation = StrategyAllocation(
            regime_label=self._dominant_regime(r),
            weights=[round(w, 4) for w in fused],
            confidence=round(min(confidence / self.N_STRATEGIES, 1.0), 3),
            base_contribution=self.BASE_RATIO,
        )
        self._last_allocation = allocation

        self._logger.debug("strategy_adapted",
                          dominant=self.STRATEGY_NAMES[dominant],
                          confidence=round(confidence / self.N_STRATEGIES, 3))

        return allocation

    def record_performance(self, strategy_index: int, pnl: float) -> None:
        """Record strategy performance for adaptive memory.

        Like the thyroid remembering which metabolic modes work best
        under which conditions.
        """
        if 0 <= strategy_index < self.N_STRATEGIES:
            # Store normalized PnL contribution
            self._performance_memory[strategy_index].append(
                1.0 / (1.0 + math.exp(-pnl * 10))  # sigmoid normalize
            )
            # Keep last 252 (1 year)
            if len(self._performance_memory[strategy_index]) > 252:
                self._performance_memory[strategy_index] = \
                    self._performance_memory[strategy_index][-252:]

    def _apply_performance_bias(self, weights: list[float]) -> list[float]:
        """Slightly bias weights toward historically profitable strategies.

        Like the body naturally preferring metabolic pathways that
        have proven efficient.
        """
        perf_scores = [0.5] * self.N_STRATEGIES
        for i in range(self.N_STRATEGIES):
            history = self._performance_memory[i]
            if history:
                perf_scores[i] = sum(history) / len(history)

        # Small bias: ±5%
        bias_factor = 0.05
        biased = []
        for i in range(self.N_STRATEGIES):
            bias = (perf_scores[i] - 0.5) * 2 * bias_factor
            biased.append(weights[i] * (1.0 + bias))

        total = sum(biased)
        return [w / max(total, 1e-10) for w in biased]

    @staticmethod
    def _dominant_regime(regime_dist: list[float]) -> str:
        idx = max(range(len(regime_dist)), key=lambda i: regime_dist[i])
        return StrategyAdapter.REGIME_NAMES[idx] if idx < len(StrategyAdapter.REGIME_NAMES) else "unknown"

    def get_base_weights(self) -> dict[str, list[float]]:
        """Get the base weight matrix (for inspection)."""
        return {
            self.REGIME_NAMES[i]: [round(w, 4) for w in self._base_weights[i]]
            for i in range(self.N_REGIMES)
        }

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "call_count": self._call_count,
            "n_regimes": self.N_REGIMES,
            "n_strategies": self.N_STRATEGIES,
            "base_ratio": self.BASE_RATIO,
            "last_allocation": {
                "regime": self._last_allocation.regime_label if self._last_allocation else "none",
                "weights": self._last_allocation.weights if self._last_allocation else None,
                "confidence": self._last_allocation.confidence if self._last_allocation else 0.0,
            } if self._last_allocation else None,
            "performance_memory_size": {i: len(self._performance_memory[i]) for i in range(self.N_STRATEGIES)},
        }
