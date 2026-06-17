"""Phase 6 Genesis tests — AlphaEvolve/SwarmHarness/NVIDIA AVO/DARPA DICE grade."""
import pytest

class TestGeneticProgram:
    def test_evolve(self):
        from kernel.genesis.genetic_program import GeneticProgrammingEngine
        gp = GeneticProgrammingEngine(10)
        gp.seed_population(["x=1+1","def f():return 42","print(sum(range(10)))","import math","class A:pass"])
        r = gp.evolve_generation()
        assert r["generation"] == 1
        assert r["best_fitness"] >= 0
    def test_reflection(self):
        from kernel.genesis.genetic_program import GeneticProgrammingEngine
        gp = GeneticProgrammingEngine(10)
        gp.seed_population(["print(1)","x=2"])
        gp.add_reflection("past mutation improved fitness by 0.3")
        assert len(gp._run.reflection_memory) == 1

class TestSwarmIntel:
    def test_spawn_and_assign(self):
        from kernel.genesis.swarm_intel import SwarmCoordinator
        sc = SwarmCoordinator(16)
        a = sc.spawn_agent("explorer")
        assert a is not None
        sc.create_task("test task","coding")
        tid = sc.self_assign(a.id)
        assert tid is not None
        sc.complete_task(a.id, tid, True, "done")
        assert a.trust_score > 0.5
    def test_stats(self):
        from kernel.genesis.swarm_intel import SwarmCoordinator
        sc = SwarmCoordinator(8)
        for _ in range(4): sc.spawn_agent()
        for _ in range(3): sc.create_task(f"t{_}","coding")
        s = sc.get_stats()
        assert s["total_agents"] == 4

class TestGPUKernelGen:
    def test_seed(self):
        from kernel.genesis.gpu_kernel_gen import GPUKernelGenerator
        gen = GPUKernelGenerator()
        kid = gen.seed_kernel("test","matmul")
        assert kid.startswith("kernel_")
    def test_optimize(self):
        from kernel.genesis.gpu_kernel_gen import GPUKernelGenerator
        gen = GPUKernelGenerator()
        kid = gen.seed_kernel("opt_test","rmsnorm")
        r = gen.optimize(kid,rounds=3)
        assert "final_fitness" in r

class TestEconomicNet:
    def test_auction(self):
        from kernel.genesis.economic_net import EconomicNetwork
        net = EconomicNetwork()
        a = net.register_agent("coding")
        assert a.credits == 100.0
        aid = net.create_auction("optimize code",10.0)
        net.place_bid(a.id,aid,5.0)
        r = net.settle_auction(aid)
        assert r["status"] == "settled"
    def test_tick(self):
        from kernel.genesis.economic_net import EconomicNetwork
        net = EconomicNetwork()
        for _ in range(5): net.register_agent()
        r = net.tick()
        assert "credits_drained" in r

class TestControlledEmergence:
    def test_assess_stable(self):
        from kernel.genesis.controlled_emergence import ControlledEmergence
        ce = ControlledEmergence()
        a = ce.assess({"total_agents":5,"avg_trust":0.95,"emergent_roles":3,
                        "completion_rate":1.0,"gini":0.1,"active_pheromones":10,
                        "active_agents":5,"agents_above_energy":5,"fitness_gain_per_gen":0.0})
        assert "phase" in a
        assert a["total_guardrails"] >= 8
    def test_guardrails_trigger(self):
        from kernel.genesis.controlled_emergence import ControlledEmergence
        ce = ControlledEmergence()
        a = ce.assess({"total_agents":300,"avg_trust":0.1,"emergent_roles":600,
                        "completion_rate":0.05,"gini":0.9,"active_pheromones":20000,
                        "active_agents":1,"agents_above_energy":0,"fitness_gain_per_gen":0.9})
        assert a["phase"] == "collapsing"

class TestGenesisMCPTools:
    def test_all_registered(self):
        from mcp.server import SclerotiumMCPServer
        s = SclerotiumMCPServer(); s.register_all_tools()
        for n in ["gp_seed","gp_evolve","swarm_status","gpu_seed","econ_tick","emergence_assess"]:
            assert s.tools.get_handler(n) is not None, f"Missing: {n}"
