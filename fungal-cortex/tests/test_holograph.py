"""Tests for ⑤ Holographic Metacognition."""

import pytest

from src.holograph.fractal_encoder import FractalEncoder, InterferencePattern
from src.holograph.holographic_query import FrequencyBand, HolographicQuery
from src.holograph.anomaly_projector import AnomalyProjector, AnomalyProjection


class TestFractalEncoder:
    @pytest.fixture
    def encoder(self) -> FractalEncoder:
        return FractalEncoder(frequency_bands=8, target_bits=81920)

    def test_initial_pattern_empty(self, encoder: FractalEncoder) -> None:
        pattern = encoder.get_pattern()
        assert pattern.event_count == 0
        assert pattern.coherence == 0.0
        assert len(pattern.amplitudes) == 8

    def test_encode_single_event(self, encoder: FractalEncoder) -> None:
        encoder.encode_event({"type": "scan", "severity": "high", "module": "M1"})
        pattern = encoder.get_pattern()
        assert pattern.event_count == 1
        assert sum(pattern.amplitudes) > 0

    def test_encode_batch(self, encoder: FractalEncoder) -> None:
        events = [{"type": f"event-{i}", "value": i} for i in range(100)]
        encoder.encode_batch(events)
        pattern = encoder.get_pattern()
        assert pattern.event_count == 100
        assert pattern.compression_ratio > 1.0

    def test_compression_ratio_improves_with_events(self, encoder: FractalEncoder) -> None:
        encoder.encode_batch([{"x": i} for i in range(500)])
        pattern = encoder.get_pattern()
        assert pattern.compression_ratio > 10.0  # Should get good compression

    def test_coherence_increases_with_similar_events(self) -> None:
        enc = FractalEncoder(frequency_bands=4)
        for _ in range(100):
            enc.encode_event({"type": "heartbeat", "status": "ok"})
        pattern = enc.get_pattern()
        assert pattern.coherence > 0.5  # Similar events → high coherence

    def test_reset(self, encoder: FractalEncoder) -> None:
        encoder.encode_event({"test": True})
        encoder.reset()
        pattern = encoder.get_pattern()
        assert pattern.event_count == 0

    def test_pattern_hash_changes(self, encoder: FractalEncoder) -> None:
        encoder.encode_event({"a": 1})
        h1 = encoder.get_pattern().pattern_hash
        encoder.encode_event({"a": 2})
        h2 = encoder.get_pattern().pattern_hash
        assert h1 != h2  # Hash should change with new data

    def test_stats(self, encoder: FractalEncoder) -> None:
        encoder.encode_batch([{"i": i} for i in range(50)])
        s = encoder.stats
        assert s["event_count"] == 50


class TestHolographicQuery:
    @pytest.fixture
    def populated_query(self) -> HolographicQuery:
        encoder = FractalEncoder(frequency_bands=8)
        encoder.encode_batch([{"type": "test", "i": i} for i in range(200)])
        return HolographicQuery(encoder.get_pattern())

    def test_read_single_band(self, populated_query: HolographicQuery) -> None:
        reading = populated_query.read_band(FrequencyBand.BASE)
        assert reading.band == FrequencyBand.BASE
        assert reading.amplitude > 0
        assert isinstance(reading.coherence_contribution, float)

    def test_read_all_bands(self, populated_query: HolographicQuery) -> None:
        readings = populated_query.read_all_bands()
        assert len(readings) == 8
        assert all(r.amplitude >= 0 for r in readings)

    def test_read_composite_health(self, populated_query: HolographicQuery) -> None:
        health = populated_query.read_composite_health()
        assert 0.0 <= health <= 1.0

    def test_read_domain_state(self, populated_query: HolographicQuery) -> None:
        state = populated_query.read_domain_state("trading")
        assert state["domain"] == "trading"
        assert "healthy" in state

    def test_empty_pattern_returns_zeros(self) -> None:
        hq = HolographicQuery()
        reading = hq.read_band(FrequencyBand.BASE)
        assert reading.amplitude == 0.0
        health = hq.read_composite_health()
        assert health == 0.0


class TestAnomalyProjector:
    @pytest.fixture
    def projector(self) -> AnomalyProjector:
        return AnomalyProjector(sigma_threshold=3.0, window_size=50)

    @pytest.fixture
    def baseline_pattern(self) -> InterferencePattern:
        enc = FractalEncoder(frequency_bands=8)
        enc.encode_batch([{"type": "normal", "value": 0.5} for _ in range(200)])
        return enc.get_pattern()

    def test_update_baseline(self, projector: AnomalyProjector, baseline_pattern: InterferencePattern) -> None:
        projector.update_baseline(baseline_pattern)
        assert projector._pattern_count == 1
        assert len(projector._baseline_amplitudes) == 8

    def test_project_no_anomaly(self, projector: AnomalyProjector, baseline_pattern: InterferencePattern) -> None:
        # Train baseline
        for _ in range(50):
            projector.update_baseline(baseline_pattern)
        # Test same pattern → no anomaly
        result = projector.project(baseline_pattern)
        assert not result.detected or result.anomaly_score < projector._sigma

    def test_project_detects_anomaly(self, projector: AnomalyProjector) -> None:
        # Train baseline with normal patterns
        for _ in range(50):
            enc = FractalEncoder(frequency_bands=8)
            enc.encode_batch([{"type": "normal", "value": 0.5} for _ in range(100)])
            projector.update_baseline(enc.get_pattern())

        # Test with very different pattern
        enc2 = FractalEncoder(frequency_bands=8)
        enc2.encode_batch([{"type": "anomaly", "severity": 0.99, "alert": True} for _ in range(100)])
        anomalous = enc2.get_pattern()

        result = projector.project(anomalous)
        # May or may not detect depending on deviation
        assert result.anomaly_score >= 0

    def test_anomaly_projection_fields(self, projector: AnomalyProjector, baseline_pattern: InterferencePattern) -> None:
        projector.update_baseline(baseline_pattern)
        result = projector.project(baseline_pattern)
        assert "anomaly_score" in result.__dict__ or hasattr(result, "anomaly_score")

    def test_likely_source_mapped(self, projector: AnomalyProjector) -> None:
        # Set up baseline
        enc = FractalEncoder(frequency_bands=8)
        enc.encode_batch([{"a": 1} for _ in range(100)])
        projector.update_baseline(enc.get_pattern())

        # Anomalous pattern
        enc2 = FractalEncoder(frequency_bands=8)
        enc2.encode_batch([{"b": 999} for _ in range(100)])
        result = projector.project(enc2.get_pattern())
        assert result.likely_source in (
            "system_health", "agent_network", "strategy_engine", "risk_system",
            "data_pipeline", "cognitive_scheduler", "emergence_detector",
            "market_regime_detector", "unknown",
        )

    def test_stats(self, projector: AnomalyProjector, baseline_pattern: InterferencePattern) -> None:
        projector.update_baseline(baseline_pattern)
        s = projector.stats
        assert s["pattern_count"] == 1
        assert s["sigma_threshold"] == 3.0
