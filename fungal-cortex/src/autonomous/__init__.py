"""L4 Spinal Cord + Brainstem Autonomous Middleware — 脊髓+脑干自治中台.

Biological Metaphor:
  脊髓: 不经过大脑的反射弧(膝跳反射)——快速、自动、不占用意识资源
  自主神经系统: 交感(战斗/逃跑)+副交感(休息/消化)——自动调节内脏功能
  Physarum黏菌: 最小作用量路径优化——没有大脑但能找到最短路径
  蚁群信息素: 间接通信(Stigmergy)——审计追踪=信息素沉积
  海马体: 情景记忆编码+检索——因果追溯=记忆回溯
  蛋白质折叠: 构象催化——演化版本通过构象"传染"传播

一句话: L4是系统的"脊髓"和"自主神经"——它不思考,
但自动完成任务的编排、执行、审计、演化, 如同你不需要思考如何呼吸。

Sub-modules:
  M1: IntentParser + TaskDAGBuilder + ConflictDetector (丘脑→运动皮层)
  M2: TransactionManager + CircuitBreakerBridge (自主神经系统)
  M3: AuditTrail + CausalTracer + Counterfactual (Stigmergy + 海马体 + 前额叶)
  M4: OnlineEvolutionEngine + StrategyValidator (双循环可塑性 + 朊病毒检测)
  M5: VectorRetrieval + FinancialKG + MemoryWeaving (嗅觉记忆 + 菌根网络 + REM睡眠)
  M6: PolicyEngine + BehaviorMonitor (内环境稳态 + 内感受网络)

References (2025-2026):
  - Physarum Lagrangian (arXiv:2511.08531, Nov 2025)
  - S-MADRL: Stigmergic Multi-Agent DRL (AROB 2026)
  - HAIS-IDS (Singh & Arora 2025)
  - Maury (2025), "Amyloid world hypothesis", FEBS Letters 599:2693-2705
  - Hippocampal replay & pattern completion
  - Mycorrhizal bidirectional C/N transfer (Frontiers 2025)
  - Thyroid as Dual Governor (Zenodo 2026)
  - Insula+ACC interoception theory (Craig 2002, Barrett 2017)
"""

from __future__ import annotations

# M1: Intent + DAG
from src.autonomous.intent_parser import IntentParser, Intent, IntentType
from src.autonomous.task_dag import TaskDAGBuilder, TaskNode, TaskDAG
from src.autonomous.conflict_detector import ConflictDetector, Conflict, ConflictType

# M2: Transaction + Circuit
from src.autonomous.transaction_manager import TransactionManager, Transaction, TxState
from src.autonomous.circuit_breaker_bridge import CircuitBreakerBridge, BreakerState

# M3: Audit + Causal + Counterfactual
from src.autonomous.audit_trail import AuditTrail, AuditRecord, AuditSeverity
from src.autonomous.causal_tracer import CausalTracer, CausalLink, CausalChain
from src.autonomous.counterfactual import CounterfactualEngine, Scenario

# M4: Evolution + Validation
from src.autonomous.online_evolution import OnlineEvolutionEngine, EvolutionLevel
from src.autonomous.strategy_validator import StrategyAutoValidator, ValidationReport

# M5: Vector + KG + Memory
from src.autonomous.vector_retrieval import VectorRetrievalEngine, DistanceMetric
from src.autonomous.financial_kg import FinancialKnowledgeGraph, EntityNode, RelationType
from src.autonomous.memory_weaving import MemoryWeaving, WorkingMemory, MemoryConsolidation

# M6: Policy + Behavior
from src.autonomous.policy_engine import PolicyEngine, PolicyRule, RulePriority
from src.autonomous.behavior_monitor import BehaviorMonitor, BehaviorProfile, AnomalyAlert

# Phase 5: Cross-Layer Bridges
from src.autonomous.immune_audit_bridge import ImmuneAuditBridge, SpleenRecord, ClaimFate
from src.autonomous.dag_cluster_bridge import DAGClusterBridge, ClusterTask, DAGDecomposition, TaskPhase, RedundancyLevel

__all__ = [
    # M1
    "IntentParser", "Intent", "IntentType",
    "TaskDAGBuilder", "TaskNode", "TaskDAG",
    "ConflictDetector", "Conflict", "ConflictType",
    # M2
    "TransactionManager", "Transaction", "TxState",
    "CircuitBreakerBridge", "BreakerState",
    # M3
    "AuditTrail", "AuditRecord", "AuditSeverity",
    "CausalTracer", "CausalLink", "CausalChain",
    "CounterfactualEngine", "Scenario",
    # M4
    "OnlineEvolutionEngine", "EvolutionLevel",
    "StrategyAutoValidator", "ValidationReport",
    # M5
    "VectorRetrievalEngine", "DistanceMetric",
    "FinancialKnowledgeGraph", "EntityNode", "RelationType",
    "MemoryWeaving", "WorkingMemory", "MemoryConsolidation",
    # M6
    "PolicyEngine", "PolicyRule", "RulePriority",
    "BehaviorMonitor", "BehaviorProfile", "AnomalyAlert",
    # Phase 5: Cross-Layer Bridges
    "ImmuneAuditBridge", "SpleenRecord", "ClaimFate",
    "DAGClusterBridge", "ClusterTask", "DAGDecomposition", "TaskPhase", "RedundancyLevel",
]
