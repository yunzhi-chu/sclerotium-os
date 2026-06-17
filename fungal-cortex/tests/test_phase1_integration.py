"""Integration tests for Phase 1: L1 Liquid Perception → L2 Liquid Routing bridge."""

import asyncio

import numpy as np
import pytest

from src.bridge.phase1_liquid_bridge import (
    Phase1LiquidBridge,
    Phase1Result,
    ProcessingPath,
)
from src.l1.liquid_perceptor import DataPoint, ModalityType


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def bridge() -> Phase1LiquidBridge:
    """Bridge with routing enabled, SNN disabled (faster tests)."""
    return Phase1LiquidBridge(enable_snn=False, enable_routing=True)


@pytest.fixture
def bridge_with_snn() -> Phase1LiquidBridge:
    """Bridge with all Phase 1 features enabled."""
    return Phase1LiquidBridge(enable_snn=True, enable_routing=True)


@pytest.fixture
def sample_data() -> DataPoint:
    return DataPoint(
        modality=ModalityType.TIME_SERIES,
        vector=np.random.RandomState(42).randn(20).astype(np.float64),
        metadata={"source": "test"},
    )


# ═══════════════════════════════════════════════════════════════════════
# Unit Tests
# ═══════════════════════════════════════════════════════════════════════


class TestBridgeLifecycle:
    """Test bridge initialization and shutdown."""

    def test_initial_state(self, bridge: Phase1LiquidBridge) -> None:
        assert bridge.is_initialized is False
        assert bridge._process_count == 0

    @pytest.mark.asyncio
    async def test_initialize(self, bridge: Phase1LiquidBridge) -> None:
        await bridge.initialize()
        assert bridge.is_initialized is True

    @pytest.mark.asyncio
    async def test_shutdown(self, bridge: Phase1LiquidBridge) -> None:
        await bridge.initialize()
        await bridge.shutdown()
        assert bridge.is_initialized is False

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, bridge: Phase1LiquidBridge) -> None:
        await bridge.initialize()
        await bridge.initialize()  # Second call should be safe
        assert bridge.is_initialized is True


class TestBridgeProcessing:
    """Test the L1→L2 pipeline through the bridge."""

    @pytest.mark.asyncio
    async def test_process_single(
        self, bridge: Phase1LiquidBridge, sample_data: DataPoint,
    ) -> None:
        await bridge.initialize()
        result = await bridge.process(
            sample_data,
            task_description="Analyze this market data",
            task_complexity=0.5,
        )
        assert isinstance(result, Phase1Result)
        assert result.processing_path == ProcessingPath.V4_LIQUID
        assert result.percept is not None
        assert result.hyper_params is not None
        assert result.routing_decision is not None  # routing enabled
        assert result.latency_ms >= 0.0

    @pytest.mark.asyncio
    async def test_process_increments_count(
        self, bridge: Phase1LiquidBridge, sample_data: DataPoint,
    ) -> None:
        await bridge.initialize()
        assert bridge._process_count == 0
        await bridge.process(sample_data)
        assert bridge._process_count == 1
        await bridge.process(sample_data)
        assert bridge._process_count == 2

    @pytest.mark.asyncio
    async def test_process_without_routing(
        self, sample_data: DataPoint,
    ) -> None:
        """Bridge without routing should still process L1+L2a."""
        b = Phase1LiquidBridge(enable_routing=False)
        await b.initialize()
        result = await b.process(sample_data)
        assert result.percept is not None
        assert result.hyper_params is not None
        assert result.routing_decision is None  # routing disabled

    @pytest.mark.asyncio
    async def test_process_batch(
        self, bridge: Phase1LiquidBridge,
    ) -> None:
        await bridge.initialize()
        rng = np.random.RandomState(99)
        batch = [
            DataPoint(
                modality=ModalityType.TIME_SERIES,
                vector=rng.randn(20).astype(np.float64),
            )
            for _ in range(5)
        ]
        results = await bridge.process_batch(batch)
        assert len(results) == 5
        for r in results:
            assert isinstance(r, Phase1Result)

    @pytest.mark.asyncio
    async def test_process_stream(
        self, bridge: Phase1LiquidBridge,
    ) -> None:
        await bridge.initialize()
        rng = np.random.RandomState(42)

        async def data_stream():
            for _ in range(3):
                yield DataPoint(
                    modality=ModalityType.TIME_SERIES,
                    vector=rng.randn(20).astype(np.float64),
                )

        results = []
        async for result in bridge.process_stream(data_stream()):
            results.append(result)

        assert len(results) == 3


class TestBridgeSNN:
    """Test SNN encoding through the bridge."""

    @pytest.mark.asyncio
    async def test_process_with_snn(
        self, bridge_with_snn: Phase1LiquidBridge, sample_data: DataPoint,
    ) -> None:
        await bridge_with_snn.initialize()
        result = await bridge_with_snn.process(sample_data)
        assert result.spike_train is not None
        assert result.spike_train.spike_count >= 0

    def test_infer_snn_error_without_snn(self, bridge: Phase1LiquidBridge) -> None:
        with pytest.raises(RuntimeError, match="SNN encoder not enabled"):
            bridge.infer_snn(np.random.randn(64))


class TestLegacyCompatibility:
    """Test compatibility with v3.0 interfaces."""

    @pytest.mark.asyncio
    async def test_to_regime_context(
        self, bridge: Phase1LiquidBridge, sample_data: DataPoint,
    ) -> None:
        await bridge.initialize()
        result = await bridge.process(sample_data)
        regime_dist = bridge.to_regime_context(result)
        assert len(regime_dist) == 6  # v3.0 expects 6-dim
        assert abs(sum(regime_dist) - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_to_strategy_weights(
        self, bridge: Phase1LiquidBridge, sample_data: DataPoint,
    ) -> None:
        await bridge.initialize()
        result = await bridge.process(sample_data)
        weights = bridge.to_strategy_weights(result)
        assert len(weights) == 12  # v4.0 has 12 strategies
        assert abs(sum(weights) - 1.0) < 0.02  # Softmax

    @pytest.mark.asyncio
    async def test_to_safety_thresholds(
        self, bridge: Phase1LiquidBridge, sample_data: DataPoint,
    ) -> None:
        await bridge.initialize()
        result = await bridge.process(sample_data)
        thresholds = bridge.to_safety_thresholds(result)
        assert len(thresholds) == 8
        assert all(t > 0 for t in thresholds)  # Softplus > 0


class TestBridgeStats:
    """Test bridge statistics."""

    def test_stats_initial(self, bridge: Phase1LiquidBridge) -> None:
        stats = bridge.stats
        assert stats["initialized"] is False
        assert stats["process_count"] == 0
        assert "l1" in stats
        assert "l2_ltn" in stats

    @pytest.mark.asyncio
    async def test_stats_after_processing(
        self, bridge: Phase1LiquidBridge, sample_data: DataPoint,
    ) -> None:
        await bridge.initialize()
        await bridge.process(sample_data)
        stats = bridge.stats
        assert stats["process_count"] == 1
        assert stats["last_result"] is not None
        assert "regime" in stats["last_result"]
        assert "tau" in stats["last_result"]


class TestBridgeModelRegistration:
    """Test model registration through the bridge."""

    def test_list_registered_models(self, bridge: Phase1LiquidBridge) -> None:
        models = bridge.list_registered_models()
        assert len(models) == 7  # Default pool

    def test_register_custom_model(self, bridge: Phase1LiquidBridge) -> None:
        from src.l2.multi_model_router import ModelProfile, ModelTier
        custom = ModelProfile(
            model_id="custom-model",
            tier=ModelTier.LOCAL_SMALL,
            provider="custom",
        )
        bridge.register_model(custom)
        assert "custom-model" in bridge.list_registered_models()

    def test_list_models_without_router(self) -> None:
        b = Phase1LiquidBridge(enable_routing=False)
        assert b.list_registered_models() == []


class TestBridgeReset:
    """Test bridge reset."""

    @pytest.mark.asyncio
    async def test_reset(
        self, bridge: Phase1LiquidBridge, sample_data: DataPoint,
    ) -> None:
        await bridge.initialize()
        await bridge.process(sample_data)
        assert bridge._process_count == 1

        bridge.reset()
        assert bridge._process_count == 0
        assert bridge._last_result is None


# ═══════════════════════════════════════════════════════════════════════
# Cross-Layer Integration Tests
# ═══════════════════════════════════════════════════════════════════════


class TestFullPhase1Pipeline:
    """End-to-end Phase 1 pipeline tests."""

    @pytest.mark.asyncio
    async def test_multimodal_processing(self) -> None:
        """Process different modalities through the bridge."""
        bridge = Phase1LiquidBridge(enable_snn=False, enable_routing=True)
        await bridge.initialize()

        modalities = [
            (ModalityType.TIME_SERIES, np.random.randn(20)),
            (ModalityType.TEXT, np.random.randn(768)),
            (ModalityType.AUDIO, np.random.randn(256)),
        ]

        for mod, vec in modalities:
            dp = DataPoint(modality=mod, vector=vec.astype(np.float64))
            result = await bridge.process(dp, task_description=f"Process {mod.value}")
            assert result.percept.modality == mod

    @pytest.mark.asyncio
    async def test_tau_feedback_loop(self) -> None:
        """Verify the L2→L1 tau feedback loop operates through the bridge."""
        bridge = Phase1LiquidBridge(enable_routing=False)
        await bridge.initialize()

        initial_tau = bridge.perceptor._state.tau
        taus = [initial_tau]

        rng = np.random.RandomState(777)
        for _ in range(20):
            dp = DataPoint(
                modality=ModalityType.TIME_SERIES,
                vector=rng.randn(20).astype(np.float64),
            )
            result = await bridge.process(dp)
            taus.append(result.percept.tau_used)

        # Tau should have adapted during processing
        assert taus[-1] != initial_tau
        # Tau should stay within bounds
        assert all(0.05 <= t <= 5.0 for t in taus)

    @pytest.mark.asyncio
    async def test_v3_compatibility_flow(self) -> None:
        """Phase 1 bridge → v3.0 AdaptiveHyperNetwork compatibility."""
        from src.adaptive.hypernetwork import AdaptiveHyperNetwork

        bridge = Phase1LiquidBridge(enable_routing=False)
        await bridge.initialize()

        # Process through Phase 1
        dp = DataPoint(
            modality=ModalityType.TIME_SERIES,
            vector=np.random.randn(20).astype(np.float64),
        )
        result = await bridge.process(dp)

        # Convert to v3.0 format
        regime_dist = bridge.to_regime_context(result)
        strategy_weights = bridge.to_strategy_weights(result)
        safety_thresholds = bridge.to_safety_thresholds(result)

        # Feed into v3.0 HyperNetwork (should accept the format)
        hn = AdaptiveHyperNetwork()

        # v3.0 expects 6-dim regime → generates 8-dim strategy / 24-dim indicator / 5-dim safety
        v3_output = hn.forward(regime_dist)
        assert len(v3_output.strategy_weights) == 8  # Legacy 8-dim

        # v4.0 provides 12-dim strategy / 32-dim indicator / 8-dim safety
        assert len(strategy_weights) == 12  # Enhanced 12-dim
        assert len(safety_thresholds) == 8   # Enhanced 8-dim

    @pytest.mark.asyncio
    async def test_concurrent_processing(self) -> None:
        """Multiple bridges can process independently (no shared state issues)."""
        b1 = Phase1LiquidBridge()
        b2 = Phase1LiquidBridge()
        await b1.initialize()
        await b2.initialize()

        dp1 = DataPoint(
            modality=ModalityType.TIME_SERIES,
            vector=np.random.randn(20).astype(np.float64),
        )
        dp2 = DataPoint(
            modality=ModalityType.TEXT,
            vector=np.random.randn(768).astype(np.float64),
        )

        # Process concurrently
        r1, r2 = await asyncio.gather(
            b1.process(dp1, task_description="Task 1"),
            b2.process(dp2, task_description="Task 2"),
        )

        assert r1.percept.modality == ModalityType.TIME_SERIES
        assert r2.percept.modality == ModalityType.TEXT
        # Each bridge maintains independent state
        assert b1._process_count == 1
        assert b2._process_count == 1
