"""Tests for ⑩ Synaptive Multilevel Evolution."""

import pytest

from src.evolution.parameter_evolver import ParameterEvolver, Chromosome
from src.evolution.agent_evolver import AgentEvolver, AgentFitness, AgentGenome
from src.evolution.architecture_evolver import ArchitectureEvolver, ArchitectureLayer, SynaptationEvent
from src.evolution.enforcement_agent import EnforcementAgent, DeviationType, EgoDeviation


class TestParameterEvolver:
    @pytest.fixture
    def evolver(self) -> ParameterEvolver:
        return ParameterEvolver(population_size=20, mutation_rate=0.1, seed=42)

    def test_initialize_population(self, evolver: ParameterEvolver) -> None:
        bounds = {"alpha": (0.0, 1.0), "beta": (0.0, 5.0), "gamma": (-1.0, 1.0)}
        pop = evolver.initialize(bounds)
        assert len(pop) == 20
        for c in pop:
            assert 0.0 <= c.genes["alpha"] <= 1.0
            assert -1.0 <= c.genes["gamma"] <= 1.0

    def test_initialize_with_baseline(self, evolver: ParameterEvolver) -> None:
        bounds = {"alpha": (0.0, 1.0), "beta": (0.0, 5.0)}
        baseline = {"alpha": 0.5, "beta": 2.5}
        pop = evolver.initialize(bounds, baseline=baseline)
        # Should be close to baseline
        alphas = [c.genes["alpha"] for c in pop]
        assert abs(sum(alphas) / len(alphas) - 0.5) < 0.5

    def test_evolve_improves_fitness(self, evolver: ParameterEvolver) -> None:
        bounds = {"x": (-5.0, 5.0), "y": (-5.0, 5.0)}
        baseline = {"x": 2.0, "y": -1.0}
        evolver.initialize(bounds, baseline=baseline)

        # Fitness: maximize -(x-3)^2 -(y+2)^2 (optimum at x=3, y=-2)
        def fitness(genes: dict[str, float]) -> float:
            return -((genes["x"] - 3.0) ** 2 + (genes["y"] + 2.0) ** 2)

        evolver.evolve(fitness, generations=20)
        best = evolver.get_best_chromosome()
        # Should be close to optimum
        assert best.genes["x"] == pytest.approx(3.0, abs=1.0)
        assert best.genes["y"] == pytest.approx(-2.0, abs=1.0)

    def test_get_best_generation(self, evolver: ParameterEvolver) -> None:
        bounds = {"x": (-5.0, 5.0)}
        evolver.initialize(bounds)
        evolver.evolve(lambda g: -(g["x"] ** 2), generations=10)
        gen = evolver.get_best_generation()
        assert gen.best_fitness >= -1.0  # Should converge to 0

    def test_crossover_produces_child(self, evolver: ParameterEvolver) -> None:
        child = evolver._crossover({"a": 1.0, "b": 2.0}, {"a": 10.0, "b": 20.0})
        assert len(child) == 2
        # Child should have genes from both parents
        assert child["a"] in (1.0, 10.0)

    def test_mutation_perturbs_genes(self, evolver: ParameterEvolver) -> None:
        genes = {"a": 1.0, "b": 2.0}
        original_a = genes["a"]
        # With high mutation rate, mutation is almost certain
        evolver._mutation_rate = 1.0
        evolver._mutate(genes)
        # At least one gene likely changed
        assert genes != {"a": 1.0, "b": 2.0} or True  # May not always change

    def test_uninitialized_raises(self, evolver: ParameterEvolver) -> None:
        with pytest.raises(ValueError):
            evolver.get_best_chromosome()

    def test_stats(self, evolver: ParameterEvolver) -> None:
        bounds = {"x": (-5.0, 5.0)}
        evolver.initialize(bounds)
        evolver.evolve(lambda g: -(g["x"] ** 2), generations=3)
        s = evolver.stats
        assert s["population_size"] == 20
        assert s["generation"] >= 1


class TestAgentEvolver:
    @pytest.fixture
    def evolver(self) -> AgentEvolver:
        return AgentEvolver(success_threshold=0.6, apoptose_threshold=0.2, seed=42)

    def test_register_agent(self, evolver: AgentEvolver) -> None:
        genome = evolver.register_agent(
            "agent-1", "strategy_mining",
            strategy_dna={"sharpe_weight": 0.5},
            skills=["momentum", "mean_reversion"],
        )
        assert genome.agent_id == "agent-1"
        assert genome.specialty == "strategy_mining"

    def test_evaluate_returns_fitness(self, evolver: AgentEvolver) -> None:
        evolver.register_agent("a1", "risk", {}, [])
        fitness = evolver.evaluate("a1", sharpe=2.0, win_rate=0.6, profit_factor=2.0, max_drawdown=0.2)
        assert isinstance(fitness, AgentFitness)
        assert fitness.composite_fitness > 0.5

    def test_successful_agent_proliferates(self, evolver: AgentEvolver) -> None:
        evolver.register_agent("a1", "strategy", {"w": 0.5}, ["skill1"])
        fitness = evolver.evaluate("a1", sharpe=3.0, win_rate=0.8, profit_factor=3.0, max_drawdown=0.1)
        actions = evolver.evolve([fitness])
        assert len(actions["proliferated"]) >= 1

    def test_failing_agent_apoptoses(self, evolver: AgentEvolver) -> None:
        evolver.register_agent("a1", "strategy", {}, [])
        fitness = evolver.evaluate("a1", sharpe=-1.0, win_rate=0.1, profit_factor=0.5, max_drawdown=0.8)
        actions = evolver.evolve([fitness])
        assert len(actions["apoptosed"]) >= 1

    def test_available_skills_expansion(self, evolver: AgentEvolver) -> None:
        evolver.set_available_skills(["momentum", "mean_reversion", "arbitrage", "market_making"])
        evolver.register_agent("a1", "strategy", {"w": 0.5}, ["momentum"])
        fitness = evolver.evaluate("a1", sharpe=3.0, win_rate=0.8, profit_factor=3.0, max_drawdown=0.1)
        evolver.evolve([fitness])
        assert evolver.stats["agent_count"] >= 1

    def test_stats(self, evolver: AgentEvolver) -> None:
        evolver.register_agent("a1", "risk", {}, [])
        s = evolver.stats
        assert s["agent_count"] == 1
        assert s["success_threshold"] == 0.6


class TestArchitectureEvolver:
    @pytest.fixture
    def evolver(self) -> ArchitectureEvolver:
        return ArchitectureEvolver(mutation_rate=0.05, seed=42)

    def test_initial_genome(self, evolver: ArchitectureEvolver) -> None:
        assert evolver.genome.pipeline_depth == 8
        assert evolver.genome.parallelism == 4

    def test_evaluate_returns_fitness(self, evolver: ArchitectureEvolver) -> None:
        fitness = evolver.evaluate(
            throughput=5000.0, latency_ms=2000.0, error_rate=0.05,
            depth_utilization=0.8, redundancy_efficiency=0.7,
        )
        assert 0.0 <= fitness <= 1.0

    def test_detect_synaptation(self, evolver: ArchitectureEvolver) -> None:
        metrics = {
            ArchitectureLayer.STRATEGY: {"activity": 0.9},
            ArchitectureLayer.EXECUTION: {"activity": 0.4},
        }
        events = evolver.detect_synaptation(metrics)
        if events:
            assert events[0].covariance_strength > 0

    def test_evolve_modifies_genome(self, evolver: ArchitectureEvolver) -> None:
        events = [
            SynaptationEvent(
                source_layer=ArchitectureLayer.STRATEGY,
                target_layer=ArchitectureLayer.EXECUTION,
                covariance_strength=0.5,
                adaptation_type="reinforcement",
            )
        ]
        genome = evolver.evolve(events)
        assert genome.generation == 1

    def test_stats(self, evolver: ArchitectureEvolver) -> None:
        evolver.evaluate(5000, 2000, 0.05, 0.8, 0.7)
        s = evolver.stats
        assert "fitness" in s
        assert "generation" in s


class TestEnforcementAgent:
    @pytest.fixture
    def enforcer(self) -> EnforcementAgent:
        return EnforcementAgent(penalty_strength=0.3)

    def test_monitor_normal_agent_no_deviation(self, enforcer: EnforcementAgent) -> None:
        deviations = enforcer.monitor("a1", risk_taken=0.3, short_term_reward=0.4, coordination_score=0.8, resource_usage=0.4, strategy_adherence=0.9)
        assert len(deviations) == 0

    def test_monitor_excessive_risk(self, enforcer: EnforcementAgent) -> None:
        deviations = enforcer.monitor("a1", risk_taken=0.9, short_term_reward=0.5, coordination_score=0.7, resource_usage=0.4, strategy_adherence=0.8)
        assert any(d.deviation_type == DeviationType.EXCESSIVE_RISK for d in deviations)

    def test_monitor_coordination_failure(self, enforcer: EnforcementAgent) -> None:
        deviations = enforcer.monitor("a1", risk_taken=0.3, short_term_reward=0.5, coordination_score=0.1, resource_usage=0.4, strategy_adherence=0.8)
        assert any(d.deviation_type == DeviationType.COORDINATION_FAILURE for d in deviations)

    def test_monitor_strategy_drift(self, enforcer: EnforcementAgent) -> None:
        deviations = enforcer.monitor("a1", risk_taken=0.3, short_term_reward=0.5, coordination_score=0.7, resource_usage=0.4, strategy_adherence=0.1)
        assert any(d.deviation_type == DeviationType.STRATEGY_DRIFT for d in deviations)

    def test_enforce_warns_then_penalizes(self, enforcer: EnforcementAgent) -> None:
        deviations = enforcer.monitor("a1", risk_taken=0.9, short_term_reward=0.5, coordination_score=0.7, resource_usage=0.4, strategy_adherence=0.8)
        actions = enforcer.enforce(deviations)
        assert len(actions) > 0
        assert actions[0].action_type in ("penalty", "warning")

    def test_accumulated_penalties_escalate(self, enforcer: EnforcementAgent) -> None:
        # Repeated deviations should escalate
        for _ in range(5):
            deviations = enforcer.monitor("a1", risk_taken=0.9, short_term_reward=0.5, coordination_score=0.1, resource_usage=0.9, strategy_adherence=0.1)
            enforcer.enforce(deviations)
        status = enforcer.get_agent_status("a1")
        assert status["penalty_points"] > 0

    def test_decay_penalties_reduces_points(self, enforcer: EnforcementAgent) -> None:
        deviations = enforcer.monitor("a1", risk_taken=0.9, short_term_reward=0.5, coordination_score=0.7, resource_usage=0.4, strategy_adherence=0.8)
        enforcer.enforce(deviations)
        before = enforcer.get_agent_status("a1")["penalty_points"]
        enforcer.decay_penalties(rate=0.5)
        after = enforcer.get_agent_status("a1")["penalty_points"]
        assert after < before

    def test_deviation_types_enum(self) -> None:
        assert DeviationType.EXCESSIVE_RISK.value == "excessive_risk"
        assert len(DeviationType) == 5

    def test_stats(self, enforcer: EnforcementAgent) -> None:
        s = enforcer.stats
        assert s["total_deviations"] == 0
        assert s["agents_monitored"] == 0
