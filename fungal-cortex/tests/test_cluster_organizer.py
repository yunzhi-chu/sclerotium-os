"""Tests for M3: Cluster Self-Organizer."""

import pytest

from src.l6.cluster_organizer import (
    AgentPerformance,
    AgentSpecialty,
    AgentVerdict,
    ClusterSelfOrganizer,
)


class TestAgentVerdict:
    def test_enum_values(self) -> None:
        assert AgentVerdict.EXCELLENT.value == "excellent"
        assert AgentVerdict.CRITICAL.value == "critical"
        assert len(AgentVerdict) == 5


class TestClusterSelfOrganizer:
    @pytest.fixture
    def organizer(self) -> ClusterSelfOrganizer:
        org = ClusterSelfOrganizer(
            success_weight=0.35,
            efficiency_weight=0.25,
            quality_weight=0.25,
            resource_weight=0.15,
            excellent_threshold=0.85,
            underperforming_threshold=0.40,
            underperforming_strikes=3,
        )
        for i in range(5):
            spec = list(AgentSpecialty)[i]
            org.register_agent(f"agent-{i}", spec)
        return org

    def test_register_agent(self, organizer: ClusterSelfOrganizer) -> None:
        organizer.register_agent("test-1", AgentSpecialty.STRATEGY_MINING)
        assert "test-1" in organizer.get_active_agents()

    def test_evaluate_all_agents(self, organizer: ClusterSelfOrganizer) -> None:
        results = organizer.evaluate_all_agents(
            success_rates={"agent-0": 0.9, "agent-1": 0.5, "agent-2": 0.3, "agent-3": 0.95, "agent-4": 0.2},
            efficiency_scores={"agent-0": 0.8, "agent-1": 0.6, "agent-2": 0.4, "agent-3": 0.9, "agent-4": 0.3},
            quality_scores={"agent-0": 0.85, "agent-1": 0.5, "agent-2": 0.35, "agent-3": 0.9, "agent-4": 0.25},
            resource_usages={"agent-0": 0.2, "agent-1": 0.4, "agent-2": 0.6, "agent-3": 0.1, "agent-4": 0.8},
        )
        assert len(results) == 5
        assert all(isinstance(r.overall, float) for r in results)

    def test_excellent_agent_verdict(self) -> None:
        org = ClusterSelfOrganizer(excellent_threshold=0.85)
        assert org._verdict(0.90) == AgentVerdict.EXCELLENT

    def test_good_agent_verdict(self) -> None:
        org = ClusterSelfOrganizer()
        assert org._verdict(0.75) == AgentVerdict.GOOD

    def test_adequate_agent_verdict(self) -> None:
        org = ClusterSelfOrganizer()
        assert org._verdict(0.50) == AgentVerdict.ADEQUATE

    def test_underperforming_agent_verdict(self) -> None:
        org = ClusterSelfOrganizer(underperforming_threshold=0.40)
        assert org._verdict(0.30) == AgentVerdict.UNDERPERFORMING

    def test_critical_agent_verdict(self) -> None:
        org = ClusterSelfOrganizer(underperforming_threshold=0.40)
        assert org._verdict(0.15) == AgentVerdict.CRITICAL

    def test_reorganize_excellent_promoted(self, organizer: ClusterSelfOrganizer) -> None:
        results = organizer.evaluate_all_agents(
            success_rates={"agent-3": 0.95},
            efficiency_scores={"agent-3": 0.9},
            quality_scores={"agent-3": 0.95},
            resource_usages={"agent-3": 0.1},
        )
        actions = organizer.reorganize(results)
        assert "agent-3" in actions["promoted"]

    def test_reorganize_underperforming_destroyed(self, organizer: ClusterSelfOrganizer) -> None:
        # Simulate 3 consecutive underperforming evaluations
        for _ in range(3):
            results = organizer.evaluate_all_agents(
                success_rates={"agent-4": 0.1},
                efficiency_scores={"agent-4": 0.1},
                quality_scores={"agent-4": 0.1},
                resource_usages={"agent-4": 0.9},
            )
        actions = organizer.reorganize(results)
        assert "agent-4" in actions["destroyed"]

    def test_reorganize_spawns_replacement(self, organizer: ClusterSelfOrganizer) -> None:
        # Make agent-4 underperforming 3 times
        for _ in range(3):
            results = organizer.evaluate_all_agents(
                success_rates={"agent-4": 0.1},
                efficiency_scores={"agent-4": 0.1},
                quality_scores={"agent-4": 0.1},
                resource_usages={"agent-4": 0.9},
            )
        actions = organizer.reorganize(results)
        assert len(actions["spawned"]) > 0

    def test_strike_reset_on_good_performance(self, organizer: ClusterSelfOrganizer) -> None:
        # One bad eval
        organizer.evaluate_all_agents(
            success_rates={"agent-0": 0.1},
            efficiency_scores={"agent-0": 0.1},
            quality_scores={"agent-0": 0.1},
            resource_usages={"agent-0": 0.9},
        )
        assert organizer._strike_counts["agent-0"] == 1
        # One good eval resets
        organizer.evaluate_all_agents(
            success_rates={"agent-0": 0.9},
            efficiency_scores={"agent-0": 0.9},
            quality_scores={"agent-0": 0.9},
            resource_usages={"agent-0": 0.1},
        )
        assert organizer._strike_counts["agent-0"] == 0

    def test_optimize_topology_creates_coordinator(self, organizer: ClusterSelfOrganizer) -> None:
        # Register 3 agents of same specialty
        for i in range(5, 8):
            organizer.register_agent(f"agent-{i}", AgentSpecialty.REGIME_RESEARCH)
        organizer.evaluate_all_agents(
            success_rates={f"agent-{i}": 0.7 for i in range(8)},
            efficiency_scores={f"agent-{i}": 0.7 for i in range(8)},
            quality_scores={f"agent-{i}": 0.7 for i in range(8)},
            resource_usages={f"agent-{i}": 0.3 for i in range(8)},
        )
        topology = organizer.optimize_topology()
        # regime_research should have a coordinator (3+ agents)
        assert len(topology.coordinators) >= 1

    def test_optimize_topology_small_group_no_coordinator(self, organizer: ClusterSelfOrganizer) -> None:
        topology = organizer.optimize_topology()
        # Each specialty has only 1 agent → no coordinator needed
        assert len(topology.coordinators) == 0

    def test_get_agent_history(self, organizer: ClusterSelfOrganizer) -> None:
        organizer.evaluate_all_agents(
            success_rates={"agent-0": 0.8},
            efficiency_scores={"agent-0": 0.8},
            quality_scores={"agent-0": 0.8},
            resource_usages={"agent-0": 0.2},
        )
        history = organizer.get_agent_history("agent-0")
        assert len(history) >= 1
        assert history[0].verdict == AgentVerdict.GOOD

    def test_stats(self, organizer: ClusterSelfOrganizer) -> None:
        s = organizer.stats
        assert s["total_agents"] == 5
        assert s["active_agents"] == 5
        assert s["generation"] == 0

    def test_agent_performance_dataclass(self) -> None:
        perf = AgentPerformance(
            agent_id="test",
            specialty=AgentSpecialty.RISK_CONTROL,
            success_rate=0.8,
            efficiency=0.7,
            quality=0.75,
            resource_usage=0.3,
            overall=0.72,
            verdict=AgentVerdict.GOOD,
        )
        assert perf.specialty == AgentSpecialty.RISK_CONTROL
