"""L9: Edge Mesh + Quantum Bridge (Phase 5 v4.0).

Biological Metaphor:
  Photosynthesis + Internet BGP — quantum coherence for parallel policy
  evaluation, DHT-based P2P for decentralized knowledge sharing.
"""

from src.l9.p2p_mesh import (
    AggregatedKnowledge,
    GossipMessage,
    KnowledgeVector,
    NetworkIdentity,
    P2PMeshConfig,
    PeerNode,
    PeerToPeerMesh,
)
from src.l9.hybrid_quantum_agent import (
    ActionDistribution,
    AnnealingSolution,
    ClassicalCritic,
    HybridQuantumAgent,
    HybridQuantumConfig,
    QuantumActor,
    QuantumCircuit,
    QuantumTrainingResult,
)

__all__ = [
    # P2P Mesh
    "PeerToPeerMesh",
    "P2PMeshConfig",
    "NetworkIdentity",
    "PeerNode",
    "KnowledgeVector",
    "AggregatedKnowledge",
    "GossipMessage",
    # Hybrid Quantum
    "HybridQuantumAgent",
    "HybridQuantumConfig",
    "QuantumActor",
    "QuantumCircuit",
    "ClassicalCritic",
    "ActionDistribution",
    "QuantumTrainingResult",
    "AnnealingSolution",
]
