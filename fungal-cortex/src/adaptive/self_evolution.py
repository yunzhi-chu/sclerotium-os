"""L0/L3c: SelfEvolutionLoop — "闭环自进化 + Panarchy四相" (Closed-Loop Self-Evolution + Panarchy).

Biological Metaphor:
  生物进化 = 变异(随机探索) + 选择(环境淘汰) + 遗传(成功复制)
  + Panarchy四相(系统层面的适应性循环)

  Actor→Judge→Meta-Judge三阶段:
    Actor(行动者) = 基因突变产生新性状
    Judge(裁判) = 自然环境选择
    Meta-Judge(元裁判) = 长期进化趋势(如Cope's rule: 体型趋向增大)

  Panarchy四相(与生物演化高度对应):
    r相(增长/开拓): 物种快速繁殖 + 新策略大量涌现
      如同寒武纪大爆发——多样性爆炸式增长
    K相(保守/积累): 生态系统趋于稳定 + 策略被固化
      如同恐龙时代后期——高度特化但脆弱
    Ω相(释放/崩溃): 环境突变 + 大规模灭绝 + 旧策略清零
      如同小行星撞击→恐龙灭绝
    α相(重组/新生): 空出的生态位被新物种占据 + 全新策略涌现
      如同哺乳动物辐射演化

  版本快照(create_version_snapshot):
    如同化石记录——保存每个地质时代的生物群快照
    可回滚到任意历史版本 = 从化石DNA复活灭绝物种(理论上)

  朊病毒构象催化升级:
    如同朊病毒(Prion)的β-sheet自催化模板机制(Maury 2025, FEBS Letters):
    一个成功的策略构象可以"感染"其他策略, 使其折叠为相同的高绩效构象
    → 这就是"最佳实践"在系统中的传播机制!
    但也要防止"病态构象"(过拟合策略)的传染性传播

Reference:
  Maury (2025), "Amyloid world hypothesis", FEBS Letters 599:2693-2705;
  Holling & Gunderson, Panarchy (2002);
  AESOP 2025 Conference, "The Dynamics of Panarchy"
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


# ── Panarchy Phases ───────────────────────────────────────────────────

class PanarchyPhase(Enum):
    R = "r"  # Growth/Exploitation — rapid expansion
    K = "K"  # Conservation — stability, accumulation
    OMEGA = "omega"  # Release/Collapse — creative destruction
    ALPHA = "alpha"  # Reorganization/Renewal — new possibilities


# ── Data Structures ───────────────────────────────────────────────────

@dataclass
class StrategyGene:
    """A single evolvable strategy encoded as a "gene"."""

    gene_id: str
    strategy_type: str  # e.g., "momentum", "mean_reversion"
    params: list[float]  # evolvable parameters
    fitness: float = 0.5  # 0-1 fitness score
    age: int = 0  # generations survived
    parent_id: str | None = None  # lineage tracking
    mutation_rate: float = 0.01  # per-parameter mutation probability
    conformational_score: float = 0.5  # prion-like template fitness
    created_at: float = field(default_factory=time.time)


@dataclass
class GenerationSnapshot:
    """A fossil record of the population at one generation."""

    generation: int
    phase: PanarchyPhase
    population: list[StrategyGene]
    best_fitness: float
    avg_fitness: float
    diversity: float  # 0-1, how diverse the population is
    timestamp: float = field(default_factory=time.time)


@dataclass
class EvolutionReport:
    """Output report from one evolution cycle."""

    generation: int
    phase: PanarchyPhase
    population_size: int
    best_fitness: float
    avg_fitness: float
    diversity: float
    extinctions: int  # strategies removed this cycle
    births: int  # new strategies created
    conformations_spread: int  # strategies "infected" by prion-like catalysis
    phase_transition: bool  # did panarchy phase change?
    timestamp: float = field(default_factory=time.time)


class SelfEvolutionLoop:
    """Closed-loop self-evolution engine with Panarchy dynamics.

    The "evolution" engine of the adaptive system — mutates, selects, and
    propagates strategies using biological evolution principles combined
    with prion-like conformational catalysis and Panarchy adaptive cycles.

    Architecture:
      - Actor→Judge→Meta-Judge three-stage loop
      - Panarchy r→K→Ω→α phase dynamics
      - Prion-like conformational catalysis for best-practice propagation
      - Version snapshots for rollback capability
      - Diversity preservation to prevent monoculture collapse
    """

    MIN_POPULATION = 10
    MAX_POPULATION = 200
    MUTATION_SCALE = 0.05  # std of Gaussian mutation
    PRION_INFECTION_THRESHOLD = 0.75  # fitness threshold for conformational spread
    PRION_INFECTION_RATE = 0.15  # fraction of population "infected" per cycle

    def __init__(self) -> None:
        self._logger = CortexLogger("self_evolution")
        self._call_count = 0

        # Population
        self._population: list[StrategyGene] = []
        self._gene_counter: int = 0

        # Panarchy state
        self._phase: PanarchyPhase = PanarchyPhase.R
        self._phase_duration: int = 0
        self._connectedness: float = 0.3  # how interconnected the system is
        self._resilience: float = 0.8  # how much buffer/reserve the system has

        # Evolution tracking
        self._generation: int = 0
        self._snapshots: list[GenerationSnapshot] = []
        self._extinction_record: list[dict[str, Any]] = []

        # Actor-Judge-MetaJudge tracking
        self._actor_history: list[dict[str, Any]] = []
        self._judge_verdicts: list[dict[str, Any]] = []
        self._meta_judge_rules: dict[str, float] = {
            "diversity_minimum": 0.15,
            "fitness_entropy_threshold": 0.5,
            "conformational_risk_threshold": 0.6,
        }

    # ── Actor: Generate Variations ────────────────────────────────────

    def _actor_generate(self, n_variations: int = 5) -> list[StrategyGene]:
        """Actor phase: generate new strategy variations.

        Like genetic mutation producing new traits:
        - Mutation: random perturbation of existing high-fitness genes
        - Crossover: combine parameters from two parent genes
        - Innovation: create completely new random genes

        Returns list of new candidate genes.
        """
        candidates: list[StrategyGene] = []

        # Mutation: perturb top performers
        if self._population:
            sorted_pop = sorted(self._population, key=lambda g: g.fitness, reverse=True)
            top_n = max(1, len(sorted_pop) // 3)
            for i in range(min(top_n, n_variations // 2)):
                parent = sorted_pop[i]
                mutated_params = self._mutate(parent.params, parent.mutation_rate)
                gene = StrategyGene(
                    gene_id=self._next_gene_id(),
                    strategy_type=parent.strategy_type,
                    params=mutated_params,
                    fitness=0.5,  # initial fitness, will be evaluated
                    parent_id=parent.gene_id,
                )
                candidates.append(gene)

        # Innovation: completely new random genes
        for _ in range(n_variations // 2):
            strategy_types = ["momentum", "mean_reversion", "multi_factor",
                            "arbitrage", "event_driven", "timing"]
            st = strategy_types[int(_pseudo_random(self._call_count + len(candidates)) * len(strategy_types))]
            n_params = 8  # typical strategy parameter count
            params = [_pseudo_random(self._call_count * 100 + i) * 2 - 1 for i in range(n_params)]
            gene = StrategyGene(
                gene_id=self._next_gene_id(),
                strategy_type=st,
                params=params,
                fitness=0.5,
            )
            candidates.append(gene)

        return candidates

    def _mutate(self, params: list[float], mutation_rate: float) -> list[float]:
        """Gaussian mutation on parameters."""
        mutated = []
        for p in params:
            if _pseudo_random(int(time.time() * 1000) + len(mutated)) < mutation_rate:
                # Gaussian perturbation
                u1 = _pseudo_random(int(time.time() * 2000) + len(mutated))
                u2 = _pseudo_random(int(time.time() * 3000) + len(mutated))
                z = math.sqrt(-2 * math.log(max(u1, 1e-10))) * math.cos(2 * math.pi * u2)
                mutated.append(p + z * self.MUTATION_SCALE)
            else:
                mutated.append(p)
        return mutated

    # ── Judge: Evaluate Fitness ───────────────────────────────────────

    def _judge_evaluate(self, gene: StrategyGene, performance_data: dict[str, float] | None = None) -> float:
        """Judge phase: evaluate gene fitness.

        Like natural selection — the environment determines which traits survive.

        Fitness = weighted combination of:
          - Sharpe-like ratio (risk-adjusted return)
          - Consistency (low variance in performance)
          - Diversity contribution (how different from existing population)
        """
        if performance_data is None:
            # Default: random fitness (exploration)
            return _pseudo_random(int(time.time() * 4000 + hash(gene.gene_id) % 1000000))

        sharpe = performance_data.get("sharpe", 0.0)
        consistency = performance_data.get("consistency", 0.5)
        diversity_contrib = performance_data.get("diversity_contrib", 0.5)

        # Weighted fitness
        fitness = 0.5 * min(max(sharpe / 3.0, 0.0), 1.0) + \
                  0.3 * consistency + \
                  0.2 * diversity_contrib

        return max(0.01, min(1.0, fitness))

    # ── Meta-Judge: Long-term Trends ──────────────────────────────────

    def _meta_judge_review(self) -> dict[str, Any]:
        """Meta-Judge phase: evaluate long-term evolutionary trends.

        Like Cope's rule (body size tends to increase over evolutionary time),
        the Meta-Judge detects long-term patterns and adjusts the rules.
        """
        if len(self._snapshots) < 10:
            return {"trend": "insufficient_data"}

        recent = self._snapshots[-10:]

        # Trend: is fitness improving?
        fitness_trend = [
            s.best_fitness for s in recent
        ]
        improving = sum(1 for i in range(1, len(fitness_trend))
                       if fitness_trend[i] > fitness_trend[i - 1])

        trend = "stable"
        if improving >= 7:
            trend = "improving"
        elif improving <= 2:
            trend = "declining"

        # Adjust meta-rules based on trends
        if trend == "declining":
            # Increase diversity minimum to encourage exploration
            self._meta_judge_rules["diversity_minimum"] = min(0.3,
                self._meta_judge_rules["diversity_minimum"] + 0.02)
            # Decrease conformational risk threshold to prevent monoculture
            self._meta_judge_rules["conformational_risk_threshold"] = max(0.3,
                self._meta_judge_rules["conformational_risk_threshold"] - 0.02)
        elif trend == "improving":
            # Relax constraints slightly
            self._meta_judge_rules["diversity_minimum"] = max(0.1,
                self._meta_judge_rules["diversity_minimum"] - 0.01)

        return {
            "trend": trend,
            "improvement_ratio": improving / 9,
            "adjusted_rules": dict(self._meta_judge_rules),
        }

    # ── Panarchy Dynamics ─────────────────────────────────────────────

    def _update_panarchy_phase(self) -> bool:
        """Update Panarchy phase based on connectedness and resilience.

        r→K: Growth slows as connectedness increases, resilience accumulates
        K→Ω: High connectedness + low resilience → system brittle → collapse
        Ω→α: After collapse, resources released → reorganization possible
        α→r: New structures emerge → rapid growth resumes
        """
        self._phase_duration += 1
        prev_phase = self._phase

        if self._phase == PanarchyPhase.R:
            # Growth phase: connectedness increases, resilience slowly builds
            self._connectedness += 0.02
            self._resilience += 0.01
            if self._connectedness > 0.7:
                self._phase = PanarchyPhase.K
                self._phase_duration = 0

        elif self._phase == PanarchyPhase.K:
            # Conservation: high connectedness, resilience starts declining
            self._connectedness += 0.005
            self._resilience -= 0.015
            if self._connectedness > 0.8 and self._resilience < 0.2:
                self._phase = PanarchyPhase.OMEGA
                self._phase_duration = 0
                self._logger.warn("panarchy_omega_phase", reason="brittle_system")

        elif self._phase == PanarchyPhase.OMEGA:
            # Release: creative destruction
            self._connectedness -= 0.05
            self._resilience = 0.2  # reset
            # Mass extinction event: remove low-fitness genes
            if self._population:
                extinction_threshold = sorted(g.fitness for g in self._population)[len(self._population) // 3]
                survivors = [g for g in self._population if g.fitness >= extinction_threshold]
                extinct = len(self._population) - len(survivors)
                self._population = survivors
                self._logger.info("mass_extinction", extinct=extinct, survivors=len(survivors))
            if self._connectedness < 0.4:
                self._phase = PanarchyPhase.ALPHA
                self._phase_duration = 0

        elif self._phase == PanarchyPhase.ALPHA:
            # Reorganization: new structures form
            self._connectedness += 0.03
            self._resilience += 0.05
            if self._resilience > 0.5:
                self._phase = PanarchyPhase.R
                self._phase_duration = 0

        self._connectedness = max(0.05, min(1.0, self._connectedness))
        self._resilience = max(0.05, min(1.0, self._resilience))

        return prev_phase != self._phase

    # ── Prion-like Conformational Catalysis (Maury 2025) ──────────────

    def _conformational_spread(self) -> int:
        """Spread successful "conformations" through the population.

        Like prion proteins catalyzing the conversion of normal proteins
        to the prion form through β-sheet templating:
        - High-fitness strategies "infect" lower-fitness ones
        - The infected strategies adopt the successful parameter structure
        - But we must prevent "pathological conformations" (overfitting)
        """
        if len(self._population) < 5:
            return 0

        # Find "infectious" genes (fitness > threshold)
        infectious = [g for g in self._population if g.fitness >= self.PRION_INFECTION_THRESHOLD]
        if not infectious:
            return 0

        # Check conformational risk: if one conformation dominates >60%, suppress spread
        if infectious:
            best_type = max(set(g.strategy_type for g in infectious),
                          key=lambda t: sum(1 for g in infectious if g.strategy_type == t))
            domination = sum(1 for g in infectious if g.strategy_type == best_type) / len(infectious)
            if domination > self._meta_judge_rules["conformational_risk_threshold"]:
                # Too much conformational uniformity → suppress spread
                self._logger.warn("conformational_risk_suppressed",
                                dominant_type=best_type,
                                domination=round(domination, 3))
                return 0

        # Select target genes to "infect"
        n_infect = max(1, int(len(self._population) * self.PRION_INFECTION_RATE))
        targets = [g for g in self._population if g.fitness < self.PRION_INFECTION_THRESHOLD]
        if not targets:
            return 0

        spread_count = 0
        for _ in range(min(n_infect, len(targets))):
            target = targets[int(_pseudo_random(len(targets) * 777) * len(targets)) % len(targets)]
            template = infectious[int(_pseudo_random(len(infectious) * 888) * len(infectious)) % len(infectious)]

            # "Fold" target params toward template params (β-sheet templating)
            fold_ratio = 0.3  # how much to adopt template's structure
            target.conformational_score = min(1.0, target.conformational_score + 0.1)
            for i in range(min(len(target.params), len(template.params))):
                target.params[i] = (1 - fold_ratio) * target.params[i] + fold_ratio * template.params[i]
            spread_count += 1

        return spread_count

    # ── Main Evolution Cycle ──────────────────────────────────────────

    def evolve(
        self,
        performance_data: dict[str, dict[str, float]] | None = None,
    ) -> EvolutionReport:
        """Execute one complete evolution cycle.

        Actor → Judge → Meta-Judge → (Prion spread) → (Panarchy update)

        Args:
            performance_data: {gene_id: {sharpe, consistency, diversity_contrib}}

        Returns:
            EvolutionReport with generation statistics
        """
        self._call_count += 1
        self._generation += 1

        # 0. Ensure minimum population
        if len(self._population) < self.MIN_POPULATION:
            for _ in range(self.MIN_POPULATION):
                st = ["momentum", "mean_reversion", "multi_factor"][_ % 3]
                gene = StrategyGene(
                    gene_id=self._next_gene_id(),
                    strategy_type=st,
                    params=[_pseudo_random(i * 12345) * 2 - 1 for i in range(8)],
                    fitness=0.5,
                )
                self._population.append(gene)

        # 1. ACTOR: Generate new candidates
        n_variations = max(3, len(self._population) // 5)
        candidates = self._actor_generate(n_variations)

        # 2. JUDGE: Evaluate all genes
        perf = performance_data or {}
        for gene in self._population:
            gene_data = perf.get(gene.gene_id, {})
            gene.fitness = self._judge_evaluate(gene, gene_data)
            gene.age += 1

        for gene in candidates:
            gene_data = perf.get(gene.gene_id, {})
            gene.fitness = self._judge_evaluate(gene, gene_data)

        # Add judged candidates to population
        self._population.extend(candidates)

        # 3. META-JUDGE: Long-term trend analysis
        meta_review = self._meta_judge_review()

        # 4. PRION SPREAD: Conformational catalysis
        spread_count = self._conformational_spread()

        # 5. SELECTION: Remove low-fitness genes (natural selection)
        if len(self._population) > self.MAX_POPULATION:
            self._population.sort(key=lambda g: g.fitness, reverse=True)
            extinct = len(self._population) - self.MAX_POPULATION
            removed = self._population[self.MAX_POPULATION:]
            self._population = self._population[:self.MAX_POPULATION]
            for g in removed:
                self._extinction_record.append({
                    "gene_id": g.gene_id,
                    "strategy_type": g.strategy_type,
                    "fitness": g.fitness,
                    "age": g.age,
                    "generation": self._generation,
                })
        else:
            extinct = 0

        # 6. PANARCHY: Update phase
        phase_changed = self._update_panarchy_phase()

        # 7. SNAPSHOT: Save generation snapshot
        if self._population:
            best_fitness = max(g.fitness for g in self._population)
            avg_fitness = sum(g.fitness for g in self._population) / len(self._population)
            # Diversity: std of fitness distribution
            fit_std = (sum((g.fitness - avg_fitness) ** 2 for g in self._population) / len(self._population)) ** 0.5
            diversity = min(fit_std * 3, 1.0)
        else:
            best_fitness = 0.0
            avg_fitness = 0.0
            diversity = 0.0

        snapshot = GenerationSnapshot(
            generation=self._generation,
            phase=self._phase,
            population=[StrategyGene(
                gene_id=g.gene_id, strategy_type=g.strategy_type,
                params=g.params[:], fitness=g.fitness, age=g.age,
                parent_id=g.parent_id, conformational_score=g.conformational_score,
            ) for g in self._population],
            best_fitness=best_fitness,
            avg_fitness=avg_fitness,
            diversity=diversity,
        )
        self._snapshots.append(snapshot)
        if len(self._snapshots) > 100:
            self._snapshots = self._snapshots[-100:]

        # Build report
        report = EvolutionReport(
            generation=self._generation,
            phase=self._phase,
            population_size=len(self._population),
            best_fitness=round(best_fitness, 4),
            avg_fitness=round(avg_fitness, 4),
            diversity=round(diversity, 4),
            extinctions=extinct,
            births=len(candidates),
            conformations_spread=spread_count,
            phase_transition=phase_changed,
        )

        self._logger.info("evolution_cycle",
                         generation=self._generation,
                         phase=self._phase.value,
                         pop_size=len(self._population),
                         best_fitness=round(best_fitness, 3),
                         meta_trend=meta_review.get("trend", "unknown"))

        return report

    def create_version_snapshot(self, version_label: str) -> dict[str, Any]:
        """Create a named version snapshot for rollback.

        Like a fossil record — preserves the complete genetic makeup
        of the population at this moment for potential resurrection.
        """
        return {
            "version": version_label,
            "generation": self._generation,
            "phase": self._phase.value,
            "population_size": len(self._population),
            "genes": [
                {
                    "gene_id": g.gene_id,
                    "strategy_type": g.strategy_type,
                    "params": g.params[:],
                    "fitness": g.fitness,
                    "parent_id": g.parent_id,
                }
                for g in self._population
            ],
            "timestamp": time.time(),
        }

    def rollback_to_snapshot(self, snapshot: dict[str, Any]) -> int:
        """Rollback population to a previous snapshot.

        Like resurrecting extinct species from fossil DNA.
        Returns number of genes restored.
        """
        self._population = []
        for gene_data in snapshot.get("genes", []):
            gene = StrategyGene(
                gene_id=gene_data["gene_id"],
                strategy_type=gene_data["strategy_type"],
                params=gene_data["params"],
                fitness=gene_data.get("fitness", 0.5),
                parent_id=gene_data.get("parent_id"),
            )
            self._population.append(gene)

        self._logger.info("rollback_executed",
                         version=snapshot.get("version"),
                         genes_restored=len(self._population))

        return len(self._population)

    def _next_gene_id(self) -> str:
        self._gene_counter += 1
        return f"gene-{self._gene_counter:06d}"

    def get_phase_status(self) -> dict[str, Any]:
        """Get current Panarchy phase and system state."""
        return {
            "phase": self._phase.value,
            "phase_duration": self._phase_duration,
            "connectedness": round(self._connectedness, 3),
            "resilience": round(self._resilience, 3),
            "population_size": len(self._population),
            "generation": self._generation,
        }

    @property
    def stats(self) -> dict[str, Any]:
        if self._population:
            best = max(self._population, key=lambda g: g.fitness)
            best_gene = {
                "gene_id": best.gene_id,
                "strategy_type": best.strategy_type,
                "fitness": round(best.fitness, 4),
                "age": best.age,
            }
        else:
            best_gene = None

        return {
            "generation": self._generation,
            "phase": self._phase.value,
            "phase_duration": self._phase_duration,
            "population_size": len(self._population),
            "best_gene": best_gene,
            "connectedness": round(self._connectedness, 3),
            "resilience": round(self._resilience, 3),
            "snapshot_count": len(self._snapshots),
            "extinction_count": len(self._extinction_record),
            "meta_judge_rules": {k: round(v, 3) for k, v in self._meta_judge_rules.items()},
        }


def _pseudo_random(seed: int) -> float:
    x = (seed * 1103515245 + 12345) & 0x7FFFFFFF
    return (x % 1000000) / 1000000.0
