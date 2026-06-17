"""Tests for metrics module — Prometheus-compatible metrics registry."""

from __future__ import annotations

from src.utils.metrics import MetricSnapshot, MetricsRegistry, get_metrics


class TestMetricSnapshot:
    def test_creation(self):
        snap = MetricSnapshot(name="cpu_usage", value=0.85, labels={"host": "srv1"})
        assert snap.name == "cpu_usage"
        assert snap.value == 0.85
        assert snap.labels == {"host": "srv1"}
        assert snap.timestamp > 0


class TestMetricsRegistry:
    def test_initial_empty(self):
        reg = MetricsRegistry()
        snap = reg.snapshot()
        assert snap["counters"] == {}
        assert snap["gauges"] == {}
        assert snap["histogram_counts"] == {}
        assert "timestamp" in snap

    def test_inc_default_value(self):
        reg = MetricsRegistry()
        reg.inc("requests")
        assert reg.snapshot()["counters"]["requests"] == 1

    def test_inc_explicit_value(self):
        reg = MetricsRegistry()
        reg.inc("bytes", 100)
        assert reg.snapshot()["counters"]["bytes"] == 100

    def test_inc_accumulates(self):
        reg = MetricsRegistry()
        reg.inc("req")
        reg.inc("req", 2)
        reg.inc("req", 3)
        assert reg.snapshot()["counters"]["req"] == 6

    def test_set_gauge(self):
        reg = MetricsRegistry()
        reg.set_gauge("temperature", 36.6)
        assert reg.snapshot()["gauges"]["temperature"] == 36.6

    def test_set_gauge_overwrites(self):
        reg = MetricsRegistry()
        reg.set_gauge("temp", 1.0)
        reg.set_gauge("temp", 2.0)
        assert reg.snapshot()["gauges"]["temp"] == 2.0

    def test_observe_adds_to_histogram(self):
        reg = MetricsRegistry()
        reg.observe("latency", 0.1)
        reg.observe("latency", 0.2)
        reg.observe("latency", 0.3)
        assert reg.snapshot()["histogram_counts"]["latency"] == 3

    def test_observe_multiple_histograms(self):
        reg = MetricsRegistry()
        reg.observe("latency_ms", 5)
        reg.observe("latency_ms", 10)
        reg.observe("response_size", 1024)
        snap = reg.snapshot()
        assert snap["histogram_counts"]["latency_ms"] == 2
        assert snap["histogram_counts"]["response_size"] == 1

    def test_reset_clears_counters_and_gauges(self):
        reg = MetricsRegistry()
        reg.inc("counter1", 5)
        reg.set_gauge("gauge1", 3.14)
        reg.reset()
        snap = reg.snapshot()
        assert snap["counters"] == {}
        assert snap["gauges"] == {}

    def test_multiple_counters_independent(self):
        reg = MetricsRegistry()
        reg.inc("a", 1)
        reg.inc("b", 2)
        reg.inc("c", 3)
        snap = reg.snapshot()
        assert snap["counters"]["a"] == 1
        assert snap["counters"]["b"] == 2
        assert snap["counters"]["c"] == 3


class TestGetMetrics:
    def test_returns_singleton(self):
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2

    def test_singleton_is_registry(self):
        m = get_metrics()
        assert isinstance(m, MetricsRegistry)
