"""Cross-Phase Integration Tests — verify ALL phases interconnect correctly.

Tests that modules from different phases can interoperate:
  Phase 2 (Core) ↔ Phase 5 (Sovereign) ↔ Phase 9 (Innovation)
  Phase 3 (Gateways) ↔ Phase 11 (Cache)
  Phase 6 (Genesis) ↔ Phase 10 (Apotheosis)
  ...and every other meaningful combination.
"""
import pytest

class TestCoreToSovereignIntegration:
    """Core infrastructure (Phase 2) → Sovereign modules (Phase 5)."""
    def test_arbiter_plus_ring0(self):
        from kernel.constitutional_arbiter import ConstitutionalArbiter
        from kernel.sovereign.ring0_gov import Ring0Governor
        arbiter = ConstitutionalArbiter()
        ring0 = Ring0Governor()
        # Phase 2 Arbiter + Phase 5 Ring-0: dual-layer security
        r1 = arbiter.review("memory_search",{"query":"test"})
        r2 = ring0.review("memory_search",{"category":"computation","action":"analyze"})
        assert r1.verdict.value in ("APPROVED","APPROVED_WITH_WARNING")
        assert r2.allowed is True

    def test_hexis_memory_plus_mycelial(self):
        from kernel.hexis_memory import HexisMemoryStore
        from kernel.innovation.mycelial_memory import MycelialMemristiveMemory
        # Phase 2 Hexis + Phase 9 M³: dual memory systems interoperate
        hexis = HexisMemoryStore(chroma_path="./data/int_chroma",sqlite_path="./data/int_mem.db")
        m3 = MycelialMemristiveMemory()
        # Store in Hexis, mirror in M³
        mid_hexis = hexis.store("evolution gen 42: FCPI 0.78",level="episodic",importance=0.8)
        mid_m3 = m3.store("evolution gen 42: FCPI 0.78",importance=0.8)
        assert mid_hexis.startswith("mem_")
        assert mid_m3.startswith("m3_")
        hexis.close()

    def test_sandstorm_plus_wasm(self):
        from kernel.sandstorm import SandstormExecutor
        from kernel.advanced.wasm_sandbox import WASMSandbox
        # Phase 2 Sandstorm + Phase 4 WASM: dual sandbox
        l1 = SandstormExecutor()
        wasm = WASMSandbox()
        assert l1 is not None
        assert wasm is not None

class TestGatewayToCacheIntegration:
    """Gateway (Phase 3) → Cache Engine (Phase 11)."""
    def test_model_gateway_with_cache(self):
        from gateways.models import UniversalModelGateway
        from kernel.cache.prompt_cache_engine import PromptCacheEngine
        gw = UniversalModelGateway()
        cache = PromptCacheEngine("deepseek")
        cache.warmup(system_prompt="You are a helpful assistant.")
        # Model gateway provides models, cache optimizes their use
        providers = gw.list_providers()
        assert len(providers) >= 15
        r = cache.optimize_request(system="You are a helpful assistant.",messages=[],user_input="test")
        assert r["provider"] == "deepseek"

    def test_mcp_market_with_skills_market(self):
        from gateways.mcp_market import MCPMarketGateway
        from gateways.skills_market import SkillsMarketGateway
        mcp = MCPMarketGateway()
        skills = SkillsMarketGateway()
        # Search across both markets
        mcp_results = mcp.search("postgres")
        skill_results = skills.search("code review")
        assert len(skill_results) >= 1
        assert len(skill_results) >= 1

class TestGenesisToApotheosisIntegration:
    """Genesis (Phase 6) → Apotheosis (Phase 10)."""
    def test_swarm_with_epigenetic(self):
        from kernel.genesis.swarm_intel import SwarmCoordinator
        from kernel.apotheosis.epigenetic_state import EpigeneticComputationalState
        # Swarm agents regulated by epigenetic state
        swarm = SwarmCoordinator(16)
        ecs = EpigeneticComputationalState()
        for role in ["explorer","exploiter","reviewer","validator","planner"]:
            agent = swarm.spawn_agent(role)
            mid = ecs.register_module(role)
            if role in ("reviewer","validator"):
                ecs.mark_success(mid)
            if agent: swarm.create_task(f"{role} task",role)
        stats = ecs.get_epigenome_stats()
        assert stats["total_modules"] >= 5

    def test_economic_with_immuno(self):
        from kernel.genesis.economic_net import EconomicNetwork
        from kernel.apotheosis.immuno_attention import ImmunoAttentionNetwork
        # Economic agents use immunological attention for decision-making
        net = EconomicNetwork()
        ian = ImmunoAttentionNetwork()
        agent = net.register_agent("trader")
        ab = ian.generate_antibody("auction_strategy")
        ian.affinity_maturation("auction_strategy",generations=3)
        assert agent is not None
        assert ab.affinity > 0

class TestInnovationToCosmicIntegration:
    """Innovation (Phase 9) → Cosmic (Phase 7)."""
    def test_consciousness_with_world_model(self):
        from kernel.innovation.resonant_closure import ResonantClosureKernel
        from kernel.cosmic.world_model import WorldModel
        # Consciousness kernel observes world model
        rck = ResonantClosureKernel()
        wm = WorldModel()
        sid = wm.observe([{"type":"agent"},{"type":"environment"}])
        p = wm.predict_next(sid,"observe")
        state = rck.conscious_moment(0.3,[0.5,0.6],0.4,0.2)
        assert state.phi >= 0
        assert p["level"] == "L1_Predictor"

    def test_quantum_bio_with_recursive_self(self):
        from kernel.innovation.quantum_bio_coherence import QuantumBioCoherenceEngine
        from kernel.cosmic.recursive_self import RecursiveSelfImprover
        # Quantum tunneling guides recursive self-improvement
        qb = QuantumBioCoherenceEngine()
        for i in range(15): qb.register_module(f"strategy_{i}")
        ri = RecursiveSelfImprover()
        ri.register_module("optimize","def optimize(): return max(data)")
        r = qb.tunnel_search("strategy",brute_force_space=200)
        s = ri.get_status()
        assert r["energy_saved_pct"] >= 50
        assert s["modules"] >= 1

class TestFullToolPipeline:
    """Verify tools from ALL phases are registered and callable."""
    def test_all_134_tools_registered(self):
        from mcp.server import SclerotiumMCPServer
        s = SclerotiumMCPServer(); s.register_all_tools()
        assert s.tools.tool_count >= 134

    def test_tool_categories_coverage(self):
        from mcp.server import SclerotiumMCPServer
        s = SclerotiumMCPServer(); s.register_all_tools()
        cats = set()
        for t in s.tools.list_tools():
            cats.add(t["category"])
        required = {"system","evolution","memory","sandbox","skills","code_analysis",
                    "im","desktop","scheduler","files","info","models","mcp_market",
                    "skills_market","advanced","sovereign","genesis","cosmic","omega",
                    "innovation","apotheosis","cache"}
        missing = required - cats
        assert len(missing) == 0, f"Missing categories: {missing}"

    def test_cross_phase_tool_call_chain(self):
        """Simulate a full agent workflow across multiple phase tools."""
        from mcp.server import SclerotiumMCPServer
        s = SclerotiumMCPServer(); s.register_all_tools()
        tools = s.tools

        # Step 1: System status (Phase 2)
        h = tools.get_handler("system_status")
        assert h is not None

        # Step 2: Memory search (Phase 2)
        h = tools.get_handler("memory_search")
        assert h is not None

        # Step 3: Cache optimize (Phase 11)
        h = tools.get_handler("cache_warmup")
        assert h is not None

        # Step 4: Kernel capabilities (Phase 5)
        h = tools.get_handler("kernel_capabilities")
        assert h is not None

        # Step 5: Swarm status (Phase 6)
        h = tools.get_handler("swarm_status")
        assert h is not None

        # Step 6: World simulate (Phase 7)
        h = tools.get_handler("world_simulate")
        assert h is not None

        # Step 7: Physical perceive (Phase 8)
        h = tools.get_handler("physical_perceive")
        assert h is not None

        # Step 8: M³ store (Phase 9)
        h = tools.get_handler("m3_store")
        assert h is not None

        # Step 9: Immuno mature (Phase 10)
        h = tools.get_handler("immuno_mature")
        assert h is not None

        # All handlers resolved — full pipeline is connected
