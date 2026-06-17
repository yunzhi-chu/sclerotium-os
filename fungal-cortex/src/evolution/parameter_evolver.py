"""L1: Parameter Evolution — genetic algorithm + fitness-proportionate selection.

Operates at the fastest timescale (minutes). Each chromosome encodes a set of
strategy parameters (weights, thresholds, lookback windows, etc.).

Algorithm:
1. Initialize population of N chromosomes (random perturbations of baseline)
2. Evaluate fitness (backtest/validation performance)
3. Select: tournament selection with elitism
4. Crossover: single-point crossover with configurable probability
5. Mutate: Gaussian perturbation with adaptive mutation rate
6. Repeat for G generations
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Chromosome:
    """A single parameter set (individual in the population)."""

    genes: dict[str, float]  # parameter_name → value
    fitness: float = 0.0
    generation: int = 0
    parent_ids: list[str] = field(default_factory=list)


@dataclass
class EvolutionGeneration:
    """Snapshot of one generation's state."""

    generation: int
    population: list[Chromosome]
    best_fitness: float
    mean_fitness: float
    diversity: float  # Standard deviation of fitness


class ParameterEvolver:
    """L1: Genetic algorithm for strategy parameter optimization.

    Timescale: minutes (fast adaptation to recent market conditions).
    """

    def __init__(
        self,
        population_size: int = 50,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
        elitism_count: int = 3,
        tournament_size: int = 4,
        seed: int | None = None,
    ) -> None:
        self._pop_size = population_size
        self._mutation_rate = mutation_rate
        self._crossover_rate = crossover_rate
        self._elitism = elitism_count
        self._tournament = tournament_size
        self._population: list[Chromosome] = []
        self._generation = 0
        self._history: list[EvolutionGeneration] = []
        if seed is not None:
            random.seed(seed)

    def initialize(
        self,
        parameter_bounds: dict[str, tuple[float, float]],
        baseline: dict[str, float] | None = None,
    ) -> list[Chromosome]:
        """Initialize population with random parameter values within bounds."""
        self._population = []
        for i in range(self._pop_size):
            genes: dict[str, float] = {}
            for name, (lo, hi) in parameter_bounds.items():
                if baseline and name in baseline:
                    # Perturb around baseline
                    noise = random.gauss(0.0, (hi - lo) * 0.1)
                    genes[name] = min(hi, max(lo, baseline[name] + noise))
                else:
                    genes[name] = random.uniform(lo, hi)
            self._population.append(Chromosome(genes=genes, generation=0, parent_ids=[]))
        self._generation = 0
        return self._population

    def evolve(
        self,
        fitness_fn: Callable[[dict[str, float]], float],
        generations: int = 20,
    ) -> EvolutionGeneration:
        """Run evolution for the specified number of generations."""
        for _ in range(generations):
            self._step_generation(fitness_fn)
        return self.get_best_generation()

    def _step_generation(self, fitness_fn: Callable[[dict[str, float]], float]) -> None:
        """Execute one generation of evolution."""
        self._generation += 1

        # Evaluate fitness
        for chrom in self._population:
            chrom.fitness = fitness_fn(chrom.genes)
            chrom.generation = self._generation

        # Sort by fitness (descending)
        self._population.sort(key=lambda c: c.fitness, reverse=True)

        # Record generation stats
        best = self._population[0]
        mean_fit = sum(c.fitness for c in self._population) / len(self._population)
        fit_std = math.sqrt(sum((c.fitness - mean_fit) ** 2 for c in self._population) / len(self._population))
        self._history.append(EvolutionGeneration(
            generation=self._generation,
            population=[c for c in self._population],
            best_fitness=best.fitness,
            mean_fitness=mean_fit,
            diversity=fit_std,
        ))

        # Create next generation
        new_pop: list[Chromosome] = []

        # Elitism: keep top N
        for i in range(min(self._elitism, len(self._population))):
            new_pop.append(Chromosome(
                genes=dict(self._population[i].genes),
                fitness=self._population[i].fitness,
                generation=self._generation,
                parent_ids=[self._population[i].genes.get("_id", "")],
            ))

        # Fill rest with crossover + mutation
        while len(new_pop) < self._pop_size:
            parent1 = self._tournament_select()
            parent2 = self._tournament_select()

            if random.random() < self._crossover_rate:
                child_genes = self._crossover(parent1.genes, parent2.genes)
            else:
                child_genes = dict(parent1.genes)

            self._mutate(child_genes)
            new_pop.append(Chromosome(
                genes=child_genes,
                generation=self._generation,
                parent_ids=[parent1.genes.get("_id", ""), parent2.genes.get("_id", "")],
            ))

        self._population = new_pop

    def _tournament_select(self) -> Chromosome:
        """Tournament selection: pick best from random subset."""
        candidates = random.sample(self._population, min(self._tournament, len(self._population)))
        return max(candidates, key=lambda c: c.fitness)

    def _crossover(self, genes1: dict[str, float], genes2: dict[str, float]) -> dict[str, float]:
        """Single-point crossover on parameter sets."""
        keys = list(genes1.keys())
        if len(keys) < 2:
            return dict(genes1)

        crossover_point = random.randint(1, len(keys) - 1)
        child: dict[str, float] = {}
        for i, key in enumerate(keys):
            if i < crossover_point:
                child[key] = genes1.get(key, genes2.get(key, 0.0))
            else:
                child[key] = genes2.get(key, genes1.get(key, 0.0))
        return child

    def _mutate(self, genes: dict[str, float]) -> None:
        """Gaussian mutation with adaptive rate."""
        for key in list(genes.keys()):
            if random.random() < self._mutation_rate:
                perturbation = random.gauss(0.0, abs(genes[key]) * 0.1 + 0.01)
                genes[key] += perturbation

    def get_best_chromosome(self) -> Chromosome:
        if not self._population:
            raise ValueError("Population not initialized")
        return max(self._population, key=lambda c: c.fitness)

    def get_best_generation(self) -> EvolutionGeneration:
        if not self._history:
            raise ValueError("No evolution history")
        return self._history[-1]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "population_size": self._pop_size,
            "generation": self._generation,
            "mutation_rate": self._mutation_rate,
            "crossover_rate": self._crossover_rate,
            "best_fitness": self._history[-1].best_fitness if self._history else 0.0,
            "diversity": self._history[-1].diversity if self._history else 0.0,
        }
