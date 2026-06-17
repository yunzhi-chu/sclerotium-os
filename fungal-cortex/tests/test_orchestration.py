"""Tests for Phase 3 Orchestration layer."""
import pytest
from src.orchestration.root_agent import RootAgent, RootAgentRole, AgentLifecycle
from src.orchestration.cognitive_scheduler import CognitiveScheduler, CognitiveDepth, TaskCategory, SchedulerDecision
from src.orchestration.cluster_manager import ClusterManager, Specialty, AgentStatus, SpecialtyCluster, AgentHandle


class TestRootAgent:
    @pytest.fixture
    def root(self) -> RootAgent:
        return RootAgent()

    def test_initial_state_is_lifecycle_manager(self, root: RootAgent) -> None:
        assert root.state.role == RootAgentRole.LIFECYCLE_MANAGER

    def test_set_boundaries(self, root: RootAgent) -> None:
        root.set_boundaries((0.0, 0.5), (1000.0, 1000000.0))
        assert "risk" in root.state.boundaries
        assert "capital" in root.state.boundaries
        assert root.state.role == RootAgentRole.BOUNDARY_SETTER

    def test_define_axis(self, root: RootAgent) -> None:
        root.define_axis("return", 0.0, 1.0)
        assert "return" in root.state.axes
        assert root.state.role == RootAgentRole.AXIS_DEFINER

    def test_set_constraint(self, root: RootAgent) -> None:
        root.set_constraint("max_leverage", 3.0)
        assert root.state.constraints["max_leverage"] == 3.0

    def test_check_constraint_pass(self, root: RootAgent) -> None:
        root.set_constraint("max_leverage", 3.0)
        ok, msg = root.check_constraint("max_leverage", 2.0)
        assert ok

    def test_check_constraint_violation(self, root: RootAgent) -> None:
        root.set_constraint("max_leverage", 3.0)
        ok, msg = root.check_constraint("max_leverage", 5.0)
        assert not ok

    def test_allocate_resources(self, root: RootAgent) -> None:
        alloc = root.allocate_resources({"regime": 0.3, "strategy": 0.4})
        assert root.state.role == RootAgentRole.RESOURCE_ALLOCATOR
        total = sum(alloc.values())
        assert total <= root.state.resource_budget

    def test_spawn_agent(self, root: RootAgent) -> None:
        agent_id = root.spawn_agent("strategy")
        assert agent_id in root.state.managed_agents
        assert root.state.managed_agents[agent_id]["specialty"] == "strategy"

    def test_promote_agent(self, root: RootAgent) -> None:
        agent_id = root.spawn_agent("regime")
        assert root.promote_agent(agent_id)
        assert root.state.managed_agents[agent_id]["lifecycle"] == AgentLifecycle.PROMOTING.value

    def test_apoptose_agent(self, root: RootAgent) -> None:
        agent_id = root.spawn_agent("indicator")
        assert root.apoptose_agent(agent_id)
        assert root.state.managed_agents[agent_id]["lifecycle"] == AgentLifecycle.DEAD.value

    def test_evaluate_agents_categorizes(self, root: RootAgent) -> None:
        root.spawn_agent("strategy", {"performance": 0.9})
        root.spawn_agent("risk", {"performance": 0.3})
        evals = root.evaluate_agents()
        assert "excellent" in evals
        assert "critical" in evals

    async def test_tick_apoptoses_critical(self, root: RootAgent) -> None:
        root.spawn_agent("risk", {"performance": 0.1})
        await root.tick()
        evals = root.evaluate_agents()
        assert len(evals["critical"]) == 0  # Should be apoptosed

    def test_stats(self, root: RootAgent) -> None:
        root.spawn_agent("strategy")
        s = root.stats
        assert s["managed_agents"] == 1
        assert "role" in s


class TestCognitiveScheduler:
    @pytest.fixture
    def scheduler(self) -> CognitiveScheduler:
        return CognitiveScheduler()

    def test_schedule_quick_query(self, scheduler: CognitiveScheduler) -> None:
        decision = scheduler.schedule("t1", TaskCategory.QUICK_QUERY)
        assert decision.assigned_depth == CognitiveDepth.L1_FAST
        assert decision.priority == 3

    def test_schedule_deep_research(self, scheduler: CognitiveScheduler) -> None:
        decision = scheduler.schedule("t2", TaskCategory.DEEP_RESEARCH)
        assert decision.assigned_depth == CognitiveDepth.L4_RESEARCH

    def test_time_pressure_reduces_depth(self, scheduler: CognitiveScheduler) -> None:
        decision = scheduler.schedule("t3", TaskCategory.DEEP_RESEARCH, time_pressure=0.9)
        assert decision.assigned_depth.value < CognitiveDepth.L4_RESEARCH.value

    def test_novelty_increases_depth(self, scheduler: CognitiveScheduler) -> None:
        decision = scheduler.schedule("t4", TaskCategory.SIMPLE_ANALYSIS, novelty=0.9)
        assert decision.assigned_depth.value >= CognitiveDepth.L2_BASIC.value

    def test_low_resources_reduces_depth(self, scheduler: CognitiveScheduler) -> None:
        decision = scheduler.schedule("t5", TaskCategory.DEBATE_CLAIM, resource_remaining=0.1)
        assert decision.assigned_depth.value <= CognitiveDepth.L3_DEBATE.value

    def test_meta_reflection_is_l6(self, scheduler: CognitiveScheduler) -> None:
        decision = scheduler.schedule("t6", TaskCategory.META_REFLECTION)
        assert decision.assigned_depth == CognitiveDepth.L6_META

    def test_cognitive_depth_expected_latency(self) -> None:
        assert CognitiveDepth.L1_FAST.expected_latency_ms == 200
        assert CognitiveDepth.L3_DEBATE.expected_latency_ms == 2000

    def test_get_pending_count(self, scheduler: CognitiveScheduler) -> None:
        scheduler.schedule("a", TaskCategory.QUICK_QUERY)
        scheduler.schedule("b", TaskCategory.DEEP_RESEARCH)
        assert scheduler.get_pending_count(CognitiveDepth.L2_BASIC) >= 1

    def test_stats(self, scheduler: CognitiveScheduler) -> None:
        scheduler.schedule("s1", TaskCategory.QUICK_QUERY)
        s = scheduler.stats
        assert s["total_scheduled"] == 1
        assert "recent_depth_distribution" in s


class TestClusterManager:
    @pytest.fixture
    def manager(self) -> ClusterManager:
        return ClusterManager()

    def test_five_specialty_clusters(self, manager: ClusterManager) -> None:
        assert len(manager._clusters) == 5
        assert Specialty.REGIME in manager._clusters

    def test_register_agent(self, manager: ClusterManager) -> None:
        handle = manager.register_agent(Specialty.STRATEGY)
        assert handle.specialty == Specialty.STRATEGY
        assert manager.total_agents == 1

    def test_deregister_agent(self, manager: ClusterManager) -> None:
        handle = manager.register_agent(Specialty.RISK)
        assert manager.deregister_agent(handle.agent_id)
        assert manager.total_agents == 0

    def test_route_task_to_least_loaded(self, manager: ClusterManager) -> None:
        h1 = manager.register_agent(Specialty.INDICATOR)
        h2 = manager.register_agent(Specialty.INDICATOR)
        h1.load = 0.9  # Overloaded
        h2.load = 0.1  # Lightly loaded
        h1.status = AgentStatus.BUSY
        h2.status = AgentStatus.IDLE

        best = manager.route_task(Specialty.INDICATOR, {"task": "test"})
        assert best is not None
        assert best.agent_id == h2.agent_id

    def test_elect_coordinator_three_agents(self, manager: ClusterManager) -> None:
        for _ in range(3):
            manager.register_agent(Specialty.TACTICAL)
        coordinator = manager.elect_coordinator(Specialty.TACTICAL)
        assert coordinator is not None
        cluster = manager.get_cluster(Specialty.TACTICAL)
        assert cluster.coordinator_id == coordinator

    def test_scale_up_when_high_load(self, manager: ClusterManager) -> None:
        for _ in range(3):
            h = manager.register_agent(Specialty.REGIME)
            h.load = 0.9
            h.status = AgentStatus.BUSY
        action = manager.scale_cluster(Specialty.REGIME)
        assert action in ("scale_up_1", "scale_up_2", "hold")

    def test_heartbeat(self, manager: ClusterManager) -> None:
        h = manager.register_agent(Specialty.RISK)
        assert manager.heartbeat(h.agent_id)

    def test_check_offline_agents(self, manager: ClusterManager) -> None:
        h = manager.register_agent(Specialty.STRATEGY)
        h.last_heartbeat = 0.0  # Force offline detection
        offline = manager.check_offline_agents(timeout_seconds=1.0)
        assert h.agent_id in offline

    def test_route_with_coordinator(self, manager: ClusterManager) -> None:
        for _ in range(4):
            manager.register_agent(Specialty.STRATEGY)
        manager.elect_coordinator(Specialty.STRATEGY)
        best = manager.route_task(Specialty.STRATEGY, {"task": "coordinated"})
        assert best is not None

    def test_stats(self, manager: ClusterManager) -> None:
        manager.register_agent(Specialty.INDICATOR)
        s = manager.stats
        assert s["total_agents"] == 1
        assert "clusters" in s
