"""Phase 4 L5 Cluster Smoke Test."""
import random
import time

print("=== Phase 4 L5 Cluster Smoke Test ===")
print()

# 1. Import test
print("[1/10] Testing imports...")
from src.cluster.agent_factory import AgentFactory, AgentSpecialty
from src.cluster.communicator import ClusterCommunicator, MessageType
from src.cluster.pool_manager import AgentPoolManager
from src.cluster.endogenous_engine import EndogenousTargetEngine, TargetType
from src.cluster.consensus import DistributedConsensus
from src.cluster.knowledge_network import GlobalKnowledgeNetwork, MemoryType
from src.cluster.distributed_evolution import DistributedEvolutionEngine, EvolutionLevel
from src.cluster.global_audit import GlobalAuditTrail, AuditEventType
from src.orchestration.root_agent import RootAgent
from src.cluster import __all__ as cluster_all
print(f"  [OK] All 9 modules imported ({len(cluster_all)} exports)")
print()

# 2. AgentFactory
print("[2/9] Testing AgentFactory...")
factory = AgentFactory()
agent = factory.create_agent(AgentSpecialty.STRATEGY_MINING)
assert agent is not None
print(f"  [OK] Agent: {agent.agent_id[:12]}.., specialty={agent.specialty.value}")

agent2 = factory.get_or_create(AgentSpecialty.RISK_CONTROL)
assert agent2 is not None
census = factory.count_by_specialty()
print(f"  [OK] Census: {census}")
print(f"  [OK] Stats: {factory.stats}")
print()

# 3. ClusterCommunicator
print("[3/9] Testing ClusterCommunicator...")
comm = ClusterCommunicator()
msg = comm.send(MessageType.TASK_ASSIGN, "agent_1", {"task": "backtest AAPL"})
print(f"  [OK] Message: {msg.msg_id[:12]}..")

phero = comm.deposit_pheromone("knowledge", "topic:regime_detection", 1.0, "agent_1")
print(f"  [OK] Pheromone: {phero.pheromone_id[:12]}..")

sniffed = comm.sniff("topic:regime_detection")
print(f"  [OK] Sniffed: {len(sniffed)} pheromones")

qs_result = comm.qs_activate("test_signal")
print(f"  [OK] QS: {qs_result}")
print()

# 4. AgentPoolManager
print("[4/9] Testing AgentPoolManager...")
pool_mgr = AgentPoolManager(communicator=comm)
pool_mgr.register_pool(AgentSpecialty.STRATEGY_MINING, max_size=10)
pool_mgr.add_agent(agent)

assigned = pool_mgr.assign_task("strategy_mining", "task_001")
print(f"  [OK] Task assigned to: {assigned}")

pool_mgr.complete_task("strategy_mining", agent.agent_id, 0.85)
print(f"  [OK] Pool stats: {pool_mgr.stats}")
print()

# 5. EndogenousTargetEngine
print("[5/9] Testing EndogenousTargetEngine...")
engine = EndogenousTargetEngine()
result = engine.evaluate(0.4, "neutral")
print(f"  [OK] Evaluation: triggered={result['triggered']}")

if result["triggered"]:
    target = engine.execute_next()
    if target:
        print(f"  [OK] Target: {target.target_type.value} -> {target.description[:50]}...")
        engine.complete(target.target_id, True)
print(f"  [OK] Stats: {engine.stats}")
print()

# 6. DistributedConsensus
print("[6/9] Testing DistributedConsensus...")
consensus = DistributedConsensus()
proposal = consensus.propose("system_config", "Update risk parameters", ["option_a", "option_b", "option_c"], "root_agent")
consensus.vote(proposal.proposal_id, "voter_1", "option_a", 0.9, "regime_research")
consensus.vote(proposal.proposal_id, "voter_2", "option_a", 0.8, "risk_control")
consensus.vote(proposal.proposal_id, "voter_3", "option_b", 0.7, "tactics_research")
consensus.vote(proposal.proposal_id, "voter_4", "option_a", 0.85, "strategy_mining")

tally = consensus.tally(proposal.proposal_id)
print(f"  [OK] Tally: state={tally['state']}, winner={tally.get('winner', 'N/A')}")
print()

# 7. GlobalKnowledgeNetwork
print("[7/9] Testing GlobalKnowledgeNetwork...")
gkn = GlobalKnowledgeNetwork()
node = gkn.sync_from_agent("agent_1", {"key": "regime_pattern", "data": [0.1, 0.3, 0.5]}, MemoryType.SEMANTIC, 0.02)
if node:
    print(f"  [OK] Node: {node.node_id[:12]}.., score={node.score:.3f}")

results = gkn.query({"key": "regime_pattern"}, top_k=3)
print(f"  [OK] Query: {len(results)} results")

stats = gkn.get_network_stats()
print(f"  [OK] Network: {stats}")
print()

# 8. DistributedEvolutionEngine
print("[8/9] Testing DistributedEvolutionEngine...")
evo = DistributedEvolutionEngine()
evo.register_strategy("strat_1", {"alpha": 0.5, "beta": 0.3, "gamma": 0.1})

mutated = evo.micro_evolve("strat_1", 0.05)
if mutated:
    print(f"  [OK] Micro-evolved: {mutated}")

shapley = evo.compute_shapley(
    ["indicator_A", "indicator_B", "indicator_C"],
    baseline_fn=lambda ids: sum(abs(hash(i)) % 100 / 1000 for i in ids),
    eval_fn=lambda e, ids: sum(abs(hash(i + e)) % 100 / 1000 for i in ids) * 1.1,
)
print(f"  [OK] SHAP values: top={shapley[0].entity_id} ({shapley[0].shapley_value:.4f})")
print(f"  [OK] Stats: {evo.stats}")
print()

# 9. GlobalAuditTrail + RootAgent upgrade
print("[9/9] Testing GlobalAuditTrail + RootAgent...")
audit = GlobalAuditTrail()
rec = audit.record(AuditEventType.AGENT_CREATED, "agent_1", {"specialty": "strategy_mining"}, trace_id="trace_001")
print(f"  [OK] Record: {rec.record_id[:12]}..")

anomalies = audit.detect_anomalies("agent_1", {"param_a": 0.99, "param_b": 0.5})
print(f"  [OK] Anomalies: {len(anomalies)}")

integrity = audit.verify_integrity()
print(f"  [OK] Integrity: valid={integrity['valid']}")

# RootAgent v4.0 upgrade
root = RootAgent()
root.set_constraint("max_agents", 500)
root.set_constraint("max_cpu_percent", 80.0)

# Batch task
tasks = [
    {"specialty": "regime", "payload": {"action": "scan"}, "priority": 5},
    {"specialty": "strategy", "payload": {"action": "optimize"}, "priority": 3},
]
batch_result = root.submit_batch_task(tasks, dag_id="dag_001")
print(f"  [OK] Batch: assigned={batch_result['assigned']}")

# Aggregate results
agg = root.aggregate_results([
    {"agent_id": "a1", "value": 42.0, "confidence": 0.9},
    {"agent_id": "a2", "value": 40.0, "confidence": 0.8},
    {"agent_id": "a3", "value": 44.0, "confidence": 0.7},
], method="weighted")
print(f"  [OK] Aggregate: result={agg['result']:.2f}, conf={agg['confidence']:.3f}")

# Carrying capacity
capacity = root.enforce_carrying_capacity()
print(f"  [OK] Carrying capacity: within={capacity['within_capacity']}")

# Cluster broadcast
broadcast = root.get_cluster_state_for_broadcast()
print(f"  [OK] Broadcast: agents={broadcast['managed_count']}, specs={len(broadcast['agent_distribution'])}")
print()

print("=== ALL 9 TESTS PASSED ===")
print(f"Modules: {len(cluster_all)} exported from src.cluster")
print("smoke test complete.")
