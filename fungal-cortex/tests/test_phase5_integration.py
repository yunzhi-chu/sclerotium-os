"""Integration tests for Phase 5: L8 Self-Referential + L9 P2P/Quantum + L10 Constitutional/Conscious."""

import asyncio

import numpy as np
import pytest

from src.bridge.quantum_bridge import QuantumBridge, QuantumOptimizationResult
from src.bridge.conscious_bridge import (
    ConsciousBridge,
    MetaControlLevel,
    MetaControlParams,
    OverrideResult,
)
from src.l3.mycorrhizal_debate_network import (
    DebateNetworkConfig,
    MycorrhizalDebateNetwork,
)
from src.l8.self_referential_compiler import SelfReferentialCompiler, SystemGenome
from src.l9.p2p_mesh import PeerToPeerMesh
from src.l9.hybrid_quantum_agent import HybridQuantumAgent
from src.l10.constitutional_arbiter import ConstitutionalArbiter, GuardAction, GuardDecision
from src.l10.conscious_kernel import ConsciousKernel, ConsciousnessLevel


class TestPhase5BridgeLifecycle:
    def test_quantum_bridge_init(self) -> None:
        bridge = QuantumBridge()
        assert bridge.stats["optimization_count"] == 0

    def test_conscious_bridge_init(self) -> None:
        bridge = ConsciousBridge()
        assert bridge.current_control_level == MetaControlLevel.READ_ONLY


class TestQuantumBridgeL9L3:
    def test_encode_debate_params(self) -> None:
        bridge = QuantumBridge()
        config = DebateNetworkConfig(hub_count=3, mesh_degree=4)
        ising = bridge.encode_debate_params(config)
        assert ising.num_spins == 12
        assert ising.h.shape == (12,)
        assert ising.J.shape == (12, 12)

    def test_anneal(self) -> None:
        bridge = QuantumBridge()
        config = DebateNetworkConfig()
        ising = bridge.encode_debate_params(config)
        solution = bridge.anneal(ising)
        assert solution.solution_vector.shape == (12,)

    def test_optimize_debate_params(self) -> None:
        bridge = QuantumBridge()
        config = DebateNetworkConfig(hub_count=3, mesh_degree=4)
        result = bridge.optimize_debate_params(config)
        assert isinstance(result, QuantumOptimizationResult)
        assert len(result.optimized_params) == 5
        assert result.validation_accuracy > 0.0

    def test_quantum_disabled_fallback(self) -> None:
        bridge = QuantumBridge(enable_quantum=False)
        config = DebateNetworkConfig()
        ising = bridge.encode_debate_params(config)
        solution = bridge.anneal(ising)
        assert solution.backend == "classical_fallback"


class TestConsciousBridgeL10L6:
    def test_read_consciousness_level(self) -> None:
        bridge = ConsciousBridge()
        level = bridge.read_consciousness_level()
        assert level in ConsciousnessLevel

    def test_adjust_metacognition_dormant(self) -> None:
        bridge = ConsciousBridge()
        params = bridge.adjust_metacognition()
        assert isinstance(params, MetaControlParams)
        assert params.control_level == MetaControlLevel.READ_ONLY

    def test_emergency_override(self) -> None:
        bridge = ConsciousBridge()
        result = bridge.emergency_override("harm_detected")
        assert isinstance(result, OverrideResult)
        assert result.overridden
        assert result.new_control_level == MetaControlLevel.READ_ONLY

    def test_get_phenomenal_experience(self) -> None:
        bridge = ConsciousBridge()
        # Generate some experience first
        bridge._kernel.register_processor("test")
        bridge._kernel.submit_output("test", np.ones(8), 0.8, 0.7)
        bridge._kernel.compete()
        bridge._kernel.compute_phi()
        bridge._kernel.generate_phenomenal_experience()
        exp = bridge.get_phenomenal_experience()
        assert exp is not None


class TestL8L9L10Coexistence:
    @pytest.mark.asyncio
    async def test_l8_improve_with_l10_governance(self) -> None:
        """L8 self-improvement while L10 governance monitors."""
        l8 = SelfReferentialCompiler()
        l10 = ConstitutionalArbiter()

        # Load genome
        import tempfile, os
        tmpdir = tempfile.mkdtemp()
        paths = []
        for i in range(2):
            p = os.path.join(tmpdir, f"mod_{i}.py")
            with open(p, "w") as f:
                f.write(f"# Module {i}\ndef f{i}():\n    pass\n")
            paths.append(p)

        l8.load_genome(paths)

        # Run improvement cycle
        await l8.self_improve_cycle({"L1": {"error_rate": 0.12, "latency_ms": 400}})

        # L10 audits the improvement
        action = GuardAction(action_id="audit-l8", source_layer="L8", action_type="self_improve")
        decision = l10.intercept(action)
        assert decision in (GuardDecision.ALLOW, GuardDecision.FLAG_FOR_HUMAN_REVIEW)

        # Clean up
        for p in paths:
            os.unlink(p)
        os.rmdir(tmpdir)


class TestFullPhase5Pipeline:
    @pytest.mark.asyncio
    async def test_all_phase5_components(self) -> None:
        """Verify all Phase 5 components initialize and interact correctly."""
        # L8
        l8 = SelfReferentialCompiler()
        import tempfile, os
        tmpdir = tempfile.mkdtemp()
        p = os.path.join(tmpdir, "test.py")
        with open(p, "w") as f:
            f.write("def test():\n    pass\n")
        l8.load_genome([p])

        # L9
        mesh = PeerToPeerMesh()
        mesh.join_network(["peer1:9000"])
        qagent = HybridQuantumAgent()

        # L10
        arbiter = ConstitutionalArbiter()
        kernel = ConsciousKernel()

        # Bridges
        qbridge = QuantumBridge()
        cbridge = ConsciousBridge(conscious_kernel=kernel, arbiter=arbiter)

        # Verify all initialized
        assert l8.genome is not None
        assert mesh.stats["is_connected"]
        assert qagent.stats["qubits"] > 0
        assert arbiter.stats["principles_count"] == 4
        assert kernel.emergence_level == ConsciousnessLevel.DORMANT

        # Cross-component interaction
        await l8.self_improve_cycle({"L9": {"latency_ms": 200}})
        mesh.gossip_propagate(b"improvement")
        qagent.train_hybrid(episodes=5)
        kernel.compute_phi()
        kernel.generate_phenomenal_experience()
        cbridge.adjust_metacognition()

        # Clean up
        os.unlink(p)
        os.rmdir(tmpdir)

    @pytest.mark.asyncio
    async def test_parallel_phase1_thru_phase5(self) -> None:
        """All five phases coexist and process in parallel."""
        from src.bridge.phase1_liquid_bridge import Phase1LiquidBridge
        from src.bridge.phase2_mycorrhizal_bridge import Phase2MycorrhizalBridge
        from src.bridge.phase3_causal_orch_bridge import Phase3CausalOrchestrationBridge
        from src.bridge.phase4_genome_twin_bridge import Phase4GenomeTwinBridge
        from src.l1.liquid_perceptor import DataPoint, ModalityType

        p1 = Phase1LiquidBridge(enable_snn=False, enable_routing=False)
        await p1.initialize()

        p2 = Phase2MycorrhizalBridge(enable_validator=False, enable_swarm=False)
        await p2.initialize()

        p3 = Phase3CausalOrchestrationBridge()
        await p3.initialize()

        p4 = Phase4GenomeTwinBridge()
        await p4.initialize()

        # Phase 5 components
        l8 = SelfReferentialCompiler()
        mesh = PeerToPeerMesh()
        mesh.join_network(["bootstrap:9000"])
        arbiter = ConstitutionalArbiter()
        kernel = ConsciousKernel()
        kernel.compute_phi()
        kernel.generate_phenomenal_experience()

        # All 5 phases operational
        assert p1.is_initialized and p2.is_initialized and p3.is_initialized and p4.is_initialized
        assert mesh.stats["is_connected"]
        assert arbiter.stats["principles_count"] == 4
        assert kernel.current_phi >= 0.0

        # Process through all
        p1_result = await p1.process(DataPoint(
            modality=ModalityType.TIME_SERIES,
            vector=np.random.RandomState(42).randn(20).astype(np.float64),
        ))
        assert p1_result.percept is not None

        p2_result = await p2.process_claim("System is healthy", agent_id="a1")
        assert p2_result.trace is not None

        p3_result = await p3.plan_and_execute("Monitor system health")
        assert p3_result.execution_plan is not None

        p4_result = await p4.evolve_and_simulate(
            "Optimize overall architecture",
            state_vector=np.random.RandomState(42).randn(64),
        )
        assert p4_result.architecture is not None

        # Phase 5: governance audit
        action = GuardAction(action_id="final", source_layer="L10", action_type="report_health")
        decision = arbiter.intercept(action)
        assert decision in (GuardDecision.ALLOW, GuardDecision.FLAG_FOR_HUMAN_REVIEW)
