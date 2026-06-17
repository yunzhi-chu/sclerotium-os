"""Integration tests for Phase 4: L6 Genome Evolution + L7 World Model."""

import asyncio

import numpy as np
import pytest

from src.bridge.phase4_genome_twin_bridge import (
    EvolutionPath,
    Phase4GenomeTwinBridge,
    Phase4Result,
)
from src.l6.darwinian_godel_machine import (
    AgentGenome,
    DarwinianGodelMachine,
    Gene,
    MutationType,
)
from src.l6.mas2_architecture_customizer import (
    CustomArchitecture,
    MAS2ArchitectureCustomizer,
    TaskProfile,
)
from src.l7.active_inference_agent import (
    ActiveInferenceAgent,
    Observation,
    PolicyType,
)
from src.l7.digital_twin_engine import (
    AnomalySeverity,
    DigitalTwinEngine,
    HealthReport,
    PhysicalState,
)


@pytest.fixture
def bridge() -> Phase4GenomeTwinBridge:
    return Phase4GenomeTwinBridge(enable_dgm=True, enable_mas2=True, enable_active_inference=True, enable_digital_twin=True)


@pytest.fixture
def bridge_minimal() -> Phase4GenomeTwinBridge:
    return Phase4GenomeTwinBridge(enable_dgm=False, enable_mas2=False, enable_active_inference=False, enable_digital_twin=False)


class TestBridgeLifecycle:
    def test_initial_state(self, bridge: Phase4GenomeTwinBridge) -> None:
        assert not bridge.is_initialized
        assert bridge.stats["process_count"] == 0

    @pytest.mark.asyncio
    async def test_initialize(self, bridge: Phase4GenomeTwinBridge) -> None:
        await bridge.initialize()
        assert bridge.is_initialized

    @pytest.mark.asyncio
    async def test_shutdown(self, bridge: Phase4GenomeTwinBridge) -> None:
        await bridge.initialize()
        await bridge.shutdown()
        assert not bridge.is_initialized

    @pytest.mark.asyncio
    async def test_initialize_minimal(self, bridge_minimal: Phase4GenomeTwinBridge) -> None:
        await bridge_minimal.initialize()
        assert bridge_minimal.is_initialized


class TestEvolveAndSimulate:
    @pytest.mark.asyncio
    async def test_full_pipeline(self, bridge: Phase4GenomeTwinBridge) -> None:
        await bridge.initialize()
        state = np.random.RandomState(42).randn(64)
        result = await bridge.evolve_and_simulate(
            "Analyze market risk and propose rebalancing strategy",
            state_vector=state,
            complexity=0.6,
        )
        assert isinstance(result, Phase4Result)
        assert result.architecture is not None
        assert result.genome is not None

    @pytest.mark.asyncio
    async def test_pipeline_with_goal(self, bridge: Phase4GenomeTwinBridge) -> None:
        await bridge.initialize()
        goal = np.zeros(16)
        result = await bridge.evolve_and_simulate(
            "Optimize portfolio allocation",
            state_vector=np.random.RandomState(99).randn(64),
            goal_state=goal,
        )
        assert result.action is not None
        assert result.intervention is not None

    @pytest.mark.asyncio
    async def test_pipeline_increments_count(self, bridge: Phase4GenomeTwinBridge) -> None:
        await bridge.initialize()
        await bridge.evolve_and_simulate("Task 1", state_vector=np.random.RandomState(1).randn(64))
        assert bridge.stats["process_count"] == 1

    @pytest.mark.asyncio
    async def test_pipeline_minimal(self, bridge_minimal: Phase4GenomeTwinBridge) -> None:
        await bridge_minimal.initialize()
        result = await bridge_minimal.evolve_and_simulate("Task")
        assert result.architecture is None
        assert result.genome is None


class TestCrossBackboneTransfer:
    @pytest.mark.asyncio
    async def test_transfer_between_backbones(self, bridge: Phase4GenomeTwinBridge) -> None:
        await bridge.initialize()
        transferred = bridge.transfer_between_backbones("claude", "gpt")
        assert transferred is not None
        assert transferred.target_backbone == "gpt"

    def test_transfer_no_dgm(self, bridge_minimal: Phase4GenomeTwinBridge) -> None:
        assert bridge_minimal.transfer_between_backbones("claude", "gpt") is None


class TestBenchmark:
    @pytest.mark.asyncio
    async def test_benchmark_architecture(self, bridge: Phase4GenomeTwinBridge) -> None:
        await bridge.initialize()
        result = await bridge.evolve_and_simulate("Benchmark task", state_vector=np.random.RandomState(7).randn(64))
        if result.architecture:
            benchmark = bridge.benchmark_architecture(result.architecture)
            assert benchmark is not None
            assert benchmark.quality_improvement_pct >= 0


class TestTwinOperations:
    @pytest.mark.asyncio
    async def test_sync_physical_state(self, bridge: Phase4GenomeTwinBridge) -> None:
        await bridge.initialize()
        digital = bridge.sync_physical_state(np.random.RandomState(3).randn(64), "ext-state")
        assert digital is not None

    @pytest.mark.asyncio
    async def test_detect_anomalies(self, bridge: Phase4GenomeTwinBridge) -> None:
        await bridge.initialize()
        # Normal state
        bridge.sync_physical_state(np.random.RandomState(5).randn(64) * 0.1)
        result = bridge.detect_anomalies()
        # May or may not be anomaly
        if result is not None:
            assert result.severity in AnomalySeverity

    def test_sync_no_dte(self, bridge_minimal: Phase4GenomeTwinBridge) -> None:
        assert bridge_minimal.sync_physical_state(np.ones(64)) is None

    def test_detect_no_dte(self, bridge_minimal: Phase4GenomeTwinBridge) -> None:
        assert bridge_minimal.detect_anomalies() is None


class TestLegacyCompatibility:
    @pytest.mark.asyncio
    async def test_to_legacy_meta_report(self, bridge: Phase4GenomeTwinBridge) -> None:
        await bridge.initialize()
        result = await bridge.evolve_and_simulate("Analyze data", state_vector=np.random.RandomState(11).randn(64))
        legacy = bridge.to_legacy_meta_report(result)
        assert "report_id" in legacy
        assert "task" in legacy
        assert "architecture_topology" in legacy
        assert "genome_genes" in legacy
        assert "action_confidence" in legacy
        assert "free_energy" in legacy
        assert "health_score" in legacy


class TestBridgeStats:
    def test_stats_initial(self, bridge: Phase4GenomeTwinBridge) -> None:
        stats = bridge.stats
        assert "l6_dgm" in stats
        assert "l6_mas2" in stats
        assert "l7_ai" in stats
        assert "l7_dte" in stats

    @pytest.mark.asyncio
    async def test_stats_after_processing(self, bridge: Phase4GenomeTwinBridge) -> None:
        await bridge.initialize()
        await bridge.evolve_and_simulate("Test task", state_vector=np.random.RandomState(13).randn(64))
        stats = bridge.stats
        assert stats["process_count"] == 1
        assert stats["last_result"] is not None


class TestBridgeReset:
    @pytest.mark.asyncio
    async def test_reset(self, bridge: Phase4GenomeTwinBridge) -> None:
        await bridge.initialize()
        await bridge.evolve_and_simulate("Task", state_vector=np.random.RandomState(17).randn(64))
        bridge.reset()
        assert bridge.stats["process_count"] == 0
        assert not bridge.is_initialized


# ═══════════════════════════════════════════════════════════════════════
# Cross-Phase Integration Tests (Phase 1 + 2 + 3 + 4)
# ═══════════════════════════════════════════════════════════════════════


class TestFullPhase4Pipeline:
    @pytest.mark.asyncio
    async def test_end_to_end_flow(self) -> None:
        """Full Phase 4 pipeline: evolve → architect → perceive → plan → simulate."""
        bridge = Phase4GenomeTwinBridge()
        await bridge.initialize()

        # Evolve + simulate
        result = await bridge.evolve_and_simulate(
            "Design an optimal resource allocation strategy for a distributed system",
            state_vector=np.random.RandomState(42).randn(64),
            complexity=0.7,
        )
        assert result.architecture is not None
        assert result.genome is not None
        assert result.action is not None

        # Cross-backbone transfer
        transferred = bridge.transfer_between_backbones("claude", "gemini")
        assert transferred is not None

        # Benchmark
        if result.architecture:
            benchmark = bridge.benchmark_architecture(result.architecture)
            assert benchmark is not None

    @pytest.mark.asyncio
    async def test_parallel_phase1_phase2_phase3_phase4(self) -> None:
        """All four phases can coexist."""
        from src.bridge.phase1_liquid_bridge import Phase1LiquidBridge
        from src.bridge.phase2_mycorrhizal_bridge import Phase2MycorrhizalBridge
        from src.bridge.phase3_causal_orch_bridge import Phase3CausalOrchestrationBridge
        from src.l1.liquid_perceptor import DataPoint, ModalityType

        p1 = Phase1LiquidBridge(enable_snn=False, enable_routing=False)
        await p1.initialize()

        p2 = Phase2MycorrhizalBridge(enable_validator=False, enable_swarm=False)
        await p2.initialize()

        p3 = Phase3CausalOrchestrationBridge()
        await p3.initialize()

        p4 = Phase4GenomeTwinBridge()
        await p4.initialize()

        # All four initialized
        assert p1.is_initialized and p2.is_initialized and p3.is_initialized and p4.is_initialized

        # Process through all four
        p1_result = await p1.process(DataPoint(
            modality=ModalityType.TIME_SERIES,
            vector=np.random.RandomState(42).randn(20).astype(np.float64),
        ))
        assert p1_result.percept is not None

        p2_result = await p2.process_claim("Market is bullish", agent_id="a1")
        assert p2_result.trace is not None

        p3_result = await p3.plan_and_execute("Analyze data")
        assert p3_result.execution_plan is not None

        p4_result = await p4.evolve_and_simulate(
            "Synthesize findings",
            state_vector=np.random.RandomState(42).randn(64),
        )
        assert p4_result.architecture is not None
