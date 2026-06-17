"""Risk Gate — L6 5 safety gates with three-faction risk control.

The 5 safety gates (from AGENT.md L6 three-faction risk control):
1. Position Limit Gate: Max single position ≤ faction threshold
2. Stop-Loss Gate: Trailing stop based on max drawdown
3. Volatility Gate: Position sizing inversely proportional to volatility
4. Correlation Gate: Max correlation between positions
5. Concentration Gate: Max sector/exchange concentration

Three factions (L6派系风控):
- AGGRESSIVE (激进派): Higher limits (退学炒股/明王 style)
- CONSERVATIVE (保守派): Lower limits (炒股养家/乔帮主 style)
- NEUTRAL (中性派): Balanced limits (章盟主/龙飞虎 style)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class RiskFaction(Enum):
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"
    NEUTRAL = "neutral"


class GateResult(Enum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class RiskGateResult:
    """Result from a single risk gate check."""

    gate_name: str
    result: GateResult
    faction: RiskFaction
    current_value: float
    limit: float
    reason: str = ""
    recommendation: str = ""


class RiskGate:
    """5 safety gates with faction-specific thresholds.

    Each gate can be in one of three states:
    - PASS: Within safe limits
    - WARN: Approaching limit (position reduced but allowed)
    - BLOCK: Exceeds limit (trade rejected)

    The three factions provide different perspectives:
    - Aggressive: Willing to take more risk, higher limits
    - Conservative: Prioritizes capital preservation, lower limits
    - Neutral: Balanced approach, moderate limits
    """

    # Faction-specific default thresholds
    FACTION_THRESHOLDS: dict[RiskFaction, dict[str, float]] = {
        RiskFaction.AGGRESSIVE: {
            "max_position_pct": 0.25,
            "max_drawdown_pct": 0.30,
            "max_volatility": 0.50,
            "max_correlation": 0.80,
            "max_sector_concentration": 0.50,
        },
        RiskFaction.NEUTRAL: {
            "max_position_pct": 0.15,
            "max_drawdown_pct": 0.20,
            "max_volatility": 0.35,
            "max_correlation": 0.65,
            "max_sector_concentration": 0.35,
        },
        RiskFaction.CONSERVATIVE: {
            "max_position_pct": 0.08,
            "max_drawdown_pct": 0.10,
            "max_volatility": 0.20,
            "max_correlation": 0.50,
            "max_sector_concentration": 0.20,
        },
    }

    def __init__(self, faction: RiskFaction = RiskFaction.NEUTRAL, overrides: dict[str, float] | None = None) -> None:
        self._faction = faction
        self._thresholds = dict(self.FACTION_THRESHOLDS[faction])
        if overrides:
            self._thresholds.update(overrides)
        self._logger = CortexLogger("risk_gate", faction.value)
        self._gate_history: list[RiskGateResult] = []
        self._total_checks = 0
        self._blocks = 0

    def check_position_limit(self, position_size_pct: float, portfolio_value: float) -> RiskGateResult:
        """Gate 1: Single position size limit."""
        limit = self._thresholds["max_position_pct"]
        result = self._evaluate(position_size_pct, limit, "position_limit")
        self._record(result)
        return result

    def check_stop_loss(self, current_drawdown_pct: float, entry_price: float, current_price: float) -> RiskGateResult:
        """Gate 2: Stop-loss based on drawdown from entry."""
        limit = self._thresholds["max_drawdown_pct"]
        result = self._evaluate(current_drawdown_pct, limit, "stop_loss")
        self._record(result)
        return result

    def check_volatility(self, annualized_volatility: float) -> RiskGateResult:
        """Gate 3: Position sizing inversely proportional to volatility."""
        limit = self._thresholds["max_volatility"]
        result = self._evaluate(annualized_volatility, limit, "volatility")
        self._record(result)
        return result

    def check_correlation(self, avg_pairwise_correlation: float) -> RiskGateResult:
        """Gate 4: Maximum pairwise position correlation."""
        limit = self._thresholds["max_correlation"]
        result = self._evaluate(avg_pairwise_correlation, limit, "correlation")
        self._record(result)
        return result

    def check_concentration(self, max_sector_weight: float) -> RiskGateResult:
        """Gate 5: Maximum sector/exchange concentration."""
        limit = self._thresholds["max_sector_concentration"]
        result = self._evaluate(max_sector_weight, limit, "concentration")
        self._record(result)
        return result

    def check_all(
        self,
        position_pct: float,
        drawdown_pct: float,
        volatility: float,
        correlation: float,
        concentration: float,
    ) -> list[RiskGateResult]:
        """Run all 5 gates. Returns list of results."""
        self._total_checks += 1
        results = [
            self.check_position_limit(position_pct, 0),
            RiskGateResult("stop_loss", self._evaluate_gate(drawdown_pct, self._thresholds["max_drawdown_pct"]), self._faction, drawdown_pct, self._thresholds["max_drawdown_pct"]),
            RiskGateResult("volatility", self._evaluate_gate(volatility, self._thresholds["max_volatility"]), self._faction, volatility, self._thresholds["max_volatility"]),
            RiskGateResult("correlation", self._evaluate_gate(correlation, self._thresholds["max_correlation"]), self._faction, correlation, self._thresholds["max_correlation"]),
            RiskGateResult("concentration", self._evaluate_gate(concentration, self._thresholds["max_sector_concentration"]), self._faction, concentration, self._thresholds["max_sector_concentration"]),
        ]
        for r in results:
            self._record(r)
        return results

    def _evaluate(self, value: float, limit: float, gate_name: str) -> RiskGateResult:
        """Evaluate a value against its limit."""
        result = self._evaluate_gate(value, limit)
        return RiskGateResult(
            gate_name=gate_name,
            result=result,
            faction=self._faction,
            current_value=value,
            limit=limit,
            reason=f"{gate_name}: {value:.3f} vs limit {limit:.3f}" if result != GateResult.PASS else "",
            recommendation=self._recommendation(gate_name, value, limit, result),
        )

    @staticmethod
    def _evaluate_gate(value: float, limit: float) -> GateResult:
        if value <= limit * 0.7:
            return GateResult.PASS
        if value <= limit:
            return GateResult.WARN
        return GateResult.BLOCK

    @staticmethod
    def _recommendation(gate_name: str, value: float, limit: float, result: GateResult) -> str:
        if result == GateResult.PASS:
            return f"{gate_name}: within limits"
        if result == GateResult.WARN:
            return f"{gate_name}: approaching limit, reduce position"
        return f"{gate_name}: limit exceeded, close position"

    def _record(self, result: RiskGateResult) -> None:
        self._gate_history.append(result)
        if result.result == GateResult.BLOCK:
            self._blocks += 1
        if len(self._gate_history) > 1000:
            self._gate_history = self._gate_history[-500:]

    def set_faction(self, faction: RiskFaction) -> None:
        """Switch to a different risk faction."""
        self._faction = faction
        self._thresholds = dict(self.FACTION_THRESHOLDS[faction])
        self._logger.info("faction_changed", faction=faction.value)

    def set_threshold(self, name: str, value: float) -> None:
        """Override a specific threshold."""
        self._thresholds[name] = value

    @property
    def faction(self) -> RiskFaction:
        return self._faction

    @property
    def stats(self) -> dict[str, Any]:
        recent = self._gate_history[-50:] if self._gate_history else []
        return {
            "faction": self._faction.value,
            "thresholds": dict(self._thresholds),
            "total_checks": self._total_checks,
            "total_blocks": self._blocks,
            "recent_pass_rate": sum(1 for r in recent if r.result == GateResult.PASS) / max(len(recent), 1),
        }
