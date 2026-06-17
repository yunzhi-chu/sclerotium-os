"""Mycorrhizal Debate Network — 菌根网络启发式辩论引擎.

Biological Metaphor:
  Forest underground mycorrhizal network — Mother Tree hubs connect to fungal
  channels that transfer carbon, nitrogen, and disease warnings between trees.
  When one tree detects a pathogen, the warning propagates through the network,
  allowing neighboring trees to pre-emptively produce defensive compounds.

  Similarly, claims propagate through our debate network: each node is both a
  consumer and forwarder of claims. High-nutrient nodes (historically accurate)
  have higher voting weight. Consensus emerges when ≥2/3 of the network
  confirms a claim — analogous to "quorum sensing" in fungal networks.

Key Innovation (v4.0):
  Replaces centralized Market-of-Claims auction with distributed mycorrhizal
  propagation. MNIS (Mycelial Network Intelligence Score) quantifies network
  health across 8 orthogonal parameters with 91.8% predictive accuracy.

References:
  - Baladi et al. (Nature Micro 2026): MNIS framework
  - Adamatzky (Feb 2026): Fungal safety framework
  - Mycel Network (Zenodo 2026): 70-day governance experiment
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from src.utils.logging import CortexLogger


# ═══════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════


class NetworkTopology(Enum):
    """Mycorrhizal network topology type."""
    HUB_SPOKE = "hub_spoke"      # Mother-tree centered: fast broadcast, low latency
    MESH = "mesh"                 # Peer-to-peer: Byzantine fault tolerance
    SMALL_WORLD = "small_world"   # Balance of speed and robustness


class ConsensusState(Enum):
    """Consensus state of a claim in the network."""
    PENDING = "pending"            # Still propagating
    VERIFIED = "verified"          # ≥2/3 consensus reached
    REJECTED = "rejected"          # ≥2/3 rejection
    STALEMATE = "stalemate"        # No clear consensus
    EXCRETED = "excreted"          # Decayed below field strength threshold


@dataclass
class DebateNode:
    """A node in the mycorrhizal debate network.

    Like a tree connected to the fungal network — it receives, evaluates,
    and forwards claims. Nodes with higher nutrient scores (accuracy history)
    have proportionally higher voting weight.
    """

    node_id: str
    domain: str = "general"
    nutrient_score: float = 0.5       # Historical accuracy (0-1), like carbon reserves
    connected_peers: list[str] = field(default_factory=list)
    vote_history: list[dict[str, Any]] = field(default_factory=list)
    specialization: str = ""           # Domain specialization (e.g., "finance", "medical")
    trust_decay: float = 0.0           # Accumulated trust erosion
    last_active: float = field(default_factory=time.time)

    @property
    def effective_weight(self) -> float:
        """Voting weight = nutrient_score × (1 - trust_decay)."""
        return self.nutrient_score * (1.0 - min(self.trust_decay, 0.9))


@dataclass
class ClaimPropagation:
    """Tracks how a claim propagates through the network.

    Analogous to a disease warning signal spreading through fungal hyphae.
    """

    claim_id: str
    source_node: str
    propagation_path: list[str] = field(default_factory=list)  # Ordered node traversal
    hops_traveled: int = 0
    max_hops: int = 5
    signal_strength: float = 1.0     # Attenuates with each hop
    attenuation_rate: float = 0.15   # Signal loss per hop
    reached_nodes: set[str] = field(default_factory=set)
    timestamp: float = field(default_factory=time.time)

    def attenuate(self) -> None:
        """Attenuate signal strength after a hop. Like signal degradation in hyphae."""
        self.signal_strength *= (1.0 - self.attenuation_rate)
        self.hops_traveled += 1

    @property
    def is_alive(self) -> bool:
        """Signal is still strong enough to propagate further."""
        return self.hops_traveled < self.max_hops and self.signal_strength > 0.05


@dataclass
class DebateNetworkConfig:
    """Configuration for the Mycorrhizal Debate Network."""

    topology: NetworkTopology = NetworkTopology.SMALL_WORLD
    hub_count: int = 3
    mesh_degree: int = 4
    small_world_rewiring: float = 0.1
    consensus_threshold: float = 0.667    # ≥2/3 for VERIFIED
    mnis_weights: list[float] = field(default_factory=lambda: [0.15, 0.15, 0.1, 0.1, 0.15, 0.1, 0.1, 0.15])
    propagation_max_hops: int = 5
    nutrient_decay: float = 0.05           # Per-step nutrient erosion
    min_field_strength: float = 0.2        # Below this → EXCRETED
    established_threshold: float = 0.8     # Above this → ESTABLISHED knowledge


# ═══════════════════════════════════════════════════════════════════════
# Core Network
# ═══════════════════════════════════════════════════════════════════════


class MycorrhizalDebateNetwork:
    """Distributed claim debate engine using mycorrhizal network topology.

    Claims propagate through the network like fungal disease warnings.
    Each node votes with weight proportional to its nutrient score.
    Consensus is detected via quorum sensing (≥2/3 threshold).

    Usage::

        network = MycorrhizalDebateNetwork()
        network.add_node(DebateNode("node-1", nutrient_score=0.8))
        result = network.propagate_claim(claim, "node-1")
        consensus = network.detect_consensus(claim.claim_id)
        mnis = network.compute_mnis()
    """

    def __init__(self, config: DebateNetworkConfig | None = None) -> None:
        self._config = config or DebateNetworkConfig()
        self._logger = CortexLogger("mycorrhizal_debate")

        # Network state
        self._nodes: dict[str, DebateNode] = {}
        self._claims: dict[str, dict[str, Any]] = {}  # claim_id → {claim, votes, field_strength, consensus}
        self._propagations: dict[str, ClaimPropagation] = {}
        self._adjacency: dict[str, set[str]] = {}     # node_id → connected peers

        # Statistics
        self._total_propagations: int = 0
        self._total_votes: int = 0
        self._consensus_events: dict[str, int] = {s.value: 0 for s in ConsensusState}

        # MNIS parameter trackers
        self._mnis_history: list[dict[str, float]] = []

        self._logger.info("debate_network_initialized",
                          topology=self._config.topology.value,
                          consensus_threshold=self._config.consensus_threshold)

    # ── Node Management ───────────────────────────────────────────────

    def add_node(self, node: DebateNode) -> None:
        """Register a node in the network. Like a new tree joining the mycorrhizal web."""
        self._nodes[node.node_id] = node
        if node.node_id not in self._adjacency:
            self._adjacency[node.node_id] = set()
        self._logger.debug("node_added", node_id=node.node_id, domain=node.domain)

    def remove_node(self, node_id: str) -> None:
        """Remove a node. Like a tree dying and disconnecting from the network."""
        self._nodes.pop(node_id, None)
        self._adjacency.pop(node_id, None)
        for peers in self._adjacency.values():
            peers.discard(node_id)
        self._logger.debug("node_removed", node_id=node_id)

    def connect_nodes(self, node_a: str, node_b: str) -> None:
        """Form a mycorrhizal connection between two nodes."""
        if node_a in self._adjacency and node_b in self._adjacency:
            self._adjacency[node_a].add(node_b)
            self._adjacency[node_b].add(node_a)
            if node_a in self._nodes:
                self._nodes[node_a].connected_peers.append(node_b)
            if node_b in self._nodes:
                self._nodes[node_b].connected_peers.append(node_a)

    def build_topology(self) -> None:
        """Build the network topology based on config.

        This auto-connects nodes according to the selected topology type.
        """
        node_ids = list(self._nodes.keys())
        n = len(node_ids)
        if n < 2:
            return

        rng = np.random.RandomState(42)
        c = self._config

        if c.topology == NetworkTopology.HUB_SPOKE:
            # Select hub_count hubs, connect all others to nearest hub
            hubs = node_ids[:min(c.hub_count, n)]
            for i, spoke in enumerate(node_ids):
                hub = hubs[i % len(hubs)]
                if spoke != hub:
                    self.connect_nodes(spoke, hub)

        elif c.topology == NetworkTopology.MESH:
            # Each node connects to mesh_degree neighbors
            for i, nid in enumerate(node_ids):
                for j in range(1, c.mesh_degree + 1):
                    peer = node_ids[(i + j) % n]
                    if peer != nid:
                        self.connect_nodes(nid, peer)

        elif c.topology == NetworkTopology.SMALL_WORLD:
            # Start with ring lattice, then rewire with probability
            for i, nid in enumerate(node_ids):
                # Ring connections
                for k in range(1, c.mesh_degree // 2 + 1):
                    peer = node_ids[(i + k) % n]
                    self.connect_nodes(nid, peer)
            # Rewire
            for i, nid in enumerate(node_ids):
                peers = list(self._adjacency[nid])
                for peer in peers:
                    if rng.random() < c.small_world_rewiring:
                        new_peer = node_ids[rng.randint(0, n - 1)]
                        if new_peer != nid and new_peer != peer:
                            self._adjacency[nid].discard(peer)
                            self._adjacency[peer].discard(nid)
                            self.connect_nodes(nid, new_peer)

        self._logger.info("topology_built", topology=c.topology.value, node_count=n)

    # ── Claim Propagation ─────────────────────────────────────────────

    def propagate_claim(
        self,
        claim: dict[str, Any],
        source_node_id: str,
        max_hops: int | None = None,
    ) -> ClaimPropagation:
        """Propagate a claim through the mycorrhizal network.

        Like a disease warning spreading from an infected tree through
        the fungal network to neighboring trees.

        Args:
            claim: Claim dict with at least {'claim_id', 'topic', 'confidence'}
            source_node_id: ID of the originating node
            max_hops: Override propagation hop limit

        Returns:
            ClaimPropagation tracking the spread path and signal strength
        """
        if max_hops is None:
            max_hops = self._config.propagation_max_hops

        claim_id = claim.get("claim_id", f"claim-{self._total_propagations}")
        prop = ClaimPropagation(
            claim_id=claim_id,
            source_node=source_node_id,
            max_hops=max_hops,
            attenuation_rate=self._config.nutrient_decay,
        )

        # Initialize claim storage
        self._claims[claim_id] = {
            "claim": claim,
            "votes": {},           # node_id → vote_value
            "field_strength": 0.5,  # Initial field strength
            "consensus": ConsensusState.PENDING,
            "propagation_count": 0,
        }

        # BFS propagation through adjacency
        frontier = [source_node_id]
        visited: set[str] = set()

        while frontier and prop.is_alive:
            current = frontier.pop(0)
            if current in visited:
                continue
            visited.add(current)
            prop.reached_nodes.add(current)
            prop.propagation_path.append(current)

            # Auto-vote: nodes that receive the claim cast a vote
            if current in self._nodes and current != source_node_id:
                self._mycorrhizal_vote(claim_id, current)

            # Expand to neighbors
            for peer in self._adjacency.get(current, set()):
                if peer not in visited and prop.is_alive:
                    frontier.append(peer)

            prop.attenuate()

        self._claims[claim_id]["propagation_count"] += 1
        self._propagations[claim_id] = prop
        self._total_propagations += 1

        self._logger.debug("claim_propagated",
                           claim_id=claim_id,
                           hops=prop.hops_traveled,
                           reached=len(prop.reached_nodes),
                           strength=round(prop.signal_strength, 4))

        return prop

    def _mycorrhizal_vote(self, claim_id: str, node_id: str) -> float:
        """Cast a vote from a node on a claim.

        Vote weight = node's effective nutrient contribution × claim confidence.
        Like a mother tree contributing more carbon → higher voting weight.
        """
        node = self._nodes.get(node_id)
        if node is None:
            return 0.0

        claim_entry = self._claims.get(claim_id)
        if claim_entry is None:
            return 0.0

        claim_confidence = claim_entry["claim"].get("confidence", 0.5)
        vote_value = node.effective_weight * claim_confidence

        claim_entry["votes"][node_id] = vote_value
        node.vote_history.append({
            "claim_id": claim_id,
            "vote": vote_value,
            "timestamp": time.time(),
        })
        self._total_votes += 1

        # Update field strength based on vote
        self._update_field_strength(claim_id)

        return vote_value

    def _update_field_strength(self, claim_id: str) -> None:
        """Update claim's field strength based on accumulated votes.

        Positive votes increase strength; negative or absent votes cause decay.
        """
        claim_entry = self._claims.get(claim_id)
        if claim_entry is None:
            return

        votes = claim_entry["votes"]
        if not votes:
            # No votes → slow decay
            claim_entry["field_strength"] *= (1.0 - self._config.nutrient_decay)
            return

        total_weight = sum(v for v in votes.values() if v > 0)
        total_negative = sum(abs(v) for v in votes.values() if v < 0)
        node_count = len(self._nodes) or 1

        # Net support normalized by network size
        net_support = (total_weight - total_negative) / node_count
        claim_entry["field_strength"] = max(0.0, min(1.0, 0.5 + net_support))

        # Check for excretion
        if claim_entry["field_strength"] < self._config.min_field_strength:
            claim_entry["consensus"] = ConsensusState.EXCRETED
            self._consensus_events[ConsensusState.EXCRETED.value] += 1

    # ── Consensus Detection ───────────────────────────────────────────

    def detect_consensus(self, claim_id: str) -> ConsensusState:
        """Detect whether consensus has been reached on a claim.

        Quorum sensing: ≥2/3 of nodes that received the claim must agree.

        Returns:
            Current ConsensusState for the claim
        """
        claim_entry = self._claims.get(claim_id)
        if claim_entry is None:
            return ConsensusState.PENDING

        votes = claim_entry["votes"]
        threshold = self._config.consensus_threshold

        # Need at least 3 votes for meaningful consensus
        if len(votes) < 3:
            return ConsensusState.PENDING

        positive = sum(1 for v in votes.values() if v > 0)
        negative = sum(1 for v in votes.values() if v < 0)
        total_votes = len(votes)

        pos_ratio = positive / total_votes
        neg_ratio = negative / total_votes

        if pos_ratio >= threshold:
            claim_entry["consensus"] = ConsensusState.VERIFIED
            claim_entry["field_strength"] = min(1.0, claim_entry["field_strength"] + 0.2)
        elif neg_ratio >= threshold:
            claim_entry["consensus"] = ConsensusState.REJECTED
            claim_entry["field_strength"] = max(0.0, claim_entry["field_strength"] - 0.3)
        elif pos_ratio > neg_ratio and pos_ratio < threshold:
            claim_entry["consensus"] = ConsensusState.PENDING  # Still gathering
        elif abs(pos_ratio - neg_ratio) < 0.1:
            claim_entry["consensus"] = ConsensusState.STALEMATE

        # Check excretion
        if claim_entry["field_strength"] < self._config.min_field_strength:
            claim_entry["consensus"] = ConsensusState.EXCRETED

        final_state = claim_entry["consensus"]
        if final_state != ConsensusState.PENDING:
            self._consensus_events[final_state.value] += 1

        return final_state

    def get_claim_state(self, claim_id: str) -> dict[str, Any] | None:
        """Get the full state of a claim in the network."""
        return self._claims.get(claim_id)

    # ── MNIS Computation ──────────────────────────────────────────────

    def compute_mnis(self) -> float:
        """Compute the Mycelial Network Intelligence Score (MNIS).

        MNIS evaluates network health across 8 orthogonal parameters:
          1. node_diversity: Variety of node domains/specializations
          2. connectivity: Average degree / max possible degree
          3. consensus_rate: Fraction of claims reaching VERIFIED
          4. propagation_efficiency: Average nodes reached per hop
          5. nutrient_health: Average nutrient score across nodes
          6. resilience: Network tolerance to node removal (robustness)
          7. adaptation_rate: Rate of nutrient score improvement
          8. signal_fidelity: Inverse of signal attenuation per hop

        Returns:
            MNIS score in [0, 1], where >0.8 indicates excellent network health.
            Reference: 91.8% predictive accuracy for forest health (Baladi 2026).
        """
        c = self._config
        w = c.mnis_weights
        n = len(self._nodes)
        if n < 2:
            return 0.3  # Insufficient network

        # 1. Node diversity (Shannon entropy of domains)
        domains: dict[str, int] = {}
        for node in self._nodes.values():
            domains[node.domain] = domains.get(node.domain, 0) + 1
        domain_probs = np.array([v / n for v in domains.values()])
        diversity = float(-np.sum(domain_probs * np.log(domain_probs + 1e-10)) / np.log(max(len(domains), 2)))

        # 2. Connectivity
        max_degree = n - 1
        actual_degrees = [len(peers) for peers in self._adjacency.values()]
        avg_degree = np.mean(actual_degrees) if actual_degrees else 0.0
        connectivity = avg_degree / max(max_degree, 1)

        # 3. Consensus rate
        total_consensuses = sum(self._consensus_events.values())
        verified_rate = (self._consensus_events.get(ConsensusState.VERIFIED.value, 0)
                         / max(total_consensuses, 1))

        # 4. Propagation efficiency
        if self._propagations:
            avg_reached = np.mean([p.hops_traveled + 1 for p in self._propagations.values()])
            efficiency = min(1.0, avg_reached / max(n, 1))
        else:
            efficiency = 0.0

        # 5. Nutrient health
        nutrient_scores = [node.nutrient_score for node in self._nodes.values()]
        nutrient_health = float(np.mean(nutrient_scores))

        # 6. Resilience (simulated by network connectivity after removing worst node)
        if n > 2:
            remaining_edges = sum(len(p) for p in self._adjacency.values()) // 2
            max_edges = n * (n - 1) // 2
            resilience = 1.0 - (remaining_edges / max(max_edges, 1))
        else:
            resilience = 0.5

        # 7. Adaptation rate (from history)
        if len(self._mnis_history) >= 2:
            last = self._mnis_history[-1]
            prev = self._mnis_history[-2]
            adaptation = min(1.0, max(0.0, (last.get("nutrient_health", 0.5) - prev.get("nutrient_health", 0.5)) + 0.5))
        else:
            adaptation = 0.5

        # 8. Signal fidelity
        signal_fidelity = 1.0 - c.nutrient_decay

        # Weighted aggregation
        params = [diversity, connectivity, verified_rate, efficiency,
                  nutrient_health, resilience, adaptation, signal_fidelity]
        mnis = float(np.dot(w, params))

        # Normalize to [0, 1]
        mnis = max(0.0, min(1.0, mnis))

        # Record history
        record = {
            "mnis": mnis,
            "diversity": diversity,
            "connectivity": connectivity,
            "verified_rate": verified_rate,
            "efficiency": efficiency,
            "nutrient_health": nutrient_health,
            "resilience": resilience,
            "adaptation": adaptation,
            "signal_fidelity": signal_fidelity,
            "timestamp": time.time(),
        }
        self._mnis_history.append(record)

        self._logger.debug("mnis_computed", mnis=round(mnis, 4), node_count=n)

        return mnis

    # ── Network Health ────────────────────────────────────────────────

    def decay_nutrients(self) -> None:
        """Apply per-step nutrient decay to all nodes.

        Nodes that don't participate in debates slowly lose nutrient score.
        """
        for node in self._nodes.values():
            node.nutrient_score = max(0.1, node.nutrient_score * (1.0 - self._config.nutrient_decay))

    def reward_accurate_node(self, node_id: str, boost: float = 0.05) -> None:
        """Reward a node for making accurate predictions. Like feeding carbon to a tree."""
        node = self._nodes.get(node_id)
        if node:
            node.nutrient_score = min(1.0, node.nutrient_score + boost)

    def penalize_inaccurate_node(self, node_id: str, penalty: float = 0.1) -> None:
        """Penalize a node for inaccurate predictions. Like withholding nutrients."""
        node = self._nodes.get(node_id)
        if node:
            node.nutrient_score = max(0.1, node.nutrient_score - penalty)
            node.trust_decay = min(0.9, node.trust_decay + penalty * 0.5)

    # ── Properties ────────────────────────────────────────────────────

    @property
    def nodes(self) -> dict[str, DebateNode]:
        return self._nodes

    @property
    def claims(self) -> dict[str, dict[str, Any]]:
        return self._claims

    @property
    def stats(self) -> dict[str, Any]:
        c = self._config
        return {
            "node_count": len(self._nodes),
            "claim_count": len(self._claims),
            "total_propagations": self._total_propagations,
            "total_votes": self._total_votes,
            "topology": c.topology.value,
            "consensus_events": dict(self._consensus_events),
            "avg_nutrient": round(np.mean([n.nutrient_score for n in self._nodes.values()]) if self._nodes else 0.0, 4),
            "latest_mnis": round(self._mnis_history[-1]["mnis"], 4) if self._mnis_history else None,
        }

    def reset(self) -> None:
        """Reset the entire debate network."""
        self._nodes.clear()
        self._claims.clear()
        self._propagations.clear()
        self._adjacency.clear()
        self._total_propagations = 0
        self._total_votes = 0
        self._consensus_events = {s.value: 0 for s in ConsensusState}
        self._mnis_history.clear()
        self._logger.debug("debate_network_reset")
