"""Phase 5 Sovereign tests — ProgramBench/MXC/Quantum/AlphaProof grade."""
import pytest

class TestSystemBuilder:
    def test_import(self): from kernel.sovereign.system_builder import SystemBuilder; assert SystemBuilder
    def test_extract_behavior(self):
        from kernel.sovereign.system_builder import SystemBuilder
        r = SystemBuilder().extract_behavior("echo")
        assert "executable" in r
    def test_design_architecture(self):
        from kernel.sovereign.system_builder import SystemBuilder, SystemSpec
        sb = SystemBuilder()
        spec = {"behaviors": ["parse CLI args", "compute result"]}
        modules = sb.design_architecture(spec)
        assert len(modules) >= 1
        assert modules[0].name == "core"
    def test_generate_and_integrate(self):
        from kernel.sovereign.system_builder import SystemBuilder, ModulePlan
        sb = SystemBuilder()
        plan = ModulePlan(name="test_mod",responsibility="test resp",
                          interface={"in":"data","out":"result"},
                          dependencies=[],estimated_lines=100)
        code = sb.generate_module(plan,{})
        assert "test_mod" in code
        r = sb.integrate({"test_mod":code},"./data/test_sysbuild")
        assert r["modules_written"] == 1

class TestCrossRepo:
    def test_search(self):
        from kernel.sovereign.cross_repo import CrossRepoReasoner
        r = CrossRepoReasoner().search_upstream("test query", ["."])
        assert isinstance(r, list)

class TestDomainKnowledge:
    def test_list(self):
        from kernel.sovereign.domain_knowledge import DomainKnowledge
        dk = DomainKnowledge()
        assert len(dk.list_domains()) >= 10
    def test_match(self):
        from kernel.sovereign.domain_knowledge import DomainKnowledge
        dk = DomainKnowledge()
        assert dk.match_domain("qubit superposition") == "quantum"
        assert dk.match_domain("dna sequence alignment") == "bioinfo"

class TestDepMigrate:
    def test_scan(self):
        from kernel.sovereign.dep_migrate import DependencyMigrator
        dm = DependencyMigrator(); dm.add_rule("old_func","new_func")
        r = dm.scan(".")
        assert isinstance(r, list)

class TestKernelIntel:
    def test_detect(self):
        from kernel.sovereign.kernel_intel import KernelIntegrator
        ki = KernelIntegrator()
        assert ki.capabilities.platform in ("Windows","Linux","Darwin")
    def test_policy(self):
        from kernel.sovereign.kernel_intel import KernelIntegrator
        ki = KernelIntegrator()
        policy = ki.get_security_policy()
        assert policy["model"] == "deny-by-default (ATLAS Ring-0)"

class TestQuantumHybrid:
    def test_witness(self):
        from kernel.sovereign.quantum_hybrid import QuantumHybridVerifier
        qv = QuantumHybridVerifier()
        w = qv.generate_witness("x=1+1","correctness")
        assert 0 <= w.confidence <= 1
    def test_gate_allows(self):
        from kernel.sovereign.quantum_hybrid import QuantumHybridVerifier
        qv = QuantumHybridVerifier()
        r = qv.verify_self_modification("x=1","x=1+1","adds computation")
        assert "allowed" in r

class TestFormalProver:
    def test_type_safety(self):
        from kernel.sovereign.formal_prover import NeuroSymbolicProver
        r = NeuroSymbolicProver().prove_type_safety("def f(x: int) -> int: return x")
        assert r["proved"] is True
    def test_prove_all(self):
        from kernel.sovereign.formal_prover import NeuroSymbolicProver
        r = NeuroSymbolicProver().prove_all("def f(x): return x+1")
        assert "type_safety" in r["proofs"]

class TestFeatureDev:
    def test_analyze(self):
        from kernel.sovereign.feature_dev import FeatureDeveloper, FeatureSpec
        fd = FeatureDeveloper()
        r = fd.analyze_impact(FeatureSpec("test","test feature",["core"]))
        assert "total_affected_files" in r

class TestAgentProcess:
    def test_spawn(self):
        from kernel.sovereign.agent_process import AgentProcessManager
        mgr = AgentProcessManager()
        agent = mgr.spawn("print(42)")
        assert agent.agent_id.startswith("agent_")
    def test_tree(self):
        from kernel.sovereign.agent_process import AgentProcessManager
        mgr = AgentProcessManager()
        agent = mgr.spawn("print(1)")
        tree = mgr.get_tree()
        assert "root_pid" in tree

class TestRing0Gov:
    def test_allow(self):
        from kernel.sovereign.ring0_gov import Ring0Governor
        gov = Ring0Governor()
        v = gov.review("computation",{"category":"computation","action":"analyze"})
        assert v.allowed is True
    def test_deny_network(self):
        from kernel.sovereign.ring0_gov import Ring0Governor
        gov = Ring0Governor()
        v = gov.review("network_attempt",{"category":"network","action":"connect"})
        assert v.allowed is False
    def test_constitution(self):
        from kernel.sovereign.ring0_gov import Ring0Governor
        c = Ring0Governor().get_constitution()
        assert len(c) >= 5

class TestLongHorizon:
    def test_create_goal(self):
        from kernel.sovereign.long_horizon import LongHorizonExecutor
        g = LongHorizonExecutor().create_goal("build system",["analyze","design","implement"])
        assert g.status.value == "planning"
        assert len(g.sub_goals) >= 1
    def test_execute(self):
        from kernel.sovereign.long_horizon import LongHorizonExecutor
        ex = LongHorizonExecutor()
        g = ex.create_goal("test",["step1","step2"])
        r = ex.execute_all(g.id)
        assert r["progress"] >= 0
    def test_list(self):
        from kernel.sovereign.long_horizon import LongHorizonExecutor
        ex = LongHorizonExecutor()
        ex.create_goal("g1",["a","b"])
        goals = ex.list_goals()
        assert isinstance(goals, list)

class TestNeuroSymbolic:
    def test_verify(self):
        from kernel.sovereign.neuro_symbolic import NeuroSymbolicReasoner
        r = NeuroSymbolicReasoner().verify_all("def f(): return 42")
        assert "hypotheses_generated" in r
    def test_sdia(self):
        from kernel.sovereign.neuro_symbolic import NeuroSymbolicReasoner
        r = NeuroSymbolicReasoner().sdia_search("optimize code",["x=1","def f(): pass","print(42)"])
        assert r["candidates_explored"] == 3

class TestSovereignMCPTools:
    def test_all_registered(self):
        from mcp.server import SclerotiumMCPServer
        s = SclerotiumMCPServer(); s.register_all_tools()
        names = ["system_build","cross_repo_search","domain_knowledge","dep_migrate_scan",
                 "kernel_capabilities","quantum_verify","quantum_gate","formal_prove",
                 "feature_plan","agent_spawn","agent_tree","ring0_review","ring0_constitution",
                 "goal_create","goal_execute","goal_list","neuro_symbolic_verify","sdia_search"]
        for n in names:
            assert s.tools.get_handler(n) is not None, f"Missing: {n}"
