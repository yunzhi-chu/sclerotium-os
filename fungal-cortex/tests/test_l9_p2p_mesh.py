"""Tests for L9: PeerToPeerMesh — P2P边缘网格."""

import numpy as np
import pytest

from src.l9.p2p_mesh import (
    AggregatedKnowledge,
    NetworkIdentity,
    P2PMeshConfig,
    PeerNode,
    PeerToPeerMesh,
)


@pytest.fixture
def mesh() -> PeerToPeerMesh:
    return PeerToPeerMesh()


@pytest.fixture
def connected_mesh(mesh: PeerToPeerMesh) -> PeerToPeerMesh:
    mesh.join_network(["peer1:9001", "peer2:9002", "peer3:9003"])
    return mesh


class TestMeshInit:
    def test_default_init(self) -> None:
        m = PeerToPeerMesh()
        assert m.stats["peer_count"] == 0
        assert not m.stats["is_connected"]

    def test_custom_config(self) -> None:
        cfg = P2PMeshConfig(max_peers=50, gossip_ttl_default=5)
        m = PeerToPeerMesh(config=cfg)
        assert m._config.max_peers == 50
        assert m._config.gossip_ttl_default == 5


class TestNetworkJoining:
    def test_join_network(self, mesh: PeerToPeerMesh) -> None:
        identity = mesh.join_network(["bootstrap:9000"])
        assert isinstance(identity, NetworkIdentity)
        assert mesh.stats["is_connected"]
        assert mesh.identity is not None

    def test_join_with_multiple_bootstrap(self, connected_mesh: PeerToPeerMesh) -> None:
        assert connected_mesh.stats["peer_count"] == 3

    def test_join_no_bootstrap(self, mesh: PeerToPeerMesh) -> None:
        identity = mesh.join_network()
        assert isinstance(identity, NetworkIdentity)
        assert mesh.stats["is_connected"]


class TestPeerDiscovery:
    def test_discover_peers(self, connected_mesh: PeerToPeerMesh) -> None:
        peers = connected_mesh.discover_peers(max_hops=2)
        assert len(peers) > 0

    def test_discover_no_peers_before_join(self, mesh: PeerToPeerMesh) -> None:
        peers = mesh.discover_peers()
        assert len(peers) == 0


class TestGossipProtocol:
    def test_gossip_propagate(self, connected_mesh: PeerToPeerMesh) -> None:
        reached = connected_mesh.gossip_propagate(b"test data", ttl=3)
        assert reached > 0

    def test_gossip_before_join(self, mesh: PeerToPeerMesh) -> None:
        reached = mesh.gossip_propagate(b"data")
        assert reached == 0

    def test_gossip_with_coverage(self, connected_mesh: PeerToPeerMesh) -> None:
        reached = connected_mesh.gossip_propagate(b"important", ttl=2, target_coverage=0.5)
        assert reached > 0


class TestKnowledgeAggregation:
    def test_store_and_aggregate(self, connected_mesh: PeerToPeerMesh) -> None:
        connected_mesh.store_knowledge("topic_a", np.ones(8), confidence=0.8)
        connected_mesh.store_knowledge("topic_b", np.zeros(8), confidence=0.6)
        query = np.ones(8) * 0.5
        result = connected_mesh.aggregate_knowledge(query, k=2)
        assert isinstance(result, AggregatedKnowledge)
        assert result.peer_count == 2

    def test_aggregate_empty(self, mesh: PeerToPeerMesh) -> None:
        result = mesh.aggregate_knowledge(np.ones(4))
        assert result.peer_count == 0

    def test_aggregate_with_weights(self, connected_mesh: PeerToPeerMesh) -> None:
        connected_mesh.store_knowledge("high_conf", np.array([1.0, 0.0, 0.0, 0.0]), confidence=0.95)
        connected_mesh.store_knowledge("low_conf", np.array([0.0, 0.0, 0.0, 1.0]), confidence=0.1)
        query = np.array([0.8, 0.0, 0.0, 0.2])
        result = connected_mesh.aggregate_knowledge(query, k=2)
        assert result.confidence > 0.0


class TestDifferentialPrivacy:
    def test_privacy_preserving_aggregate(self, mesh: PeerToPeerMesh) -> None:
        gradients = [np.ones(10) * 0.5, np.ones(10) * 0.3, np.ones(10) * 0.7]
        result = mesh.privacy_preserving_aggregate(gradients)
        assert result.shape == (10,)
        # Result should be close to mean but not exactly (noise added)
        assert abs(result.mean() - 0.5) < 0.3

    def test_privacy_preserving_empty(self, mesh: PeerToPeerMesh) -> None:
        result = mesh.privacy_preserving_aggregate([])
        assert result.shape == (1,)


class TestPeerTrust:
    def test_update_peer_trust(self, connected_mesh: PeerToPeerMesh) -> None:
        peers = list(connected_mesh._peers.keys())
        if peers:
            connected_mesh.update_peer_trust(peers[0], 0.2)
            assert connected_mesh._peers[peers[0]].identity.trust_score > 0.5

    def test_get_trusted_peers(self, connected_mesh: PeerToPeerMesh) -> None:
        trusted = connected_mesh.get_trusted_peers(min_trust=0.3)
        assert isinstance(trusted, list)


class TestReset:
    def test_reset_clears_all(self, connected_mesh: PeerToPeerMesh) -> None:
        connected_mesh.reset()
        assert connected_mesh.stats["peer_count"] == 0
        assert not connected_mesh.stats["is_connected"]
