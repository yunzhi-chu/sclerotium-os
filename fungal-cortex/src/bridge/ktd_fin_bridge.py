"""KTD-Fin Bridge — Training/Test field isolation + Barra 7-factor attribution.

KTD-Fin (Kensho Training Domain - Finance) enforces a strict separation between
training and testing Stigmergy fields through an impermeable membrane.

Key concepts:
- 不可渗透膜 (Impermeable membrane): No information leakage from test → training
- Barra 7-factor attribution: Market, Size, Value, Momentum, Quality, Volatility, Growth
- Risk decomposition: Total risk = Σ(factor_exposure_i × factor_return_i)² + specific_risk²
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger

BARRA_FACTORS = [
    "market",     # β: Market beta
    "size",       # Market capitalization
    "value",      # Book-to-price ratio
    "momentum",   # 12-month price momentum
    "quality",    # ROE, earnings quality
    "volatility", # Historical volatility
    "growth",     # Earnings/sales growth
]


@dataclass
class BarraAttribution:
    """Barra 7-factor risk attribution result."""

    factor_exposures: dict[str, float]  # Factor name → exposure
    factor_returns: dict[str, float]  # Factor name → return contribution
    factor_risks: dict[str, float]  # Factor name → risk contribution
    specific_risk: float  # Idiosyncratic risk
    total_risk: float
    r_squared: float  # Fraction of variance explained by factors
    timestamp: float = field(default_factory=time.time)

    @property
    def systematic_risk(self) -> float:
        return self.total_risk - self.specific_risk


@dataclass
class MembraneState:
    """State of the impermeable membrane between training and test fields."""

    training_field_id: str
    test_field_id: str
    leakage_detected: bool = False
    leakage_count: int = 0
    last_checked: float = field(default_factory=time.time)
    integrity_score: float = 1.0  # 1.0 = perfect separation


class KTDFinBridge:
    """KTD-Fin bridge enforcing training/test separation.

    The bridge manages two isolated Stigmergy fields:
    1. Training field: Where strategies learn and adapt
    2. Test field: Where strategies are evaluated (no parameter updates)

    The impermeable membrane between them:
    - Allows: Strategy DNA → Test field (one-way deployment)
    - Blocks: Test results → Training parameters (prevents overfitting)
    - Records: All cross-membrane events for audit

    Barra attribution decomposes strategy returns into 7 systematic factors
    plus idiosyncratic (alpha) returns.
    """

    def __init__(self, training_field_id: str = "train", test_field_id: str = "test") -> None:
        self._membrane = MembraneState(
            training_field_id=training_field_id,
            test_field_id=test_field_id,
        )
        self._logger = CortexLogger("ktd_fin_bridge")
        self._attributions: list[BarraAttribution] = []
        self._deployed_strategies: dict[str, float] = {}  # strategy_id → deployment_time

    def deploy_to_test(self, strategy_id: str) -> bool:
        """Deploy a strategy from training to test field (one-way).

        This is the ONLY allowed cross-membrane operation:
        Training → Test (strategy DNA only, no parameter feedback)
        """
        if self._membrane.leakage_detected:
            self._logger.warn("deploy_blocked_leakage", strategy_id=strategy_id)
            return False

        self._deployed_strategies[strategy_id] = time.time()
        self._logger.info("strategy_deployed_to_test", strategy_id=strategy_id, active_deployments=len(self._deployed_strategies))
        return True

    def check_leakage(self, training_params: dict[str, float], test_results: dict[str, float]) -> bool:
        """Check for information leakage from test → training.

        Detects: correlation between test result changes and training parameter updates.
        High correlation → potential leakage (in-sample overfitting signal).
        """
        if len(training_params) < 2 or len(test_results) < 2:
            return False

        # Simple correlation check: if param changes align with test result changes
        param_changes = list(training_params.values())
        result_changes = list(test_results.values())

        correlation = self._pearson_correlation(param_changes, result_changes)
        if abs(correlation) > 0.7:
            self._membrane.leakage_detected = True
            self._membrane.leakage_count += 1
            self._membrane.integrity_score = max(0.0, self._membrane.integrity_score - 0.2)
            self._logger.warn("leakage_detected", correlation=correlation, integrity=self._membrane.integrity_score)
            return True

        self._membrane.integrity_score = min(1.0, self._membrane.integrity_score + 0.01)
        self._membrane.last_checked = time.time()
        return False

    def compute_barra_attribution(
        self,
        strategy_returns: list[float],
        factor_exposures: dict[str, list[float]],
        factor_returns: dict[str, float],
    ) -> BarraAttribution:
        """Compute Barra 7-factor risk and return attribution.

        Args:
            strategy_returns: Time series of strategy returns
            factor_exposures: Each factor's exposure time series
            factor_returns: Each factor's return over the period
        """
        exposures: dict[str, float] = {}
        risks: dict[str, float] = {}
        factor_contrib: dict[str, float] = {}

        total_variance = self._variance(strategy_returns)
        explained_variance = 0.0

        for factor in BARRA_FACTORS:
            if factor not in factor_exposures or factor not in factor_returns:
                continue

            exp_series = factor_exposures[factor]
            avg_exposure = sum(exp_series) / max(len(exp_series), 1)
            exposures[factor] = avg_exposure

            ret = factor_returns.get(factor, 0.0)
            factor_contrib[factor] = avg_exposure * ret

            risk = (avg_exposure ** 2) * self._variance(exp_series)
            risks[factor] = risk
            explained_variance += risk

        specific_risk = max(0.0, total_variance - explained_variance)
        total_risk = math.sqrt(total_variance) if total_variance > 0 else 0.0

        r_squared = explained_variance / max(total_variance, 1e-10)
        r_squared = min(r_squared, 1.0)

        attribution = BarraAttribution(
            factor_exposures=exposures,
            factor_returns=factor_contrib,
            factor_risks=risks,
            specific_risk=math.sqrt(specific_risk),
            total_risk=total_risk,
            r_squared=r_squared,
        )
        self._attributions.append(attribution)
        return attribution

    @staticmethod
    def _variance(values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        return sum((v - mean) ** 2 for v in values) / (len(values) - 1)

    @staticmethod
    def _pearson_correlation(x: list[float], y: list[float]) -> float:
        n = min(len(x), len(y))
        if n < 2:
            return 0.0
        mean_x = sum(x[:n]) / n
        mean_y = sum(y[:n]) / n
        cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        var_x = sum((xi - mean_x) ** 2 for xi in x[:n])
        var_y = sum((yi - mean_y) ** 2 for yi in y[:n])
        denom = math.sqrt(var_x * var_y)
        return cov / denom if denom > 1e-10 else 0.0

    @property
    def membrane_integrity(self) -> float:
        return self._membrane.integrity_score

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "membrane_integrity": self._membrane.integrity_score,
            "leakage_detected": self._membrane.leakage_detected,
            "leakage_count": self._membrane.leakage_count,
            "deployed_strategies": len(self._deployed_strategies),
            "attributions_computed": len(self._attributions),
            "barra_factors": BARRA_FACTORS,
        }
