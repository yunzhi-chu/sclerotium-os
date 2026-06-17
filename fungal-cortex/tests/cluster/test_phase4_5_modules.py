"""Tests for Phase 4 cluster modules + Phase 5.4 feedback bridge."""
import pytest
from src.cluster.agent_factory import AgentFactory, AgentSpecialty
from src.cluster.communicator import ClusterCommunicator, MessageType
from src.cluster.pool_manager import AgentPoolManager
from src.cluster.endogenous_engine import EndogenousTargetEngine, MetabolicMode
from src.cluster.consensus import DistributedConsensus
from src.cluster.knowledge_network import GlobalKnowledgeNetwork
from src.cluster.distributed_evolution import DistributedEvolutionEngine
from src.cluster.global_audit import GlobalAuditTrail
from src.cluster.feedback_adaptive_bridge import (
    ClusterFeedbackBridge, ProprioceptiveReading, FeedbackSignal, MuscleTone,
)


class TestAgentFactory:
    def test_create_agent(self):
        af = AgentFactory(max_agents=50, max_memory_mb=512, max_cpu_percent=50)
        agent = af.create_agent(AgentSpecialty.STRATEGY_MINING)
        assert agent is not None
        assert agent.specialty == AgentSpecialty.STRATEGY_MINING

    def test_constrain_resources(self):
        af = AgentFactory(max_agents=50, max_memory_mb=512)
        result = af.constrain_resources()
        assert result is not None

    def test_report_stats(self):
        af = AgentFactory(max_agents=50, max_memory_mb=512, max_cpu_percent=50)
        agent = af.create_agent(AgentSpecialty.STRATEGY_MINING)
        s = af.stats
        assert s["total_agents"] >= 1


class TestClusterCommunicator:
    def test_send_and_receive(self):
        comm = ClusterCommunicator()
        msg = comm.send(MessageType.TASK_ASSIGN, "agent-1", {"task": "test"}, priority=3)
        assert msg is not None
        assert msg.msg_type == MessageType.TASK_ASSIGN

    def test_broadcast(self):
        comm = ClusterCommunicator()
        comm.subscribe("agent-2", "test.topic")
        comm.broadcast(MessageType.KNOWLEDGE_SYNC, "agent-1", {"data": "x"})
        assert len(comm._messages) >= 1

    def test_pheromone_deposit_and_sniff(self):
        comm = ClusterCommunicator()
        comm.deposit_pheromone("task", "task-queue", 0.8, "agent-1")
        results = comm.sniff("task-queue", ptype="task")
        assert len(results) > 0

    def test_quorum_check(self):
        comm = ClusterCommunicator(quorum_threshold=0.6)
        comm.emit_qs_signal("test_qs", 0.3)
        comm.emit_qs_signal("test_qs", 0.4)
        reached = comm.check_quorum("test_qs")
        # 0.3+0.4=0.7 > 0.6 threshold
        assert reached


class TestAgentPoolManager:
    def test_register_pool(self):
        apm = AgentPoolManager()
        pool = apm.register_pool(AgentSpecialty.STRATEGY_MINING, 10)
        assert pool is not None
        assert pool.max_size == 10

    def test_add_agent(self):
        apm = AgentPoolManager()
        apm.register_pool(AgentSpecialty.STRATEGY_MINING, 10)
        from src.cluster.agent_factory import AgentFactory
        af = AgentFactory(max_agents=50, max_memory_mb=512, max_cpu_percent=50)
        agent = af.create_agent(AgentSpecialty.STRATEGY_MINING)
        ok = apm.add_agent(agent)
        assert ok


class TestEndogenousEngine:
    def test_evaluate(self):
        ee = EndogenousTargetEngine()
        targets = ee.evaluate(system_utilization=0.4, market_regime="bear")
        assert targets is not None

    def test_metabolic_modes(self):
        ee = EndogenousTargetEngine()
        # After evaluation with low utilization, mode should be set
        ee.evaluate(system_utilization=0.3, market_regime="bear")
        assert ee.mode is not None
        assert ee.mode.value in ("fed", "fasting", "exercise", "recovery")


class TestDistributedConsensus:
    def test_propose_and_vote(self):
        dc = DistributedConsensus()
        proposal = dc.propose("test_topic", "Change param alpha", ["approve", "reject"], "agent-1")
        assert proposal is not None
        dc.vote(proposal.proposal_id, "agent-1", "approve", 0.8, "risk")

    def test_tally(self):
        dc = DistributedConsensus()
        p = dc.propose("test_topic", "Test proposal", ["approve", "reject"], "a1")
        dc.vote(p.proposal_id, "a1", "approve", 0.7, "risk")
        dc.vote(p.proposal_id, "a2", "approve", 0.8, "strategy")
        dc.vote(p.proposal_id, "a3", "approve", 0.6, "tech")
        result = dc.tally(p.proposal_id)
        assert result is not None


class TestGlobalKnowledgeNetwork:
    def test_sync_and_query(self):
        gkn = GlobalKnowledgeNetwork()
        gkn.sync_from_agent("agent-1", {"key": "MACD_params", "pnl_impact": 0.5, "use_count": 50})
        results = gkn.query({"keyword": "MACD"})
        assert results is not None


class TestDistributedEvolution:
    def test_micro_evolve(self):
        de = DistributedEvolutionEngine()
        # First seed a strategy, then evolve it
        de._strategies["strat-1"] = {
            "params": {"sharpe": 0.5, "win_rate": 0.4},
            "fitness": 0.5,
            "generation": 0,
            "specialty": "strategy",
        }
        result = de.micro_evolve("strat-1", fitness_delta=0.1)
        assert result is not None

    def test_compute_shapley(self):
        de = DistributedEvolutionEngine()
        def baseline_fn(coalition):
            return sum(1.0 for _ in coalition)
        def eval_fn(entity, coalition):
            return len(coalition) * 0.3
        values = de.compute_shapley(["a1", "a2", "a3"], baseline_fn, eval_fn)
        assert len(values) == 3


class TestGlobalAuditTrail:
    def test_record_and_verify(self):
        gat = GlobalAuditTrail()
        from src.cluster.global_audit import AuditEventType
        gat.record(AuditEventType.AGENT_CREATED, "cluster", {"agent_id": "a1"}, "t1")
        integrity = gat.verify_integrity()
        assert integrity["valid"]

    def test_anomaly_detection(self):
        gat = GlobalAuditTrail()
        from src.cluster.global_audit import AuditEventType
        for i in range(60):
            gat.record(AuditEventType.AGENT_CREATED, f"agent_{i}", {"i": i}, f"trace_{i}")
        result = gat.verify_integrity()
        assert result is not None


class TestClusterFeedbackBridge:
    def test_danger_safety_tighten(self):
        bridge = ClusterFeedbackBridge(sharpe_danger_threshold=0.0, cooldown_period=0.0)
        reading = ProprioceptiveReading(
            reading_id="r1", source="test",
            sharpe_ratio=-0.5, win_rate=0.35, success_rate=0.5,
            agent_count=10, failure_count=5,
            specialty_performance={"strategy": 0.3},
            specialty_failures={"strategy": 4},
        )
        actions = bridge.sense(reading)
        signals = [a.signal for a in actions]
        assert FeedbackSignal.SAFETY_TIGHTEN in signals

    def test_healthy_scenario(self):
        bridge = ClusterFeedbackBridge(cooldown_period=0.0)
        reading = ProprioceptiveReading(
            reading_id="r2", source="test",
            sharpe_ratio=1.5, win_rate=0.7, success_rate=0.95,
            agent_count=10, failure_count=0,
        )
        bridge._muscle_tone = MuscleTone.HYPERTONIC
        actions = bridge.sense(reading)
        assert len(actions) >= 1

    def test_sense_from_stats(self):
        bridge = ClusterFeedbackBridge(cooldown_period=0.0)
        actions = bridge.sense_from_stats(
            sharpe=-0.3, win_rate=0.4, success_rate=0.5,
            agent_count=8, failure_count=4,
            specialty_perf={"strategy": 0.3},
            specialty_fail={"strategy": 4},
        )
        assert len(actions) > 0

    def test_l0_adjustment_summary(self):
        bridge = ClusterFeedbackBridge(cooldown_period=0.0)
        bridge.sense_from_stats(-0.3, 0.4, 0.5, 8, 4)
        summary = bridge.get_l0_adjustment_summary()
        assert "muscle_tone" in summary
        assert "adjustments" in summary
