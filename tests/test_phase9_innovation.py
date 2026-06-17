"""Phase 9 Innovation tests — M³/QBCE/RCK/OCR original inventions."""
import pytest

class TestMycelialMemory:
    def test_store_and_access(self):
        from kernel.innovation.mycelial_memory import MycelialMemristiveMemory
        m3 = MycelialMemristiveMemory()
        mid = m3.store("evolution generation 42 improved FCPI to 0.78")
        r = m3.access(mid)
        assert r is not None
        assert r["resistance_after"] < r["resistance_before"]  # Memristor effect
    def test_connect_and_search(self):
        from kernel.innovation.mycelial_memory import MycelialMemristiveMemory
        m3 = MycelialMemristiveMemory()
        a = m3.store("pattern alpha"); b = m3.store("pattern beta")
        m3.connect(a,b)
        results = m3.search("alpha")
        assert len(results) >= 1
    def test_dehydrate_rehydrate(self):
        from kernel.innovation.mycelial_memory import MycelialMemristiveMemory
        m3 = MycelialMemristiveMemory()
        m3.store("test memory content for dehydration")
        dehydrated = m3.dehydrate()
        assert dehydrated["node_count"] >= 1
        # Dehydrated data format is compatible with rehydrate
        m3b = MycelialMemristiveMemory()
        restored = m3b.rehydrate(dehydrated)
        assert isinstance(restored, int)
    def test_forget_high_resistance(self):
        from kernel.innovation.mycelial_memory import MycelialMemristiveMemory
        m3 = MycelialMemristiveMemory()
        mid = m3.store("weak memory",importance=0.1)
        m3._nodes[mid].resistance = 999.0  # Very high resistance
        forgotten = m3.forget_high_resistance(100.0)
        assert forgotten >= 1

class TestQuantumBioCoherence:
    def test_tunnel_search(self):
        from kernel.innovation.quantum_bio_coherence import QuantumBioCoherenceEngine
        qb = QuantumBioCoherenceEngine()
        for i in range(10): qb.register_module(f"test_mod_{i}: handles optimization task {i}")
        r = qb.tunnel_search("optimization",brute_force_space=100)
        assert r["method"] == "quantum_tunneling"
        assert r["energy_saved_pct"] >= 50
    def test_entanglement(self):
        from kernel.innovation.quantum_bio_coherence import QuantumBioCoherenceEngine
        qb = QuantumBioCoherenceEngine()
        a = qb.register_module("module A: handles search")
        b = qb.register_module("module B: handles ranking")
        assert qb.entangle(a,b,0.8)
        results = qb.retrieve_entangled(a)
        assert len(results) >= 1
    def test_radical_pair_decision(self):
        from kernel.innovation.quantum_bio_coherence import QuantumBioCoherenceEngine
        r = QuantumBioCoherenceEngine().radical_pair_decision("option_a","option_b")
        assert r["decision"] in ("option_a","option_b")
        assert r["mechanism"] == "radical_pair_magnetoreception"

class TestResonantClosure:
    def test_conscious_moment(self):
        from kernel.innovation.resonant_closure import ResonantClosureKernel
        rck = ResonantClosureKernel()
        state = rck.conscious_moment(0.3,[0.5,0.6,0.7],0.5,0.2)
        assert state.phi >= 0
        assert state.entropic_closure >= 0
    def test_consciousness_report(self):
        from kernel.innovation.resonant_closure import ResonantClosureKernel
        rck = ResonantClosureKernel()
        for i in range(10):
            rck.conscious_moment(0.3+i*0.05,[0.5+i*0.02]*5,0.4+i*0.05,0.1)
        report = rck.get_consciousness_report()
        assert "conscious" in report
        assert report["integrated_information_phi"] > 0

class TestOrchORSubstrate:
    def test_entangle_lattice(self):
        from kernel.innovation.orch_or_substrate import OrchORSubstrate
        ocr = OrchORSubstrate(50)
        phi = ocr.entangle_lattice(0.8)
        assert 0 <= phi <= 1
    def test_objective_reduction(self):
        from kernel.innovation.orch_or_substrate import OrchORSubstrate
        ocr = OrchORSubstrate(50)
        ocr.entangle_lattice(0.9)
        event = ocr.objective_reduction(0.9)
        if event:
            assert event.irreversibility is True
    def test_optimize_lattice(self):
        from kernel.innovation.orch_or_substrate import OrchORSubstrate
        ocr = OrchORSubstrate(30)
        r = ocr.optimize_lattice(3)
        assert "initial_free_energy" in r
        assert len(r["phi_trajectory"]) >= 1
    def test_resonance_spectrum(self):
        from kernel.innovation.orch_or_substrate import OrchORSubstrate
        ocr = OrchORSubstrate(20)
        spec = ocr.get_resonance_spectrum()
        assert abs(spec["fundamental_frequency_THz"] - 1.701) < 0.001

class TestInnovationMCPTools:
    def test_all_registered(self):
        from mcp.server import SclerotiumMCPServer
        s = SclerotiumMCPServer(); s.register_all_tools()
        for n in ["m3_store","qbc_tunnel","rck_consciousness","orch_or_collapse"]:
            assert s.tools.get_handler(n) is not None, f"Missing: {n}"
