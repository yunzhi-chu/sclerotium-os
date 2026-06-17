"""L5 4.7: DistributedEvolutionEngine — "Symbiogenesis共生进化 + SHARP" 分布式进化引擎.

Biological Metaphor:
  共生起源(Symbiogenesis): 线粒体和叶绿体的进化
    真核细胞祖先吞噬了需氧细菌(→线粒体)和蓝细菌(→叶绿体),
    两种独立生物融合→全新物种(真核生物), 这是进化史上最重要的事件之一。

  三级演化体系:
    1. 个体微进化(实时±1%): 基因突变, 每次DNA复制约10^-8错误率
    2. 群组并行进化(24h A/B测试): 同域物种形成, 对照/实验组自然选择
    3. 全局架构进化(每周): 大灭绝事件后的适应性辐射

  SHARP(分层Shapley):
    计算每个指标对总PnL的边际贡献(Shapley value)
    = "如果没有这个指标, 系统表现会差多少?"

  地衣式演化: 不同环境选择不同的藻类共生体→不同市场体制选择不同策略组合

Reference:
  Symbiogenesis (Margulis 1967, 1993);
  Dong et al. (2026), "Cladonia uncialis tripartite symbiosis genome", Scientific Data;
  Keller et al. (2026), "Ubiquitous black fungus symbiont", Current Biology
"""

from __future__ import annotations

import hashlib
import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from src.utils.logging import CortexLogger


# ── Constants ────────────────────────────────────────────────────────

class EvolutionLevel(str, Enum):
    MICRO = "micro"    # individual real-time ±1%
    GROUP = "group"    # parallel A/B testing 24h
    GLOBAL = "global"  # weekly architecture evolution


MICRO_MUTATION_RATE = 0.01  # ±1%
GROUP_TEST_DURATION = 86400  # 24 hours
GLOBAL_EVOLUTION_INTERVAL = 604800  # 1 week
MAX_STRATEGIES = 200
MAX_SHAPLEY_ITERS = 1000


# ── Data Structures ──────────────────────────────────────────────────


@dataclass
class SHAPValue:
    """Shapley value for an indicator/strategy — its marginal contribution."""

    entity_id: str
    entity_type: str  # "indicator", "strategy", "hyperparameter"
    shapley_value: float  # contribution to total PnL
    std_error: float = 0.0
    iterations: int = 0
    confidence: float = 0.0  # 0-1
    timestamp: float = field(default_factory=time.time)


@dataclass
class EvolutionRound:
    """Record of an evolution round at any level."""

    round_id: str
    level: EvolutionLevel
    mutations_applied: int = 0
    improvements: int = 0
    best_fitness_delta: float = 0.0
    elapsed_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)


# ── Main Class ───────────────────────────────────────────────────────


class DistributedEvolutionEngine:
    """Three-tier distributed evolution: micro + group + global symbiogenesis.

    Config:
      - micro_mutation_rate: max parameter change per micro round
      - group_test_duration: A/B test duration in seconds
      - global_interval: architecture evolution interval
    """

    def __init__(
        self,
        micro_mutation_rate: float = MICRO_MUTATION_RATE,
        group_test_duration: float = GROUP_TEST_DURATION,
        global_interval: float = GLOBAL_EVOLUTION_INTERVAL,
    ) -> None:
        self._micro_rate = micro_mutation_rate
        self._group_duration = group_test_duration
        self._global_interval = global_interval

        self._strategies: dict[str, dict[str, Any]] = {}  # {strategy_id: params}
        self._shapley_values: dict[str, SHAPValue] = {}
        self._evolution_history: list[EvolutionRound] = []
        self._last_global = time.time()

        self._logger = CortexLogger("distributed_evolution")

    # ── Public API ──────────────────────────────────────────────────

    def register_strategy(
        self, strategy_id: str, params: dict[str, float], metadata: dict[str, Any] | None = None
    ) -> None:
        """Register a strategy in the evolution pool."""
        self._strategies[strategy_id] = {
            "params": dict(params),
            "fitness": 0.0,
            "generation": 0,
            "metadata": metadata or {},
        }

    def micro_evolve(
        self, strategy_id: str, fitness_delta: float
    ) -> dict[str, float] | None:
        """Individual-level micro evolution: ±1% parameter mutation.

        Like DNA replication mutations — small, mostly neutral, occasionally beneficial.
        """
        entry = self._strategies.get(strategy_id)
        if entry is None:
            return None

        params = entry["params"]
        mutated: dict[str, float] = {}

        for key, value in params.items():
            # Mutation proportional to fitness signal
            mutation = self._micro_rate * math.tanh(fitness_delta / 10)
            noise = random.gauss(0, abs(mutation))
            mutated[key] = value * (1 + noise)
            # Clamp: don't allow huge single-step changes
            mutated[key] = value * max(0.7, min(1.3, 1 + noise))

        entry["params"] = mutated
        entry["generation"] += 1

        self._evolution_history.append(EvolutionRound(
            round_id=self._gen_round_id("micro", strategy_id),
            level=EvolutionLevel.MICRO,
            mutations_applied=len(mutated),
        ))
        return mutated

    def group_evolve(
        self, group: list[str], fitness_fn: Callable[[dict[str, float]], float],
        top_k: int = 3,
    ) -> dict[str, Any]:
        """Group-level parallel evolution: A/B test variants, promote winners.

        Like sympatric speciation — same environment, different niches.
        """
        results: dict[str, Any] = {
            "winners": [],
            "losers": [],
            "improvements": 0,
        }

        variants: dict[str, dict[str, float]] = {}
        for sid in group:
            entry = self._strategies.get(sid)
            if entry is None:
                continue
            # Create variant
            variant_params = self._mutate_params(entry["params"], sigma=0.05)
            variants[sid] = variant_params

        # Evaluate all
        scores: list[tuple[str, float]] = []
        for sid, params in variants.items():
            fitness = fitness_fn(params)
            scores.append((sid, fitness))

            entry = self._strategies[sid]
            old_fitness = entry["fitness"]
            if fitness > old_fitness:
                entry["params"] = params
                entry["fitness"] = fitness
                results["winners"].append(sid)
                results["improvements"] += 1
            else:
                results["losers"].append(sid)

        scores.sort(key=lambda x: x[1], reverse=True)
        results["top_scores"] = scores[:top_k]

        # Cross-breeding: combine top performers (like genetic recombination)
        if len(scores) >= 4:
            top2 = [s[0] for s in scores[:2]]
            child_params = self._crossover(
                self._strategies[top2[0]]["params"],
                self._strategies[top2[1]]["params"],
            )
            child_id = self._gen_round_id("child", str(time.time()))
            self._strategies[child_id] = {
                "params": child_params,
                "fitness": 0.0,
                "generation": max(
                    self._strategies[top2[0]]["generation"],
                    self._strategies[top2[1]]["generation"],
                ) + 1,
                "metadata": {"parents": top2},
            }
            results["offspring"] = child_id

        self._evolution_history.append(EvolutionRound(
            round_id=self._gen_round_id("group", str(time.time())),
            level=EvolutionLevel.GROUP,
            mutations_applied=len(group),
            improvements=results["improvements"],
        ))
        return results

    def global_evolve(self) -> dict[str, Any]:
        """Global architecture evolution: cull weak strategies, promote diversity.

        Like adaptive radiation after mass extinction.
        """
        if time.time() - self._last_global < self._global_interval:
            return {"triggered": False, "reason": "cooldown"}

        self._last_global = time.time()

        # Cull bottom 20%
        fitnesses = [(sid, s["fitness"]) for sid, s in self._strategies.items()]
        fitnesses.sort(key=lambda x: x[1])
        cull_count = max(1, len(fitnesses) // 5)
        culled = [sid for sid, _ in fitnesses[:cull_count]]

        for sid in culled:
            del self._strategies[sid]

        # Promote diverse top strategies (niching)
        survivors = list(self._strategies.keys())
        if len(survivors) > 3:
            # Create niche variants from top 3
            top3 = sorted(survivors, key=lambda s: self._strategies[s]["fitness"], reverse=True)[:3]
            for i, sid in enumerate(top3):
                variant = self._mutate_params(self._strategies[sid]["params"], sigma=0.1 + 0.05 * i)
                variant_id = self._gen_round_id("global_variant", str(i))
                self._strategies[variant_id] = {
                    "params": variant,
                    "fitness": 0.0,
                    "generation": self._strategies[sid]["generation"] + 1,
                    "metadata": {"ancestor": sid},
                }

        self._evolution_history.append(EvolutionRound(
            round_id=self._gen_round_id("global", str(time.time())),
            level=EvolutionLevel.GLOBAL,
            mutations_applied=len(self._strategies),
        ))
        return {
            "triggered": True,
            "culled": len(culled),
            "surviving": len(self._strategies),
            "new_variants": len(self._strategies) - len(survivors),
        }

    def compute_shapley(
        self, entity_ids: list[str],
        baseline_fn: Callable[[list[str]], float],
        eval_fn: Callable[[str, list[str]], float],
    ) -> list[SHAPValue]:
        """Compute Shapley values for entities (indicators/strategies).

        Estimates each entity's marginal contribution to total PnL.
        """
        results: list[SHAPValue] = []
        n = len(entity_ids)
        if n == 0:
            return []

        full_set = set(entity_ids)
        baseline = baseline_fn(list(full_set))

        for entity in entity_ids:
            contributions: list[float] = []

            for _ in range(min(MAX_SHAPLEY_ITERS // max(n, 1), 200)):
                # Random subset without entity
                subset_size = random.randint(0, n - 1)
                subset = set(random.sample(entity_ids, subset_size)) if subset_size > 0 else set()
                if entity in subset:
                    continue

                with_entity = eval_fn(entity, list(subset))
                without_entity = eval_fn("", list(subset))
                marginal = with_entity - without_entity
                contributions.append(marginal)

            mean_contrib = sum(contributions) / len(contributions) if contributions else 0.0
            std_err = math.sqrt(
                sum((c - mean_contrib) ** 2 for c in contributions) / max(len(contributions) - 1, 1)
            ) if len(contributions) > 1 else 0.0

            sv = SHAPValue(
                entity_id=entity,
                entity_type="indicator",
                shapley_value=mean_contrib,
                std_error=std_err,
                iterations=len(contributions),
                confidence=1.0 - min(1.0, std_err / max(abs(mean_contrib), 0.001)),
            )
            results.append(sv)
            self._shapley_values[entity] = sv

        return sorted(results, key=lambda s: abs(s.shapley_value), reverse=True)

    # ── Genetic Operators ───────────────────────────────────────────

    def _mutate_params(self, params: dict[str, float], sigma: float = 0.05) -> dict[str, float]:
        mutated: dict[str, float] = {}
        for key, value in params.items():
            noise = random.gauss(0, sigma)
            mutated[key] = value * (1 + noise)
        return mutated

    def _crossover(
        self, parent1: dict[str, float], parent2: dict[str, float]
    ) -> dict[str, float]:
        """Uniform crossover: randomly select from each parent."""
        child: dict[str, float] = {}
        all_keys = set(parent1.keys()) | set(parent2.keys())
        for key in all_keys:
            if key in parent1 and key in parent2:
                child[key] = parent1[key] if random.random() < 0.5 else parent2[key]
            elif key in parent1:
                child[key] = parent1[key]
            else:
                child[key] = parent2[key]
        return child

    @staticmethod
    def _gen_round_id(level: str, suffix: str) -> str:
        raw = f"{level}|{suffix}|{time.time()}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    # ── Stats ──────────────────────────────────────────────────────

    def get_strategy(self, strategy_id: str) -> dict[str, Any] | None:
        return self._strategies.get(strategy_id)

    @property
    def strategies(self) -> list[dict[str, Any]]:
        return [
            {"id": sid, **s} for sid, s in self._strategies.items()
        ]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "strategies": len(self._strategies),
            "shapley_values": len(self._shapley_values),
            "evolution_rounds": len(self._evolution_history),
            "last_global": self._last_global,
        }
