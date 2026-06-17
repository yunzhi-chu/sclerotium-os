"""Portfolio Manager — L7 portfolio decision + position sizing.

L7 is the final layer of the cognitive pipeline where:
- L0-L6 analysis is synthesized into actionable allocation decisions
- Position sizing is computed based on risk gate outputs
- Portfolio rebalancing is triggered on schedule or drift
- Three-faction risk views are aggregated into a consensus allocation

The portfolio manager doesn't execute trades — it generates allocation
decisions that are passed to the risk gates for final validation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from src.trading.risk_gate import RiskFaction, RiskGate, RiskGateResult
from src.utils.logging import CortexLogger


@dataclass
class Position:
    """A single portfolio position."""

    symbol: str
    market: str
    quantity: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0
    sector: str = ""
    weight: float = 0.0  # Fraction of portfolio
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    signal_strength: float = 0.0  # 0-1, from L5 trading layer

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def pnl_pct(self) -> float:
        cost_basis = self.quantity * self.avg_cost
        return (self.market_value - cost_basis) / max(cost_basis, 1e-10)


@dataclass
class PortfolioState:
    """Complete portfolio snapshot."""

    positions: dict[str, Position] = field(default_factory=dict)
    total_value: float = 0.0
    cash: float = 0.0
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    position_count: int = 0
    sector_weights: dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class AllocationDecision:
    """A single position allocation decision from L7."""

    symbol: str
    action: str  # buy, sell, hold, reduce, increase
    target_weight: float
    current_weight: float = 0.0
    confidence: float = 0.0
    reason: str = ""
    risk_gate_results: list[RiskGateResult] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class PortfolioManager:
    """L7: Portfolio decision and allocation management.

    Key functions:
    - update_portfolio(): Recalculate portfolio state from current prices
    - generate_allocations(): Produce allocation decisions from signals
    - rebalance(): Generate rebalancing trades to target weights
    - aggregate_factions(): Combine three-faction views into consensus
    """

    def __init__(
        self,
        initial_cash: float = 1_000_000.0,
        max_positions: int = 50,
        max_single_position: float = 0.25,
        rebalance_interval_hours: int = 24,
    ) -> None:
        self._state = PortfolioState(cash=initial_cash, total_value=initial_cash)
        self._max_positions = max_positions
        self._max_single_position = max_single_position
        self._rebalance_interval = rebalance_interval_hours * 3600
        self._last_rebalance: float = 0.0
        self._logger = CortexLogger("portfolio_manager")
        self._decisions: list[AllocationDecision] = []
        self._initial_cash = initial_cash

    def update_position(self, symbol: str, quantity: int, avg_cost: float, current_price: float, sector: str = "", market: str = "cn") -> Position:
        """Update or create a position."""
        if symbol in self._state.positions:
            pos = self._state.positions[symbol]
            new_total_cost = pos.quantity * pos.avg_cost + quantity * avg_cost
            pos.quantity += quantity
            pos.avg_cost = new_total_cost / max(pos.quantity, 1)
            pos.current_price = current_price
            pos.sector = sector
            pos.market = market
        else:
            pos = Position(
                symbol=symbol,
                market=market,
                quantity=quantity,
                avg_cost=avg_cost,
                current_price=current_price,
                sector=sector,
            )
            self._state.positions[symbol] = pos

        self._recalculate_state()
        return pos

    def close_position(self, symbol: str, exit_price: float) -> Position | None:
        """Close a position and realize P&L."""
        pos = self._state.positions.pop(symbol, None)
        if pos is None:
            return None
        pos.realized_pnl = pos.quantity * (exit_price - pos.avg_cost)
        self._state.cash += pos.market_value
        self._recalculate_state()
        return pos

    def generate_allocation(
        self,
        symbol: str,
        signal_strength: float,
        target_weight: float,
        risk_gates: list[RiskGate] | None = None,
        confidence: float = 0.5,
        reason: str = "",
    ) -> AllocationDecision:
        """Generate an allocation decision from signal + risk gate inputs.

        Args:
            symbol: Trading symbol
            signal_strength: 0-1 signal from L5 trading layer
            target_weight: Desired portfolio weight (0-1)
            risk_gates: Risk gates to validate against
            confidence: Overall decision confidence (0-1)
            reason: Human-readable reason for the decision
        """
        current = self._state.positions.get(symbol)
        current_weight = current.weight if current else 0.0

        # Determine action
        if abs(target_weight - current_weight) < 0.001:
            action = "hold"
        elif target_weight > current_weight:
            action = "increase" if current_weight > 0 else "buy"
        elif target_weight == 0.0:
            action = "sell"
        else:
            action = "reduce"

        # Cap target weight
        target_weight = min(target_weight, self._max_single_position)

        # Check against position limit
        if target_weight > 0 and len(self._state.positions) >= self._max_positions and action == "buy":
            action = "hold"
            reason += " [max_positions_reached]"

        # Run risk gate checks
        gate_results: list[RiskGateResult] = []
        if risk_gates:
            for gate in risk_gates:
                if action in ("buy", "increase"):
                    result = gate.check_position_limit(target_weight, self._state.total_value)
                    gate_results.append(result)
                    if result.result.value == "block":
                        action = "hold"
                        reason += f" [blocked: {result.gate_name}]"

        decision = AllocationDecision(
            symbol=symbol,
            action=action,
            target_weight=target_weight,
            current_weight=current_weight,
            confidence=confidence * signal_strength,
            reason=reason,
            risk_gate_results=gate_results,
        )
        self._decisions.append(decision)
        if len(self._decisions) > 1000:
            self._decisions = self._decisions[-500:]

        self._logger.debug("allocation_decision", symbol=symbol, action=action, target_weight=round(target_weight, 4))
        return decision

    def aggregate_factions(
        self,
        aggressive_allocation: dict[str, float],
        neutral_allocation: dict[str, float],
        conservative_allocation: dict[str, float],
    ) -> dict[str, float]:
        """Aggregate three-faction risk views into consensus allocation.

        Weight: Neutral=0.5, Aggressive=0.25, Conservative=0.25
        """
        consensus: dict[str, float] = {}
        all_symbols = set(aggressive_allocation) | set(neutral_allocation) | set(conservative_allocation)

        for symbol in all_symbols:
            consensus[symbol] = (
                aggressive_allocation.get(symbol, 0.0) * 0.25
                + neutral_allocation.get(symbol, 0.0) * 0.50
                + conservative_allocation.get(symbol, 0.0) * 0.25
            )
        return consensus

    def rebalance(self, target_weights: dict[str, float]) -> list[AllocationDecision]:
        """Generate rebalancing decisions to reach target weights."""
        self._last_rebalance = time.time()
        decisions: list[AllocationDecision] = []

        current_weights = {
            s: p.weight for s, p in self._state.positions.items()
        } if self._state.total_value > 0 else {}

        all_symbols = set(current_weights) | set(target_weights)
        for symbol in all_symbols:
            target = target_weights.get(symbol, 0.0)
            current = current_weights.get(symbol, 0.0)
            decision = self.generate_allocation(
                symbol=symbol,
                signal_strength=1.0,
                target_weight=target,
                reason=f"rebalance: {current:.3f} → {target:.3f}",
            )
            decisions.append(decision)

        self._logger.info("portfolio_rebalanced", symbols=len(all_symbols), decisions=len(decisions))
        return decisions

    def _recalculate_state(self) -> None:
        """Recalculate portfolio metrics from positions."""
        total_market_value = sum(p.market_value for p in self._state.positions.values())
        self._state.total_value = self._state.cash + total_market_value
        self._state.position_count = len(self._state.positions)
        self._state.total_pnl = self._state.total_value - self._initial_cash
        self._state.total_pnl_pct = self._state.total_pnl / max(self._initial_cash, 1)

        # Update position weights
        for pos in self._state.positions.values():
            pos.weight = pos.market_value / max(self._state.total_value, 1e-10)
            pos.unrealized_pnl = pos.quantity * (pos.current_price - pos.avg_cost)

        # Sector weights
        sectors: dict[str, float] = {}
        for pos in self._state.positions.values():
            if pos.sector:
                sectors[pos.sector] = sectors.get(pos.sector, 0.0) + pos.market_value
        for sector in sectors:
            sectors[sector] /= max(self._state.total_value, 1e-10)
        self._state.sector_weights = sectors

    def get_state(self) -> dict[str, Any]:
        """Return portfolio state as dict for WebSocket streaming."""
        return {
            "positions": [
                {
                    "symbol": p.symbol, "quantity": p.quantity, "avg_cost": p.avg_cost,
                    "current_price": p.current_price, "market_value": p.market_value,
                    "pnl_pct": p.pnl_pct, "sector": p.sector, "weight": p.weight,
                }
                for p in self._state.positions.values()
            ],
            "pnl_history": [],
            "signals": [],
            "total_value": self._state.total_value,
            "cash": self._state.cash,
            "total_pnl_pct": self._state.total_pnl_pct,
        }

    @property
    def state(self) -> PortfolioState:
        return self._state

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_value": round(self._state.total_value, 2),
            "cash": round(self._state.cash, 2),
            "position_count": self._state.position_count,
            "total_pnl_pct": round(self._state.total_pnl_pct, 4),
            "sector_weights": self._state.sector_weights,
            "max_positions": self._max_positions,
            "max_single_position": self._max_single_position,
        }
