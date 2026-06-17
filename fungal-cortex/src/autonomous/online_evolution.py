"""L4 M4a: OnlineEvolutionEngine — "双循环神经可塑性"(LTP/LTD + Pruning) 在线演化引擎.

Biological Metaphor:
  大脑的双时间尺度可塑性:
    快速循环(日内, 秒-分钟级): 突触权重的LTP/LTD变化
    慢速循环(每周, 天-周级): 突触修剪+髓鞘形成+神经发生

  快速循环: 实时反馈→微小参数调整±3%
    = AMPA受体插入/移除(LTP/LTD)
  慢速循环: Actor→Judge→Meta-Judge + 遗传规划重组
    = 睡眠中的突触修剪(剪掉40-60%不用的突触)
    + 树突棘生长(建立新连接) + 髓鞘形成(强化常用通路)

  版本快照 = 发育关键期的"印记"(Imprinting):
    在特定时间窗口内, 某些经验被永久性地编码

Reference:
  Lu et al. (2025), "Homeostatic scaling × structural plasticity", eLife;
  Grasso et al. (2025), "Connectomic traces of Hebbian plasticity", bioRxiv
"""

from __future__ import annotations

import hashlib
import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from src.utils.logging import CortexLogger


class EvolutionLevel(str, Enum):
    MICRO = "micro"   # real-time LTP/LTD
    SLOW = "slow"     # weekly pruning/myelination


@dataclass
class Individual:
    """A strategy individual — like a synaptic configuration."""

    ind_id: str
    params: dict[str, float]
    fitness: float = 0.0
    generation: int = 0
    parent_ids: list[str] = field(default_factory=list)
    age: int = 0

    def clone(self) -> Individual:
        return Individual(
            ind_id=self.ind_id, params=dict(self.params),
            fitness=self.fitness, generation=self.generation,
            parent_ids=list(self.parent_ids), age=self.age,
        )


@dataclass
class VersionSnapshot:
    """A version snapshot — like a developmental imprint."""

    snapshot_id: str
    params: dict[str, float]
    fitness: float
    timestamp: float = field(default_factory=time.time)
    description: str = ""


class OnlineEvolutionEngine:
    """Dual-time-scale evolution engine — fast LTP/LTD + slow pruning/myelination.

    Config:
      - micro_rate: max parameter change per fast cycle (default 3%)
      - population_size: for slow cycle
      - generations: slow cycle iterations
    """

    def __init__(
        self, micro_rate: float = 0.03, population_size: int = 30, generations: int = 10
    ) -> None:
        self._micro_rate = micro_rate
        self._pop_size = population_size
        self._generations = generations
        self._population: list[Individual] = []
        self._snapshots: list[VersionSnapshot] = []
        self._generation_count = 0
        self._logger = CortexLogger("online_evolution")

    def initialize(self, param_bounds: list[tuple[float, float]]) -> list[Individual]:
        """Initialize random population."""
        self._population = []
        for i in range(self._pop_size):
            params = {f"p{j}": random.uniform(lo, hi) for j, (lo, hi) in enumerate(param_bounds)}
            self._population.append(Individual(ind_id=self._gen_id("init", str(i)), params=params))
        return self._population

    def micro_evolve(self, params: dict[str, float], fitness_delta: float) -> dict[str, float]:
        """Fast cycle: LTP/LTD micro-adjustments (±3%).

        LTD: negative fitness → weaken (decrease)
        LTP: positive fitness → strengthen (increase)
        """
        mutated: dict[str, float] = {}
        signal = math.tanh(fitness_delta)
        for key, value in params.items():
            delta = self._micro_rate * signal
            noise = random.gauss(0, abs(delta) * 0.1)
            mutated[key] = value * (1 + delta + noise)
            mutated[key] = max(value * 0.5, min(value * 1.5, mutated[key]))
        return mutated

    def slow_evolve(self, fitness_fn: Callable[[dict[str, float]], float]) -> Individual:
        """Slow cycle: pruning + spinogenesis + myelination (weekly).

        Actor→Judge→Meta-Judge pipeline:
          Actor: generate variants (mutation)
          Judge: evaluate fitness (natural selection)
          Meta-Judge: decide which to keep (long-term trends)
        """
        if not self._population:
            return Individual(ind_id="empty", params={}, fitness=0.0)

        for _ in range(self._generations):
            self._generation_count += 1
            # Evaluate
            for ind in self._population:
                ind.fitness = fitness_fn(ind.params)

            # Sort
            self._population.sort(key=lambda x: x.fitness, reverse=True)

            # Elitism + Mutation + Crossover
            n_elite = max(1, self._pop_size // 5)
            new_pop = [self._population[i].clone() for i in range(n_elite)]

            while len(new_pop) < self._pop_size:
                p1, p2 = random.sample(self._population[:self._pop_size // 2], 2)
                child_params = self._crossover(p1.params, p2.params)
                child_params = self._mutate(child_params, 0.1)
                new_pop.append(Individual(
                    ind_id=self._gen_id("gen", str(len(new_pop))),
                    params=child_params,
                    generation=self._generation_count,
                    parent_ids=[p1.ind_id, p2.ind_id],
                ))

            self._population = new_pop

        return max(self._population, key=lambda x: x.fitness)

    def create_snapshot(self, params: dict[str, float], fitness: float, description: str = "") -> VersionSnapshot:
        """Create a version snapshot — developmental imprint."""
        snap = VersionSnapshot(
            snapshot_id=self._gen_id("snap", description),
            params=dict(params),
            fitness=fitness,
            description=description,
        )
        self._snapshots.append(snap)
        if len(self._snapshots) > 100:
            self._snapshots = self._snapshots[-100:]
        return snap

    def best(self) -> Individual | None:
        if not self._population:
            return None
        best = max(self._population, key=lambda x: x.fitness)
        return best.clone()

    def _crossover(self, p1: dict[str, float], p2: dict[str, float]) -> dict[str, float]:
        child: dict[str, float] = {}
        for key in set(p1) | set(p2):
            child[key] = p1[key] if random.random() < 0.5 else p2.get(key, p1[key] / 2 + p2.get(key, p1[key]) / 2)
        return child

    def _mutate(self, params: dict[str, float], sigma: float = 0.05) -> dict[str, float]:
        return {k: v * (1 + random.gauss(0, sigma)) for k, v in params.items()}

    @staticmethod
    def _gen_id(prefix: str, suffix: str) -> str:
        return hashlib.md5(f"{prefix}|{suffix}|{time.time()}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        best = self.best()
        return {
            "population": len(self._population),
            "generation": self._generation_count,
            "best_fitness": best.fitness if best else 0.0,
            "snapshots": len(self._snapshots),
        }
