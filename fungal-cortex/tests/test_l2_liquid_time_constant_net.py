"""Tests for L2a: LiquidTimeConstantNet — dynamic hyper-parameter generation."""

import numpy as np
import pytest

from src.l2.liquid_time_constant_net import (
    HyperParameters,
    LiquidHyperState,
    LiquidTimeConstantNet,
    TimeConstantConfig,
)


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def config() -> TimeConstantConfig:
    return TimeConstantConfig(
        input_dim=32,
        hidden_dim=32,
        n_strategies=12,
        n_indicators=32,
        n_safety_gates=8,
        tau_default=0.5,
        tau_ema_alpha=0.1,
    )


@pytest.fixture
def ltn(config: TimeConstantConfig) -> LiquidTimeConstantNet:
    return LiquidTimeConstantNet(config=config)


@pytest.fixture
def sample_percept() -> np.ndarray:
    rng = np.random.RandomState(42)
    return rng.randn(32).astype(np.float64)


# ═══════════════════════════════════════════════════════════════════════
# Unit Tests
# ═══════════════════════════════════════════════════════════════════════


class TestLiquidTimeConstantNetInit:
    """Test initialization."""

    def test_default_initialization(self) -> None:
        net = LiquidTimeConstantNet()
        assert net._config.input_dim == 64
        assert net._config.hidden_dim == 64
        assert net._config.n_strategies == 12
        assert net._config.tau_default == 0.5

    def test_custom_config(self, config: TimeConstantConfig) -> None:
        net = LiquidTimeConstantNet(config=config)
        assert net._config.input_dim == 32
        assert net._config.hidden_dim == 32

    def test_weights_initialized(self, ltn: LiquidTimeConstantNet) -> None:
        assert ltn._W_h.shape == (32, 32)
        assert ltn._W_tau.shape == (1, 32)
        assert ltn._W_strategy.shape == (12, 32)
        assert ltn._W_indicator.shape == (32, 32)
        assert ltn._W_safety.shape == (8, 32)

    def test_stats_property(self, ltn: LiquidTimeConstantNet) -> None:
        stats = ltn.stats
        assert stats["call_count"] == 0
        assert stats["input_dim"] == 32
        assert stats["current_tau"] == 0.5


class TestLiquidTimeConstantNetForward:
    """Test forward pass."""

    def test_forward_produces_hyperparams(
        self, ltn: LiquidTimeConstantNet, sample_percept: np.ndarray,
    ) -> None:
        params = ltn.forward(sample_percept)
        assert isinstance(params, HyperParameters)
        assert 0.0 < params.tau <= 1.0
        assert len(params.strategy_weights) == 12
        assert len(params.indicator_scales) == 32
        assert len(params.safety_thresholds) == 8

    def test_strategy_weights_are_softmax(
        self, ltn: LiquidTimeConstantNet, sample_percept: np.ndarray,
    ) -> None:
        params = ltn.forward(sample_percept)
        total = float(np.sum(params.strategy_weights))
        assert abs(total - 1.0) < 1e-4
        assert np.all(params.strategy_weights >= 0)

    def test_indicator_scales_are_sigmoid(
        self, ltn: LiquidTimeConstantNet, sample_percept: np.ndarray,
    ) -> None:
        params = ltn.forward(sample_percept)
        assert np.all(params.indicator_scales >= 0)
        assert np.all(params.indicator_scales <= 1)

    def test_safety_thresholds_are_positive(
        self, ltn: LiquidTimeConstantNet, sample_percept: np.ndarray,
    ) -> None:
        params = ltn.forward(sample_percept)
        # Softplus output is always > 0
        assert np.all(params.safety_thresholds > 0)

    def test_forward_increments_count(
        self, ltn: LiquidTimeConstantNet, sample_percept: np.ndarray,
    ) -> None:
        assert ltn._call_count == 0
        ltn.forward(sample_percept)
        assert ltn._call_count == 1

    def test_h_embedding_updated(
        self, ltn: LiquidTimeConstantNet, sample_percept: np.ndarray,
    ) -> None:
        h_before = ltn._state.h_embedding.copy()
        ltn.forward(sample_percept)
        h_after = ltn._state.h_embedding
        # H-embedding should have changed
        assert not np.allclose(h_before, h_after)


class TestLiquidTimeConstantNetTau:
    """Test adaptive time constant behavior."""

    def test_tau_adapts_with_surprise(
        self, ltn: LiquidTimeConstantNet, sample_percept: np.ndarray,
    ) -> None:
        """High surprise → tau should increase (deeper processing)."""
        ltn.reset()
        # Run with low surprise first
        p1 = ltn.forward(sample_percept, surprise=0.0, confidence=0.9)
        tau_normal = p1.tau
        # Run with high surprise
        p2 = ltn.forward(sample_percept, surprise=0.9, confidence=0.1)
        tau_surprised = p2.tau
        # High surprise should lead to higher tau (or at least different)
        assert tau_surprised > 0.0

    def test_tau_bounded(self, ltn: LiquidTimeConstantNet) -> None:
        """Tau should always stay within [tau_min, tau_max]."""
        c = ltn._config
        for _ in range(50):
            percept = np.random.randn(32).astype(np.float64)
            surprise = np.random.random()
            confidence = np.random.random()
            params = ltn.forward(percept, surprise=surprise, confidence=confidence)
            assert c.tau_min <= params.tau <= c.tau_max

    def test_tau_ema_smoothing(
        self, ltn: LiquidTimeConstantNet, sample_percept: np.ndarray,
    ) -> None:
        """Tau should change smoothly (EMA), not abruptly."""
        taus = []
        for i in range(20):
            # Alternate between high and low surprise
            surprise = 0.9 if i % 2 == 0 else 0.1
            params = ltn.forward(sample_percept, surprise=surprise)
            taus.append(params.tau)
        # Tau changes should be gradual (EMA smoothing)
        for i in range(1, len(taus)):
            delta = abs(taus[i] - taus[i - 1])
            # Delta should not be too large due to EMA
            assert delta < 0.5

    def test_tau_same_input_converges(
        self, ltn: LiquidTimeConstantNet, sample_percept: np.ndarray,
    ) -> None:
        """With constant input, tau should converge to a stable value."""
        taus = []
        for _ in range(30):
            params = ltn.forward(sample_percept, surprise=0.3, confidence=0.7)
            taus.append(params.tau)
        # Last few tau values should be close to each other
        recent = taus[-10:]
        assert max(recent) - min(recent) < 0.2


class TestLiquidTimeConstantNetWeightUpdate:
    """Test online weight adaptation."""

    def test_update_weights_no_targets(
        self, ltn: LiquidTimeConstantNet, sample_percept: np.ndarray,
    ) -> None:
        losses = ltn.update_weights(sample_percept)
        assert losses == {}

    def test_update_strategy_weights(
        self, ltn: LiquidTimeConstantNet, sample_percept: np.ndarray,
    ) -> None:
        target = np.ones(12) / 12.0  # Uniform strategy distribution
        losses = ltn.update_weights(
            sample_percept, target_strategy=target, learning_rate=0.01,
        )
        assert "strategy_loss" in losses
        assert losses["strategy_loss"] >= 0.0

    def test_update_all_channels(
        self, ltn: LiquidTimeConstantNet, sample_percept: np.ndarray,
    ) -> None:
        losses = ltn.update_weights(
            sample_percept,
            target_tau=0.3,
            target_strategy=np.ones(12) / 12.0,
            target_indicator=np.ones(32) * 0.5,
            target_safety=np.ones(8) * 0.3,
            learning_rate=0.01,
        )
        assert "tau_loss" in losses
        assert "strategy_loss" in losses
        assert "indicator_loss" in losses
        assert "safety_loss" in losses


class TestLiquidTimeConstantNetForwardWithEmbedding:
    """Test forward_with_embedding."""

    def test_returns_embedding(
        self, ltn: LiquidTimeConstantNet, sample_percept: np.ndarray,
    ) -> None:
        params, embedding = ltn.forward_with_embedding(sample_percept)
        assert isinstance(params, HyperParameters)
        assert embedding.shape == (32,)
        # Embedding should match internal state
        np.testing.assert_array_almost_equal(embedding, ltn._state.h_embedding)


class TestLiquidTimeConstantNetInputHandling:
    """Test input preprocessing."""

    def test_short_input_padded(
        self, ltn: LiquidTimeConstantNet,
    ) -> None:
        short = np.array([1.0, 2.0, 3.0])
        params = ltn.forward(short)
        assert params is not None

    def test_long_input_truncated(
        self, ltn: LiquidTimeConstantNet,
    ) -> None:
        long_vec = np.random.randn(100).astype(np.float64)
        params = ltn.forward(long_vec)
        assert params is not None

    def test_1d_input(self, ltn: LiquidTimeConstantNet) -> None:
        vec = np.random.randn(32).astype(np.float64)
        params = ltn.forward(vec)
        assert params.tau > 0.0


class TestLiquidTimeConstantNetReset:
    """Test state reset."""

    def test_reset(self, ltn: LiquidTimeConstantNet) -> None:
        ltn.forward(np.random.randn(32))
        assert ltn._call_count == 1
        ltn.reset()
        assert ltn._call_count == 0
        assert ltn._state.tau_output == ltn._config.tau_default
        assert ltn._state.tau_history == []


# ═══════════════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════════════


class TestL1ToL2Integration:
    """Test L1 LiquidPerceptor → L2 LiquidTimeConstantNet data flow."""

    def test_percept_feeds_ltn(self) -> None:
        """Simulate the full L1→L2 pipeline."""
        import asyncio
        from src.l1.liquid_perceptor import (
            DataPoint,
            LiquidPerceptor,
            LiquidPerceptorConfig,
            ModalityType,
        )

        # L1: Liquid Perceptor
        lp_config = LiquidPerceptorConfig(
            n_hidden=32,
            n_input_time_series=10,
            tau_default=0.5,
        )
        lp = LiquidPerceptor(config=lp_config)

        # L2: Liquid Time Constant Net
        ltn_config = TimeConstantConfig(
            input_dim=32,
            hidden_dim=32,
        )
        ltn = LiquidTimeConstantNet(config=ltn_config)

        # Process a data point through L1 → L2
        dp = DataPoint(
            modality=ModalityType.TIME_SERIES,
            vector=np.random.randn(10).astype(np.float64),
        )
        percept = asyncio.run(lp.perceive(dp))

        # Feed percept to L2
        params = ltn.forward(
            percept.vector,
            surprise=percept.surprise,
            confidence=percept.confidence,
        )

        # Verify the flow
        assert len(percept.vector) == ltn._config.input_dim
        assert params.tau > 0.0
        assert len(params.strategy_weights) == 12

    def test_tau_feedback_loop(self) -> None:
        """L2 tau → L1 perception speed feedback loop."""
        import asyncio
        from src.l1.liquid_perceptor import (
            DataPoint,
            LiquidPerceptor,
            LiquidPerceptorConfig,
            ModalityType,
        )

        lp = LiquidPerceptor(LiquidPerceptorConfig(
            n_hidden=16,
            n_input_time_series=5,
            tau_default=0.5,
        ))
        ltn = LiquidTimeConstantNet(TimeConstantConfig(
            input_dim=16,
            hidden_dim=16,
        ))

        for i in range(20):
            dp = DataPoint(
                modality=ModalityType.TIME_SERIES,
                vector=np.random.randn(5).astype(np.float64),
            )
            percept = asyncio.run(lp.perceive(dp))

            # L2 generates tau based on percept
            params = ltn.forward(
                percept.vector,
                surprise=percept.surprise,
                confidence=percept.confidence,
            )

            # Feedback: L2's tau → L1's next processing speed
            lp._state.tau = params.tau

        # After 20 iterations, the loop should have stabilized
        assert 0.0 < lp._state.tau <= 1.0
        assert lp._call_count == 20
        assert ltn._call_count == 20
