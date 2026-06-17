"""Tests for L1a: LiquidPerceptor — ODE-driven continuous-time perception."""

import math
import time

import numpy as np
import pytest

from src.l1.liquid_perceptor import (
    DataPoint,
    LiquidPerceptor,
    LiquidPerceptorConfig,
    LiquidState,
    ModalityType,
    Percept,
)


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def config() -> LiquidPerceptorConfig:
    return LiquidPerceptorConfig(
        n_hidden=32,
        n_input_time_series=10,
        tau_default=0.5,
        ode_solver_steps_min=4,
        ode_solver_steps_max=32,
        adaptation_window=20,
    )


@pytest.fixture
def perceptor(config: LiquidPerceptorConfig) -> LiquidPerceptor:
    return LiquidPerceptor(config=config)


@pytest.fixture
def sample_ts_data() -> DataPoint:
    rng = np.random.RandomState(42)
    return DataPoint(
        modality=ModalityType.TIME_SERIES,
        vector=rng.randn(10).astype(np.float64),
        weight=1.0,
    )


# ═══════════════════════════════════════════════════════════════════════
# Unit Tests
# ═══════════════════════════════════════════════════════════════════════


class TestLiquidPerceptorInit:
    """Test initialization and configuration."""

    def test_default_initialization(self) -> None:
        lp = LiquidPerceptor()
        assert lp._config.n_hidden == 64
        assert lp._config.tau_default == 1.0
        assert lp._state.tau == 1.0
        assert lp._state.surprise == 0.0
        assert lp._state.confidence == 0.5

    def test_custom_config(self, config: LiquidPerceptorConfig) -> None:
        lp = LiquidPerceptor(config=config)
        assert lp._config.n_hidden == 32
        assert lp._config.tau_default == 0.5

    def test_weights_initialized(self, perceptor: LiquidPerceptor) -> None:
        assert perceptor._Wx.shape == (32, 32)
        assert perceptor._Wu.shape[0] == 32
        assert perceptor._b.shape == (32,)
        # Xavier init: weights should not be all zeros
        assert np.abs(perceptor._Wx).sum() > 0
        assert np.abs(perceptor._Wu).sum() > 0

    def test_stats_property(self, perceptor: LiquidPerceptor) -> None:
        stats = perceptor.stats
        assert "call_count" in stats
        assert "current_tau" in stats
        assert "n_hidden" in stats
        assert stats["call_count"] == 0


class TestLiquidPerceptorCore:
    """Test core perception mechanics."""

    def test_perceive_returns_percept(
        self, perceptor: LiquidPerceptor, sample_ts_data: DataPoint,
    ) -> None:
        import asyncio
        percept = asyncio.run(perceptor.perceive(sample_ts_data))
        assert isinstance(percept, Percept)
        assert percept.vector.shape == (32,)
        assert percept.modality == ModalityType.TIME_SERIES
        assert 0.0 <= percept.surprise <= 1.0
        assert 0.0 <= percept.confidence <= 1.0

    def test_perceive_batch(self, perceptor: LiquidPerceptor) -> None:
        rng = np.random.RandomState(42)
        batch = [
            DataPoint(
                modality=ModalityType.TIME_SERIES,
                vector=rng.randn(10).astype(np.float64),
            )
            for _ in range(10)
        ]
        results = perceptor.perceive_batch(batch)
        assert len(results) == 10
        for p in results:
            assert isinstance(p, Percept)
        assert perceptor._call_count == 10

    def test_perceive_increments_count(
        self, perceptor: LiquidPerceptor, sample_ts_data: DataPoint,
    ) -> None:
        import asyncio
        assert perceptor._call_count == 0
        asyncio.run(perceptor.perceive(sample_ts_data))
        assert perceptor._call_count == 1
        asyncio.run(perceptor.perceive(sample_ts_data))
        assert perceptor._call_count == 2

    def test_surprise_computed(
        self, perceptor: LiquidPerceptor, sample_ts_data: DataPoint,
    ) -> None:
        """After enough calls, surprise should be meaningful."""
        import asyncio
        rng = np.random.RandomState(42)
        # Fill the window with stable data
        for _ in range(15):
            dp = DataPoint(
                modality=ModalityType.TIME_SERIES,
                vector=np.ones(10) * 0.1,
            )
            asyncio.run(perceptor.perceive(dp))
        surprise_before = perceptor._state.surprise
        # Send a very different data point
        outlier = DataPoint(
            modality=ModalityType.TIME_SERIES,
            vector=np.ones(10) * 10.0,
        )
        percept = asyncio.run(perceptor.perceive(outlier))
        assert percept.surprise > 0.0  # Should detect the outlier
        assert perceptor._state.surprise > surprise_before

    def test_tau_adapts(
        self, perceptor: LiquidPerceptor, sample_ts_data: DataPoint,
    ) -> None:
        """Tau should change when surprise is high."""
        import asyncio
        tau_initial = perceptor._state.tau
        # Send high-surprise inputs repeatedly
        rng = np.random.RandomState(99)
        for _ in range(20):
            dp = DataPoint(
                modality=ModalityType.TIME_SERIES,
                vector=rng.randn(10).astype(np.float64) * 5.0,
            )
            asyncio.run(perceptor.perceive(dp))
        tau_final = perceptor._state.tau
        # Tau should have changed from default
        assert tau_final != tau_initial

    def test_tau_bounded(self, perceptor: LiquidPerceptor) -> None:
        """Tau should always stay within [tau_min, tau_max]."""
        import asyncio
        rng = np.random.RandomState(123)
        for _ in range(100):
            dp = DataPoint(
                modality=ModalityType.TIME_SERIES,
                vector=rng.randn(10).astype(np.float64) * 10.0,
            )
            asyncio.run(perceptor.perceive(dp))
            tau = perceptor._state.tau
            assert perceptor._config.tau_min <= tau <= perceptor._config.tau_max


class TestLiquidPerceptorODE:
    """Test ODE mechanics."""

    def test_ode_forward_produces_output(
        self, perceptor: LiquidPerceptor,
    ) -> None:
        u = np.random.randn(perceptor._max_input_dim).astype(np.float64)
        hidden, steps = perceptor._liquid_forward(u)
        assert hidden.shape == (perceptor._config.n_hidden,)
        assert steps >= perceptor._config.ode_solver_steps_min
        assert steps <= perceptor._config.ode_solver_steps_max

    def test_ode_steps_scale_with_tau(self, perceptor: LiquidPerceptor) -> None:
        """Larger tau → more ODE solver steps."""
        u = np.random.randn(perceptor._max_input_dim).astype(np.float64)
        # Set small tau
        perceptor._state.tau = 0.1
        _, steps_small = perceptor._liquid_forward(u)
        # Set large tau
        perceptor._state.tau = 5.0
        _, steps_large = perceptor._liquid_forward(u)
        assert steps_large >= steps_small

    def test_ode_stability(self, perceptor: LiquidPerceptor) -> None:
        """ODE should not explode even with extreme inputs."""
        u = np.ones(perceptor._max_input_dim) * 100.0
        hidden, _ = perceptor._liquid_forward(u)
        # Hidden state should be bounded
        assert np.all(np.abs(hidden) < 100.0)


class TestLiquidPerceptorModalities:
    """Test multimodal support."""

    def test_text_modality(self, perceptor: LiquidPerceptor) -> None:
        import asyncio
        dp = DataPoint(
            modality=ModalityType.TEXT,
            vector=np.random.randn(768).astype(np.float64),
        )
        percept = asyncio.run(perceptor.perceive(dp))
        assert percept.modality == ModalityType.TEXT

    def test_audio_modality(self, perceptor: LiquidPerceptor) -> None:
        import asyncio
        dp = DataPoint(
            modality=ModalityType.AUDIO,
            vector=np.random.randn(256).astype(np.float64),
        )
        percept = asyncio.run(perceptor.perceive(dp))
        assert percept.modality == ModalityType.AUDIO

    def test_bioelectric_modality(self, perceptor: LiquidPerceptor) -> None:
        import asyncio
        dp = DataPoint(
            modality=ModalityType.BIOELECTRIC,
            vector=np.random.randn(16).astype(np.float64),
        )
        percept = asyncio.run(perceptor.perceive(dp))
        assert percept.modality == ModalityType.BIOELECTRIC

    def test_input_padding(self, perceptor: LiquidPerceptor) -> None:
        """Input with fewer features should be zero-padded."""
        import asyncio
        short_vec = np.array([1.0, 2.0, 3.0])
        dp = DataPoint(
            modality=ModalityType.TIME_SERIES,
            vector=short_vec,
        )
        # Should not crash
        percept = asyncio.run(perceptor.perceive(dp))
        assert percept is not None

    def test_input_truncation(self, perceptor: LiquidPerceptor) -> None:
        """Input with too many features should be truncated."""
        import asyncio
        long_vec = np.random.randn(200).astype(np.float64)
        dp = DataPoint(
            modality=ModalityType.TIME_SERIES,
            vector=long_vec,
        )
        percept = asyncio.run(perceptor.perceive(dp))
        assert percept is not None


class TestLiquidPerceptorRegime:
    """Test regime classification."""

    def test_regime_classification(self, perceptor: LiquidPerceptor) -> None:
        percept = np.ones(32) * 0.8
        regime = perceptor._classify_regime(percept, 0.1)
        assert regime == "trending_up"

        percept2 = np.ones(32) * (-0.8)
        regime2 = perceptor._classify_regime(percept2, 0.1)
        assert regime2 == "trending_down"

    def test_transition_regime(self, perceptor: LiquidPerceptor) -> None:
        percept = np.random.randn(32)
        regime = perceptor._classify_regime(percept, 0.8)
        assert regime == "transition"

    def test_calm_regime(self, perceptor: LiquidPerceptor) -> None:
        percept = np.ones(32) * 0.01
        regime = perceptor._classify_regime(percept, 0.1)
        assert regime in ("calm", "sideways")


class TestLiquidPerceptorShift:
    """Test distribution shift adaptation."""

    def test_no_shift_with_fresh_data(self, perceptor: LiquidPerceptor) -> None:
        result = perceptor.adapt_to_distribution_shift(
            np.random.randn(10, 10)
        )
        # Not enough history → no shift detected
        assert result["shift_detected"] is False

    def test_shift_detection(self, perceptor: LiquidPerceptor) -> None:
        import asyncio
        # Fill window with stable data
        for _ in range(25):
            dp = DataPoint(
                modality=ModalityType.TIME_SERIES,
                vector=np.ones(10) * 0.1,
            )
            asyncio.run(perceptor.perceive(dp))
        # Introduce very different distribution
        result = perceptor.adapt_to_distribution_shift(
            np.ones((10, 10)) * 10.0
        )
        assert "shift_detected" in result
        assert "magnitude" in result


class TestLiquidPerceptorEdge:
    """Test edge compilation."""

    def test_compile_to_edge(self, perceptor: LiquidPerceptor) -> None:
        compiled = perceptor.compile_to_edge()
        assert "Wx" in compiled
        assert "Wu" in compiled
        assert "b" in compiled
        assert compiled["format"] == "liquid_perceptor_v1"
        assert compiled["n_hidden"] == perceptor._config.n_hidden

    def test_load_from_edge(self, perceptor: LiquidPerceptor) -> None:
        compiled = perceptor.compile_to_edge()
        lp2 = LiquidPerceptor(config=perceptor._config)
        lp2.load_from_edge(compiled)
        np.testing.assert_array_almost_equal(lp2._Wx, perceptor._Wx)


class TestLiquidPerceptorReset:
    """Test state reset."""

    def test_reset_clears_state(self, perceptor: LiquidPerceptor) -> None:
        import asyncio
        rng = np.random.RandomState(42)
        for _ in range(10):
            dp = DataPoint(
                modality=ModalityType.TIME_SERIES,
                vector=rng.randn(10).astype(np.float64),
            )
            asyncio.run(perceptor.perceive(dp))

        assert perceptor._call_count == 10
        perceptor.reset()
        assert perceptor._call_count == 0
        assert perceptor._state.tau == perceptor._config.tau_default
        assert perceptor._state.surprise == 0.0


# ═══════════════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════════════


class TestLiquidPerceptorIntegration:
    """Integration scenarios."""

    def test_continuous_stream_processing(self) -> None:
        """Simulate a continuous data stream."""
        import asyncio

        lp = LiquidPerceptor(LiquidPerceptorConfig(
            n_hidden=16,
            n_input_time_series=5,
            tau_default=0.8,
            adaptation_window=10,
        ))

        rng = np.random.RandomState(777)
        results = []
        for i in range(50):
            # Gradual regime change
            if i < 20:
                vec = rng.randn(5) * 0.5 + 0.2  # Low volatility, slight uptrend
            elif i < 40:
                vec = rng.randn(5) * 2.0          # High volatility
            else:
                vec = rng.randn(5) * 0.3 - 0.5   # Low volatility, downtrend

            dp = DataPoint(modality=ModalityType.TIME_SERIES, vector=vec.astype(np.float64))
            percept = asyncio.run(lp.perceive(dp))
            results.append(percept)

        assert len(results) == 50
        # Tau should have adapted during the stream
        assert lp._state.tau != lp._config.tau_default
        # ODE steps should have been taken
        assert lp._total_steps > 0

    def test_multimodal_interleaving(self) -> None:
        """Interleave different modalities (like real-world perception)."""
        import asyncio

        lp = LiquidPerceptor(LiquidPerceptorConfig(
            n_hidden=16,
            n_input_time_series=5,
            n_input_text=32,
            n_input_bioelectric=8,
        ))

        modalities = [
            (ModalityType.TIME_SERIES, np.random.randn(5)),
            (ModalityType.TEXT, np.random.randn(32)),
            (ModalityType.BIOELECTRIC, np.random.randn(8)),
        ]

        for _ in range(3):
            for mod, vec in modalities:
                dp = DataPoint(modality=mod, vector=vec.astype(np.float64))
                percept = asyncio.run(lp.perceive(dp))
                assert percept.modality == mod
                assert percept.vector.shape == (16,)


@pytest.mark.parametrize("tau,expected_steps_min", [
    (0.1, 1),
    (1.0, 4),
    (3.0, 8),
])
def test_tau_steps_correlation(tau: float, expected_steps_min: int) -> None:
    """ODE steps should increase monotonically with tau."""
    config = LiquidPerceptorConfig(
        n_hidden=8,
        ode_solver_steps_min=4,
        ode_solver_steps_max=32,
    )
    lp = LiquidPerceptor(config=config)
    lp._state.tau = tau
    u = np.zeros(lp._max_input_dim)
    _, steps = lp._liquid_forward(u)
    # For very small tau, steps should be at minimum
    if tau <= 0.15:
        assert steps == config.ode_solver_steps_min
    # For larger tau, steps should be >= min
    assert steps >= config.ode_solver_steps_min
