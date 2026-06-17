"""L4 M3c: CounterfactualEngine — "前额叶反事实思维"(Prefrontal Counterfactual) 反事实引擎.

Biological Metaphor:
  人类独有的反事实思维——"如果当时选了另一条路会怎样?"
  这是前额叶皮层的高级认知功能, 是决策后悔/学习的基础。

  create_scenario("如果当时是牛市..."):
    regime_override + strategy_blacklist + safety_gate_multiplier
    = 改变一个变量, 重新运行模拟

  run_counterfactual():
    对比: original_pnl vs cf_pnl → 变化分析
    = "如果我没有卖掉那只股票, 现在会多赚多少?"
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class Scenario:
    """A counterfactual scenario — "what if..." hypothesis."""

    scenario_id: str
    description: str
    overrides: dict[str, Any]  # variable → new value
    strategy_blacklist: list[str] = field(default_factory=list)
    safety_multiplier: float = 1.0
    created_at: float = field(default_factory=time.time)


@dataclass
class CounterfactualResult:
    """Result of a counterfactual simulation."""

    result_id: str
    scenario: Scenario
    original_pnl: float = 0.0
    counterfactual_pnl: float = 0.0
    delta_pnl: float = 0.0
    delta_pct: float = 0.0
    explanation: str = ""
    created_at: float = field(default_factory=time.time)


class CounterfactualEngine:
    """Prefrontal counterfactual reasoning — explores "what if" scenarios."""

    def __init__(self) -> None:
        self._scenarios: dict[str, Scenario] = {}
        self._results: dict[str, CounterfactualResult] = []
        self._logger = CortexLogger("counterfactual")

    def create_scenario(
        self, description: str, overrides: dict[str, Any],
        strategy_blacklist: list[str] | None = None,
        safety_multiplier: float = 1.0,
    ) -> Scenario:
        """Create a hypothetical scenario — change one variable."""
        scenario = Scenario(
            scenario_id=self._gen_id("scenario", description),
            description=description,
            overrides=overrides,
            strategy_blacklist=strategy_blacklist or [],
            safety_multiplier=safety_multiplier,
        )
        self._scenarios[scenario.scenario_id] = scenario
        return scenario

    def run_counterfactual(
        self, scenario: Scenario, original_pnl: float,
        simulator: Any | None = None,
    ) -> CounterfactualResult:
        """Run a counterfactual simulation. If simulator provided, use it; otherwise estimate."""
        if simulator:
            cf_pnl = simulator(scenario)
        else:
            # Simple estimation: apply safety multiplier, adjust for blacklisted strategies
            cf_pnl = original_pnl * scenario.safety_multiplier
            if scenario.strategy_blacklist:
                cf_pnl *= 0.9  # slightly worse without those strategies

        delta = cf_pnl - original_pnl
        result = CounterfactualResult(
            result_id=self._gen_id("result", scenario.scenario_id),
            scenario=scenario,
            original_pnl=original_pnl,
            counterfactual_pnl=cf_pnl,
            delta_pnl=delta,
            delta_pct=(delta / max(abs(original_pnl), 1.0)) * 100,
            explanation=f"With {scenario.description}: PnL {original_pnl:.2f}→{cf_pnl:.2f} (Δ{delta:+.2f})",
        )
        self._results.append(result)
        if len(self._results) > 500:
            self._results = self._results[-500:]
        return result

    def compare_scenarios(
        self, original_pnl: float, scenarios: list[Scenario], simulator: Any | None = None
    ) -> list[CounterfactualResult]:
        """Run multiple scenarios and rank by impact."""
        results = [self.run_counterfactual(s, original_pnl, simulator) for s in scenarios]
        results.sort(key=lambda r: abs(r.delta_pnl), reverse=True)
        return results

    def get_scenario(self, scenario_id: str) -> Scenario | None:
        return self._scenarios.get(scenario_id)

    @staticmethod
    def _gen_id(prefix: str, desc: str) -> str:
        return hashlib.md5(f"{prefix}|{desc}|{time.time()}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, int]:
        return {"scenarios": len(self._scenarios), "results": len(self._results)}
