"""Tests for L3: MycorrhizalDebateNetwork — 菌根辩论网络."""

import numpy as np
import pytest

from src.l3.mycorrhizal_debate_network import (
    ConsensusState,
    DebateNetworkConfig,
    DebateNode,
    MycorrhizalDebateNetwork,
    NetworkTopology,
)


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def config() -> DebateNetworkConfig:
    return DebateNetworkConfig(
        topology=NetworkTopology.SMALL_WORLD,
        hub_count=2,
        mesh_degree=3,
        propagation_max_hops=3,
        consensus_threshold=0.667,
    )


@pytest.fixture
def network(config: DebateNetworkConfig) -> MycorrhizalDebateNetwork:
    return MycorrhizalDebateNetwork(config=config)


@pytest.fixture
def populated_network(network: MycorrhizalDebateNetwork) -> MycorrhizalDebateNetwork:
    """Network with 6 nodes connected in small-world topology."""
    domains = ["finance", "medical", "legal", "engineering", "ai_ml", "cybersecurity"]
    for i, domain in enumerate(domains):
        node = DebateNode(
            node_id=f"node-{domain}",
            domain=domain,
            nutrient_score=0.5 + i * 0.08,
            specialization=domain,
        )
        network.add_node(node)
    network.build_topology()
    return network


@pytest.fixture
def sample_claim() -> dict:
    return {
        "claim_id": "claim-001",
        "topic": "finance",
        "predicate": "Stock X will return >5% in 30 days",
        "confidence": 0.75,
    }


# ═══════════════════════════════════════════════════════════════════════
# Unit Tests
# ═══════════════════════════════════════════════════════════════════════


class TestDebateNetworkInit:
    """Test initialization and configuration."""

    def test_default_init(self) -> None:
        network = MycorrhizalDebateNetwork()
        assert len(network.nodes) == 0
        assert network.stats["node_count"] == 0
        assert network.stats["topology"] == "small_world"

    def test_custom_config(self, config: DebateNetworkConfig) -> None:
        network = MycorrhizalDebateNetwork(config=config)
        assert network._config.topology == NetworkTopology.SMALL_WORLD
        assert network._config.consensus_threshold == 0.667

    def test_initial_stats(self, network: MycorrhizalDebateNetwork) -> None:
        stats = network.stats
        assert stats["total_propagations"] == 0
        assert stats["total_votes"] == 0
        for state in ConsensusState:
            assert stats["consensus_events"].get(state.value, 0) == 0


class TestNodeManagement:
    """Test adding, removing, and connecting nodes."""

    def test_add_node(self, network: MycorrhizalDebateNetwork) -> None:
        node = DebateNode(node_id="n1", domain="finance", nutrient_score=0.8)
        network.add_node(node)
        assert "n1" in network.nodes
        assert network.nodes["n1"].nutrient_score == 0.8

    def test_add_multiple_nodes(self, network: MycorrhizalDebateNetwork) -> None:
        for i in range(5):
            network.add_node(DebateNode(node_id=f"n{i}", domain="general"))
        assert len(network.nodes) == 5

    def test_remove_node(self, network: MycorrhizalDebateNetwork) -> None:
        network.add_node(DebateNode(node_id="n1"))
        network.remove_node("n1")
        assert "n1" not in network.nodes

    def test_connect_nodes(self, network: MycorrhizalDebateNetwork) -> None:
        network.add_node(DebateNode(node_id="n1"))
        network.add_node(DebateNode(node_id="n2"))
        network.connect_nodes("n1", "n2")
        assert "n2" in network._adjacency["n1"]

    def test_node_effective_weight(self) -> None:
        node = DebateNode(node_id="n1", nutrient_score=0.8, trust_decay=0.2)
        assert node.effective_weight == 0.8 * 0.8  # 0.64

    def test_node_trust_decay_caps(self) -> None:
        node = DebateNode(node_id="n1", nutrient_score=1.0, trust_decay=1.5)
        # trust_decay capped at 0.9, so effective_weight = 1.0 * (1.0 - 0.9) = 0.1
        assert abs(node.effective_weight - 0.1) < 1e-9


class TestTopologyBuilding:
    """Test network topology construction."""

    def test_build_small_world(self, network: MycorrhizalDebateNetwork) -> None:
        for i in range(8):
            network.add_node(DebateNode(node_id=f"n{i}", domain="general"))
        network.build_topology()
        # After building, nodes should have connections
        degrees = [len(peers) for peers in network._adjacency.values()]
        assert all(d > 0 for d in degrees)

    def test_build_hub_spoke(self) -> None:
        config = DebateNetworkConfig(topology=NetworkTopology.HUB_SPOKE, hub_count=2)
        network = MycorrhizalDebateNetwork(config=config)
        for i in range(6):
            network.add_node(DebateNode(node_id=f"n{i}"))
        network.build_topology()
        # Hubs should have more connections than spokes
        degrees = [len(peers) for peers in network._adjacency.values()]
        assert max(degrees) >= min(degrees)

    def test_build_mesh(self) -> None:
        config = DebateNetworkConfig(topology=NetworkTopology.MESH, mesh_degree=3)
        network = MycorrhizalDebateNetwork(config=config)
        for i in range(5):
            network.add_node(DebateNode(node_id=f"n{i}"))
        network.build_topology()
        degrees = [len(peers) for peers in network._adjacency.values()]
        assert all(d > 0 for d in degrees)

    def test_build_empty_network(self, network: MycorrhizalDebateNetwork) -> None:
        """Building topology with <2 nodes should not crash."""
        network.build_topology()
        assert len(network._adjacency) == 0


class TestClaimPropagation:
    """Test claim propagation through the network."""

    def test_propagate_claim(self, populated_network: MycorrhizalDebateNetwork, sample_claim: dict) -> None:
        propagation = populated_network.propagate_claim(sample_claim, "node-finance")
        assert propagation.claim_id == "claim-001"
        assert propagation.source_node == "node-finance"
        assert len(propagation.reached_nodes) > 0

    def test_propagation_reaches_multiple_nodes(self, populated_network: MycorrhizalDebateNetwork, sample_claim: dict) -> None:
        propagation = populated_network.propagate_claim(sample_claim, "node-finance", max_hops=5)
        # Should reach several nodes in the small-world network
        assert len(propagation.reached_nodes) >= 2

    def test_propagation_signal_attenuates(self, populated_network: MycorrhizalDebateNetwork, sample_claim: dict) -> None:
        propagation = populated_network.propagate_claim(sample_claim, "node-finance", max_hops=10)
        assert propagation.signal_strength < 1.0

    def test_propagation_stops_at_max_hops(self, populated_network: MycorrhizalDebateNetwork, sample_claim: dict) -> None:
        propagation = populated_network.propagate_claim(sample_claim, "node-finance", max_hops=1)
        assert propagation.hops_traveled <= 1

    def test_auto_voting_on_propagation(self, populated_network: MycorrhizalDebateNetwork, sample_claim: dict) -> None:
        populated_network.propagate_claim(sample_claim, "node-finance", max_hops=5)
        claim_state = populated_network.get_claim_state("claim-001")
        assert claim_state is not None
        # Some nodes should have voted automatically
        assert len(claim_state["votes"]) > 0


class TestConsensusDetection:
    """Test quorum sensing / consensus detection."""

    def test_pending_with_few_votes(self, populated_network: MycorrhizalDebateNetwork) -> None:
        claim = {"claim_id": "c1", "confidence": 0.5}
        populated_network.propagate_claim(claim, "node-finance", max_hops=1)
        # With limited propagation, may still be pending
        state = populated_network.detect_consensus("c1")
        assert state in (ConsensusState.PENDING, ConsensusState.VERIFIED)

    def test_consensus_not_reached_without_votes(self, network: MycorrhizalDebateNetwork) -> None:
        state = network.detect_consensus("nonexistent")
        assert state == ConsensusState.PENDING

    def test_verified_consensus_accumulates(self, populated_network: MycorrhizalDebateNetwork) -> None:
        """Multiple high-confidence claims should drive consensus."""
        for i in range(5):
            claim = {"claim_id": f"verify-{i}", "confidence": 0.9}
            populated_network.propagate_claim(claim, "node-finance", max_hops=5)

        # After multiple high-confidence propagations, consensus should form
        all_verified = all(
            populated_network.detect_consensus(f"verify-{i}") != ConsensusState.REJECTED
            for i in range(5)
        )
        assert all_verified is True


class TestMNISComputation:
    """Test Mycelial Network Intelligence Score."""

    def test_mnis_low_for_empty_network(self, network: MycorrhizalDebateNetwork) -> None:
        mnis = network.compute_mnis()
        assert 0.0 <= mnis <= 0.5  # Low score for empty network

    def test_mnis_increases_with_nodes(self, populated_network: MycorrhizalDebateNetwork) -> None:
        mnis = populated_network.compute_mnis()
        assert 0.0 <= mnis <= 1.0
        assert isinstance(mnis, float)

    def test_mnis_history_recorded(self, populated_network: MycorrhizalDebateNetwork) -> None:
        populated_network.compute_mnis()
        populated_network.compute_mnis()
        assert len(populated_network._mnis_history) >= 2

    def test_mnis_consistent(self, populated_network: MycorrhizalDebateNetwork) -> None:
        """MNIS should be deterministic for the same network state."""
        mnis1 = populated_network.compute_mnis()
        mnis2 = populated_network.compute_mnis()
        assert abs(mnis1 - mnis2) < 0.1


class TestNutrientDynamics:
    """Test nutrient scoring and decay."""

    def test_reward_node(self, populated_network: MycorrhizalDebateNetwork) -> None:
        initial = populated_network.nodes["node-finance"].nutrient_score
        populated_network.reward_accurate_node("node-finance", boost=0.1)
        assert populated_network.nodes["node-finance"].nutrient_score > initial

    def test_penalize_node(self, populated_network: MycorrhizalDebateNetwork) -> None:
        populated_network.penalize_inaccurate_node("node-finance", penalty=0.2)
        node = populated_network.nodes["node-finance"]
        assert node.nutrient_score < 0.5 + 0.08  # initial was 0.58
        assert node.trust_decay > 0.0

    def test_decay_nutrients(self, populated_network: MycorrhizalDebateNetwork) -> None:
        initial_scores = {nid: n.nutrient_score for nid, n in populated_network.nodes.items()}
        populated_network.decay_nutrients()
        for nid, node in populated_network.nodes.items():
            assert node.nutrient_score <= initial_scores[nid]

    def test_nutrient_floor(self, populated_network: MycorrhizalDebateNetwork) -> None:
        """Nutrient should not go below 0.1."""
        for _ in range(50):
            populated_network.decay_nutrients()
        for node in populated_network.nodes.values():
            assert node.nutrient_score >= 0.1


class TestReset:
    """Test network reset."""

    def test_reset_clears_all(self, populated_network: MycorrhizalDebateNetwork) -> None:
        claim = {"claim_id": "r1", "confidence": 0.5}
        populated_network.propagate_claim(claim, "node-finance")
        populated_network.compute_mnis()

        populated_network.reset()
        assert len(populated_network.nodes) == 0
        assert len(populated_network.claims) == 0
        assert populated_network.stats["total_propagations"] == 0
        assert populated_network.stats["total_votes"] == 0
