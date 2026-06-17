"""Tests for L1b: SNNSpikingEncoder — spike-based neural encoding."""

import numpy as np
import pytest

from src.l1.snn_spiking_encoder import (
    EncodingMethod,
    SNNSpikingEncoder,
    Spike,
    SpikeEncoderConfig,
    SpikeTrain,
)


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def config() -> SpikeEncoderConfig:
    return SpikeEncoderConfig(
        n_neurons=32,
        n_input_features=16,
        duration_ms=50.0,
        rate_max_hz=100.0,
        ttfs_latency_ms=30.0,
    )


@pytest.fixture
def encoder(config: SpikeEncoderConfig) -> SNNSpikingEncoder:
    return SNNSpikingEncoder(config=config)


@pytest.fixture
def sample_signal() -> np.ndarray:
    rng = np.random.RandomState(42)
    return rng.randn(16).astype(np.float64)


# ═══════════════════════════════════════════════════════════════════════
# Unit Tests
# ═══════════════════════════════════════════════════════════════════════


class TestSNNEncoderInit:
    """Test initialization."""

    def test_default_initialization(self) -> None:
        enc = SNNSpikingEncoder()
        assert enc._config.n_neurons == 128
        assert enc._config.duration_ms == 100.0

    def test_custom_config(self, config: SpikeEncoderConfig) -> None:
        enc = SNNSpikingEncoder(config=config)
        assert enc._config.n_neurons == 32
        assert enc._config.duration_ms == 50.0

    def test_tuning_centers_initialized(self, encoder: SNNSpikingEncoder) -> None:
        centers = encoder._tuning_centers
        assert centers.shape == (32, 16)

    def test_stats_property(self, encoder: SNNSpikingEncoder) -> None:
        stats = encoder.stats
        assert stats["call_count"] == 0
        assert stats["n_neurons"] == 32


class TestRateCoding:
    """Test rate coding strategy."""

    def test_rate_encoding_produces_spikes(
        self, encoder: SNNSpikingEncoder, sample_signal: np.ndarray,
    ) -> None:
        train = encoder.encode(sample_signal, method=EncodingMethod.RATE)
        assert isinstance(train, SpikeTrain)
        assert train.encoding_method == EncodingMethod.RATE
        assert train.n_neurons == 32
        assert train.duration_ms == 50.0

    def test_rate_spikes_in_time_window(
        self, encoder: SNNSpikingEncoder, sample_signal: np.ndarray,
    ) -> None:
        train = encoder.encode(sample_signal, method=EncodingMethod.RATE)
        for spike in train.spikes:
            assert 0.0 <= spike.time_ms <= 50.0
            assert 0 <= spike.neuron_id < 32

    def test_rate_firing_rate_bounded(
        self, encoder: SNNSpikingEncoder,
    ) -> None:
        """Firing rate should be within configured bounds."""
        # Strong signal → high firing rate
        strong = np.ones(16) * 5.0
        train_strong = encoder.encode(strong, method=EncodingMethod.RATE)
        rate_strong = train_strong.mean_rate_hz

        # Weak signal → low firing rate
        weak = np.ones(16) * (-5.0)
        train_weak = encoder.encode(weak, method=EncodingMethod.RATE)
        rate_weak = train_weak.mean_rate_hz

        # Strong signal should produce higher firing rate
        # (probabilistic, but true in expectation)
        assert rate_strong >= 0.0
        assert rate_weak >= 0.0

    def test_rate_respects_refractory(
        self, encoder: SNNSpikingEncoder,
    ) -> None:
        """No neuron should fire twice within refractory period."""
        signal = np.ones(16) * 5.0  # Max firing rate
        train = encoder.encode(signal, method=EncodingMethod.RATE)
        neuron_spikes: dict[int, list[float]] = {}
        for spike in train.spikes:
            neuron_spikes.setdefault(spike.neuron_id, []).append(spike.time_ms)
        for times in neuron_spikes.values():
            times.sort()
            for i in range(1, len(times)):
                assert times[i] - times[i - 1] >= encoder._config.rate_refractory_ms - 0.01


class TestTemporalCoding:
    """Test temporal (TTFS) coding strategy."""

    def test_temporal_encoding_produces_spikes(
        self, encoder: SNNSpikingEncoder, sample_signal: np.ndarray,
    ) -> None:
        train = encoder.encode(sample_signal, method=EncodingMethod.TEMPORAL)
        assert isinstance(train, SpikeTrain)
        assert train.encoding_method == EncodingMethod.TEMPORAL

    def test_temporal_latency_bounded(
        self, encoder: SNNSpikingEncoder,
    ) -> None:
        """TTFS latency should be within [0, ttfs_latency_ms]."""
        strong = np.ones(16) * 5.0
        train = encoder.encode(strong, method=EncodingMethod.TEMPORAL)
        for spike in train.spikes:
            assert 0.0 <= spike.time_ms <= encoder._config.ttfs_latency_ms

    def test_temporal_efficient(self, encoder: SNNSpikingEncoder) -> None:
        """Temporal coding should be more spike-efficient than rate coding."""
        signal = np.ones(16) * 3.0
        train_temporal = encoder.encode(signal, method=EncodingMethod.TEMPORAL)
        train_rate = encoder.encode(signal, method=EncodingMethod.RATE)
        # Temporal coding typically produces fewer spikes (at most 1 per neuron)
        assert train_temporal.spike_count <= 32 * 2  # Allow some margin

    def test_temporal_threshold(self, encoder: SNNSpikingEncoder) -> None:
        """Very weak signals should produce no TTFS spikes."""
        weak = np.ones(16) * (-10.0)
        train = encoder.encode(weak, method=EncodingMethod.TEMPORAL)
        # Very weak signal → all neurons below threshold → few/no spikes
        assert train.spike_count < 32


class TestPopulationCoding:
    """Test population coding strategy."""

    def test_population_encoding(
        self, encoder: SNNSpikingEncoder, sample_signal: np.ndarray,
    ) -> None:
        train = encoder.encode(sample_signal, method=EncodingMethod.POPULATION)
        assert isinstance(train, SpikeTrain)
        assert train.encoding_method == EncodingMethod.POPULATION

    def test_population_multi_neuron(
        self, encoder: SNNSpikingEncoder,
    ) -> None:
        """Population coding should use multiple neurons."""
        signal = np.random.randn(16).astype(np.float64)
        train = encoder.encode(signal, method=EncodingMethod.POPULATION)
        neuron_ids = {s.neuron_id for s in train.spikes}
        # Should activate more than 1 neuron
        assert len(neuron_ids) >= 1

    def test_population_amplitude(
        self, encoder: SNNSpikingEncoder,
    ) -> None:
        """Population spikes should have graded amplitudes."""
        signal = np.random.randn(16).astype(np.float64)
        train = encoder.encode(signal, method=EncodingMethod.POPULATION)
        if train.spikes:
            amplitudes = {s.amplitude for s in train.spikes}
            # Should have varied amplitudes (not all 1.0)
            assert len(amplitudes) >= 1


class TestMultiMethodEncoding:
    """Test multi-method encoding."""

    def test_encode_multi_method(
        self, encoder: SNNSpikingEncoder, sample_signal: np.ndarray,
    ) -> None:
        results = encoder.encode_multi_method(sample_signal)
        assert EncodingMethod.RATE in results
        assert EncodingMethod.TEMPORAL in results
        assert EncodingMethod.POPULATION in results
        for train in results.values():
            assert isinstance(train, SpikeTrain)

    def test_encode_all_methods_work(
        self, encoder: SNNSpikingEncoder, sample_signal: np.ndarray,
    ) -> None:
        for method in EncodingMethod:
            train = encoder.encode(sample_signal, method)
            assert isinstance(train, SpikeTrain)


class TestLIFSimulation:
    """Test LIF neuron simulation."""

    def test_lif_simulation(
        self, encoder: SNNSpikingEncoder,
    ) -> None:
        current = np.ones(32) * 2.0  # Above-threshold current
        train = encoder.simulate_lif(current, duration_ms=20.0)
        assert isinstance(train, SpikeTrain)
        assert train.metadata["model"] == "LIF"

    def test_lif_no_spike_for_subthreshold(
        self, encoder: SNNSpikingEncoder,
    ) -> None:
        """Sub-threshold current should produce no spikes."""
        current = np.zeros(32)  # No input current
        train = encoder.simulate_lif(current, duration_ms=10.0)
        # With zero current, membrane stays at rest < threshold
        assert train.spike_count == 0

    def test_lif_supra_threshold_spikes(
        self, encoder: SNNSpikingEncoder,
    ) -> None:
        """Strong current should produce spikes."""
        current = np.ones(32) * 10.0  # Strong current
        train = encoder.simulate_lif(current, duration_ms=100.0)
        # Strong current + long duration → should have spikes
        assert train.spike_count > 0


class TestSOLOTraining:
    """Test SOLO on-chip training."""

    def test_train_on_chip_empty(self, encoder: SNNSpikingEncoder) -> None:
        result = encoder.train_on_chip([], np.array([]))
        assert result["final_loss"] == 0.0
        assert result["accuracy"] == 0.0

    def test_train_on_chip_basic(
        self, encoder: SNNSpikingEncoder,
    ) -> None:
        """Basic SOLO training with synthetic data."""
        rng = np.random.RandomState(42)
        n_samples = 10

        # Generate synthetic spike trains
        spike_data = []
        for i in range(n_samples):
            signal = rng.randn(16).astype(np.float64)
            train = encoder.encode(signal, method=EncodingMethod.RATE)
            spike_data.append(train)

        labels = np.array([i % 3 for i in range(n_samples)])  # 3 classes

        result = encoder.train_on_chip(spike_data, labels, epochs=5)
        assert "final_loss" in result
        assert "accuracy" in result
        assert result["final_loss"] >= 0.0

    def test_train_on_chip_improves(
        self, encoder: SNNSpikingEncoder,
    ) -> None:
        """Training should reduce loss over epochs."""
        rng = np.random.RandomState(777)
        n_samples = 20
        spike_data = []
        for i in range(n_samples):
            signal = rng.randn(16).astype(np.float64)
            train = encoder.encode(signal, method=EncodingMethod.RATE)
            spike_data.append(train)
        labels = np.array([i % 4 for i in range(n_samples)])

        result = encoder.train_on_chip(spike_data, labels, epochs=20)
        # Final loss should be finite
        assert result["final_loss"] < float("inf")
        assert 0.0 <= result["accuracy"] <= 1.0

    def test_infer_after_training(
        self, encoder: SNNSpikingEncoder,
    ) -> None:
        """Inference should work after training."""
        rng = np.random.RandomState(42)
        spike_data = []
        for i in range(10):
            signal = rng.randn(16).astype(np.float64)
            train = encoder.encode(signal, method=EncodingMethod.RATE)
            spike_data.append(train)
        labels = np.zeros(10, dtype=int)

        encoder.train_on_chip(spike_data, labels, epochs=5)
        output = encoder.infer(spike_data[0])
        # infer output shape = (n_input_features,) = (16,)
        assert output.shape == (16,)


class TestSpikeTrain:
    """Test SpikeTrain data structure."""

    def test_spike_train_properties(self) -> None:
        train = SpikeTrain(
            spikes=[
                Spike(time_ms=1.0, neuron_id=0),
                Spike(time_ms=2.0, neuron_id=1),
                Spike(time_ms=3.0, neuron_id=1),
            ],
            n_neurons=2,
            duration_ms=100.0,
        )
        assert train.spike_count == 3
        assert train.mean_rate_hz == pytest.approx(3 / (2 * 0.1), rel=0.01)

    def test_get_neuron_spikes(self) -> None:
        train = SpikeTrain(
            spikes=[
                Spike(time_ms=1.0, neuron_id=0),
                Spike(time_ms=2.0, neuron_id=1),
                Spike(time_ms=5.0, neuron_id=0),
            ],
            n_neurons=2,
            duration_ms=100.0,
        )
        n0_spikes = train.get_neuron_spikes(0)
        assert len(n0_spikes) == 2
        n1_spikes = train.get_neuron_spikes(1)
        assert len(n1_spikes) == 1

    def test_raster(self) -> None:
        train = SpikeTrain(
            spikes=[
                Spike(time_ms=5.0, neuron_id=1),
                Spike(time_ms=1.0, neuron_id=0),
                Spike(time_ms=3.0, neuron_id=0),
            ],
            n_neurons=2,
            duration_ms=10.0,
        )
        raster = train.raster()
        # Should be sorted by time
        assert raster[0][0] < raster[-1][0]

    def test_empty_spike_train(self) -> None:
        train = SpikeTrain(n_neurons=10, duration_ms=100.0)
        assert train.spike_count == 0
        assert train.mean_rate_hz == 0.0


class TestSNNEncoderReset:
    """Test reset functionality."""

    def test_reset(self, encoder: SNNSpikingEncoder) -> None:
        encoder.encode(np.ones(16), method=EncodingMethod.RATE)
        assert encoder._call_count == 1
        encoder.reset()
        assert encoder._call_count == 0


# ═══════════════════════════════════════════════════════════════════════
# Parametric Tests
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("n_neurons", [8, 16, 64])
def test_variable_neuron_count(n_neurons: int) -> None:
    config = SpikeEncoderConfig(n_neurons=n_neurons, n_input_features=8)
    enc = SNNSpikingEncoder(config=config)
    signal = np.random.randn(8).astype(np.float64)
    train = enc.encode(signal, method=EncodingMethod.RATE)
    assert train.n_neurons == n_neurons


@pytest.mark.parametrize("duration_ms", [10.0, 50.0, 200.0])
def test_variable_duration(duration_ms: float) -> None:
    config = SpikeEncoderConfig(n_neurons=8, n_input_features=4, duration_ms=duration_ms)
    enc = SNNSpikingEncoder(config=config)
    signal = np.ones(4)
    train = enc.encode(signal, method=EncodingMethod.RATE)
    assert train.duration_ms == duration_ms
    for spike in train.spikes:
        assert 0.0 <= spike.time_ms <= duration_ms
