"""L5 Symbiotic Cluster Platform — 共生生态集群平台.

Biological Metaphor:
  森林生态系统: 数百个物种通过菌根网络、蜜蜂通信、群体感应等机制
  协作共生, 涌现出单个物种不具备的集体智能。

  Key inspirations:
    - Root Agent = Mother Tree (母树): 森林中最古老/最大的树, 通过菌根连接整个森林
    - AgentFactory = 骨髓干细胞生态位 (HSC niche)
    - ClusterCommunicator = 蜜蜂摇摆舞 + 细菌QS + 蚁群信息素 三合一通信
    - AgentPoolManager = 内分泌能量分配系统 (EAS: HPA+HPT+HPG三轴)
    - EndogenousTargetEngine = 自噬 (Autophagy): 细胞饥饿时自我消化回收资源
    - DistributedConsensus = 章鱼Confederal模型 + 蜜蜂法定人数决策
    - GlobalKnowledgeNetwork = 菌根母树网络 + 地衣全息体 (Lichen Holobiont)
    - DistributedEvolutionEngine = Symbiogenesis (共生起源) + SHARP
    - GlobalAuditTrail = 集群免疫记忆 (AIS memory)

一句话: L5是系统的"肌肉"和"共生生态"——它执行、协调、代谢、演化,
如同一个由数百个物种组成的森林生态系统。

References (2025-2026):
  - Mycorrhizal Mother Tree networks (Qarachal & Alizadeh 2025)
  - Lichen Holobiont metagenomics (BMC Biology 2025, Current Biology 2026)
  - S-MADRL: Stigmergic Multi-Agent DRL (AROB 2026)
  - Bee Quorum Sensing phase transitions (UBarcelona 2025)
  - Octopus Confederal Neural Architecture (Nature Comms 2025, PhilArchive 2025)
  - EAS: Energy Allocation System (IJMS 2026)
  - BCAA-Akh feedback loop (Nature Comms 2026)
  - Symbiogenesis theory (Margulis 1967/1993)
"""

from __future__ import annotations

from src.cluster.agent_factory import AgentFactory, AgentSpecialty, ClusterAgent
from src.cluster.communicator import ClusterCommunicator, ClusterMessage, MessageType, Pheromone
from src.cluster.pool_manager import AgentPoolManager, AgentPool, PoolState, LoadBalancer
from src.cluster.endogenous_engine import EndogenousTargetEngine, EndogenousTarget, MetabolicMode
from src.cluster.consensus import DistributedConsensus, ConsensusProposal, QuorumState
from src.cluster.knowledge_network import GlobalKnowledgeNetwork, KnowledgeNode, MemoryMetabolism
from src.cluster.distributed_evolution import DistributedEvolutionEngine, EvolutionLevel, SHAPValue
from src.cluster.global_audit import GlobalAuditTrail, ClusterAuditRecord, AnomalyDetection
from src.cluster.feedback_adaptive_bridge import (
    ClusterFeedbackBridge,
    ProprioceptiveReading,
    FeedbackAction,
    FeedbackSignal,
    MuscleTone,
)

__all__ = [
    # 4.1
    "AgentFactory", "AgentSpecialty", "ClusterAgent",
    # 4.2
    "ClusterCommunicator", "ClusterMessage", "MessageType", "Pheromone",
    # 4.3
    "AgentPoolManager", "AgentPool", "PoolState", "LoadBalancer",
    # 4.4
    "EndogenousTargetEngine", "EndogenousTarget", "MetabolicMode",
    # 4.5
    "DistributedConsensus", "ConsensusProposal", "QuorumState",
    # 4.6
    "GlobalKnowledgeNetwork", "KnowledgeNode", "MemoryMetabolism",
    # 4.7
    "DistributedEvolutionEngine", "EvolutionLevel", "SHAPValue",
    # 4.8
    "GlobalAuditTrail", "ClusterAuditRecord", "AnomalyDetection",
    # Phase 5: Cross-Layer Bridges
    "ClusterFeedbackBridge", "ProprioceptiveReading", "FeedbackAction",
    "FeedbackSignal", "MuscleTone",
]
