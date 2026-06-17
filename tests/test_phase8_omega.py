"""Phase 8 Omega tests — Cosmos 3 Physical AI + P2P Mesh (AAAI 2026)."""
import pytest

class TestPhysicalAI:
    def test_perceive(self):
        from kernel.omega.physical_ai import PhysicalAI
        pai = PhysicalAI()
        scene = pai.perceive("a cup on a table with a robot arm nearby")
        assert len(scene.objects) >= 1
    def test_reason_and_plan(self):
        from kernel.omega.physical_ai import PhysicalAI
        pai = PhysicalAI()
        scene = pai.perceive("a cup on a table")
        r = pai.reason(scene,"grasp the cup")
        assert r["feasible"] is True
        plan = pai.plan(scene,r)
        assert len(plan.steps) >= 2
    def test_execute(self):
        from kernel.omega.physical_ai import PhysicalAI
        pai = PhysicalAI()
        scene = pai.perceive("a button")
        r = pai.reason(scene,"press the button")
        plan = pai.plan(scene,r)
        result = pai.execute_plan(plan)
        assert result["steps_executed"] >= 1

class TestP2PMesh:
    def test_register_and_share(self):
        from kernel.omega.p2p_mesh import P2PMeshNetwork
        net = P2PMeshNetwork()
        pid = net.register_peer("192.168.1.1",["coding","review"])
        assert pid.startswith("peer_")
        h = net.share_knowledge(pid,"optimized matmul kernel")
        assert h is not None
    def test_verify_chain(self):
        from kernel.omega.p2p_mesh import P2PMeshNetwork
        net = P2PMeshNetwork()
        pid = net.register_peer("node1")
        net.share_knowledge(pid,"block1")
        net.share_knowledge(pid,"block2")
        v = net.verify_chain()
        assert v["valid"] is True
        assert v["blocks"] == 2
    def test_aggregate(self):
        from kernel.omega.p2p_mesh import P2PMeshNetwork
        net = P2PMeshNetwork()
        pid = net.register_peer("n1")
        net.share_knowledge(pid,"GPU optimization for transformer attention")
        results = net.aggregate_knowledge("GPU optimization")
        assert len(results) >= 1
    def test_best_peer(self):
        from kernel.omega.p2p_mesh import P2PMeshNetwork
        net = P2PMeshNetwork()
        net.register_peer("a",["coding"])
        net.register_peer("b",["review"])
        best = net.find_best_peer("coding")
        assert best is not None

class TestOmegaMCPTools:
    def test_all_registered(self):
        from mcp.server import SclerotiumMCPServer
        s = SclerotiumMCPServer(); s.register_all_tools()
        for n in ["physical_perceive","p2p_register","p2p_verify"]:
            assert s.tools.get_handler(n) is not None, f"Missing: {n}"
