"""Tests for PrometheusExporter — metrics collection and export.

Covers all metric types (counter, gauge, histogram), Prometheus exposition format,
system/L6 metric collectors, HTTP server start/stop, and edge cases.
"""

from __future__ import annotations

import pytest

from src.monitoring.prometheus_exporter import MetricSample, MetricType, PrometheusExporter


@pytest.fixture
def exporter() -> PrometheusExporter:
    return PrometheusExporter(port=9090, collect_interval=15)


class TestMetricSample:
    """Unit tests for the MetricSample dataclass and its Prometheus line format."""

    def test_to_prometheus_line_no_labels(self) -> None:
        sample = MetricSample(
            name="test_metric",
            value=42.0,
            metric_type=MetricType.COUNTER,
            timestamp=1000000.0,
        )
        line = sample.to_prometheus_line()
        assert line == "test_metric 42.0 1000000000"

    def test_to_prometheus_line_with_labels(self) -> None:
        sample = MetricSample(
            name="test_metric",
            value=1.5,
            metric_type=MetricType.GAUGE,
            labels={"layer": "l0", "type": "alpha"},
            timestamp=2000000.0,
        )
        line = sample.to_prometheus_line()
        # Label order is dict insertion order in Python 3.7+
        assert 'test_metric{layer="l0", type="alpha"} 1.5 2000000000' == line

    def test_to_prometheus_line_empty_labels(self) -> None:
        sample = MetricSample(
            name="empty_labels",
            value=0.0,
            metric_type=MetricType.COUNTER,
            labels={},
            timestamp=0.0,
        )
        line = sample.to_prometheus_line()
        assert line == "empty_labels 0.0 0"

    def test_to_prometheus_line_zero_timestamp(self) -> None:
        sample = MetricSample(
            name="zero_ts",
            value=10.0,
            metric_type=MetricType.GAUGE,
            timestamp=1.5,
        )
        line = sample.to_prometheus_line()
        # int(1.5 * 1000) = 1500
        assert line == "zero_ts 10.0 1500"


class TestPrometheusExporterInit:
    """Tests for exporter initialization and configuration."""

    def test_default_port(self) -> None:
        exporter = PrometheusExporter()
        assert exporter.stats["port"] == 9090

    def test_custom_port(self) -> None:
        exporter = PrometheusExporter(port=9999)
        assert exporter.stats["port"] == 9999

    def test_custom_collect_interval(self) -> None:
        exporter = PrometheusExporter(collect_interval=30)
        assert exporter.stats["collect_interval"] == 30

    def test_initial_stats(self, exporter: PrometheusExporter) -> None:
        stats = exporter.stats
        assert stats == {
            "total_metrics": 0,
            "total_histograms": 0,
            "total_exports": 0,
            "port": 9090,
            "collect_interval": 15,
        }


class TestPrometheusExporterCounters:
    """Tests for record_counter behavior."""

    def test_record_counter(self, exporter: PrometheusExporter) -> None:
        exporter.record_counter("pipeline_ticks", 1.0)
        metric = exporter.get_metric("pipeline_ticks")
        assert metric is not None
        assert metric.value == 1.0
        assert metric.metric_type == MetricType.COUNTER
        assert metric.help_text == "Counter: pipeline_ticks"

    def test_record_counter_increments(self, exporter: PrometheusExporter) -> None:
        exporter.record_counter("pipeline_ticks", 1.0)
        exporter.record_counter("pipeline_ticks", 2.0)
        metric = exporter.get_metric("pipeline_ticks")
        assert metric is not None
        assert metric.value == 3.0

    def test_record_counter_default_value(self, exporter: PrometheusExporter) -> None:
        exporter.record_counter("default_inc")
        metric = exporter.get_metric("default_inc")
        assert metric is not None
        assert metric.value == 1.0

    def test_record_counter_with_labels(self, exporter: PrometheusExporter) -> None:
        exporter.record_counter("layer_ops", 1.0, {"layer": "l0"})
        exporter.record_counter("layer_ops", 2.0, {"layer": "l1"})
        # Each label combination has its own counter value in _counters
        assert exporter._counters["layer_ops{layer=l0}"] == 1.0
        assert exporter._counters["layer_ops{layer=l1}"] == 2.0

    def test_record_counter_negative_value(self, exporter: PrometheusExporter) -> None:
        """Counters accept negative values (accumulation still works)."""
        exporter.record_counter("errors", 5.0)
        exporter.record_counter("errors", -2.0)
        metric = exporter.get_metric("errors")
        assert metric is not None
        assert metric.value == 3.0


class TestPrometheusExporterGauges:
    """Tests for record_gauge behavior."""

    def test_record_gauge(self, exporter: PrometheusExporter) -> None:
        exporter.record_gauge("agents_active", 10.0)
        metric = exporter.get_metric("agents_active")
        assert metric is not None
        assert metric.value == 10.0
        assert metric.metric_type == MetricType.GAUGE
        assert metric.help_text == "Gauge: agents_active"

    def test_record_gauge_overwrites(self, exporter: PrometheusExporter) -> None:
        exporter.record_gauge("agents_active", 10.0)
        exporter.record_gauge("agents_active", 25.0)
        metric = exporter.get_metric("agents_active")
        assert metric is not None
        assert metric.value == 25.0

    def test_record_gauge_zero_value(self, exporter: PrometheusExporter) -> None:
        exporter.record_gauge("temperature", 0.0)
        metric = exporter.get_metric("temperature")
        assert metric is not None
        assert metric.value == 0.0

    def test_record_gauge_with_labels(self, exporter: PrometheusExporter) -> None:
        exporter.record_gauge("memory_mb", 512.0, {"host": "worker-1"})
        metric = exporter.get_metric("memory_mb")
        assert metric is not None
        assert metric.labels == {"host": "worker-1"}


class TestPrometheusExporterHistograms:
    """Tests for record_histogram behavior."""

    def test_record_histogram(self, exporter: PrometheusExporter) -> None:
        exporter.record_histogram("request_latency", 0.5)
        assert "request_latency" in exporter._histogram_buckets
        assert exporter._histogram_buckets["request_latency"] == [0.5]

    def test_record_histogram_multiple_values(self, exporter: PrometheusExporter) -> None:
        for v in [0.1, 0.2, 0.3]:
            exporter.record_histogram("latency", v)
        assert exporter._histogram_buckets["latency"] == [0.1, 0.2, 0.3]

    def test_record_histogram_with_labels(self, exporter: PrometheusExporter) -> None:
        exporter.record_histogram("latency_ms", 100.0, {"endpoint": "/metrics"})
        key = "latency_ms{endpoint=/metrics}"
        assert key in exporter._histogram_buckets

    def test_record_histogram_label_isolation(self, exporter: PrometheusExporter) -> None:
        """Different label combos should produce separate histogram buckets."""
        exporter.record_histogram("lat", 1.0, {"env": "a"})
        exporter.record_histogram("lat", 10.0, {"env": "b"})
        assert exporter._histogram_buckets["lat{env=a}"] == [1.0]
        assert exporter._histogram_buckets["lat{env=b}"] == [10.0]

    def test_record_histogram_trims_to_500_on_excess(self, exporter: PrometheusExporter) -> None:
        """When histogram exceeds 1000 entries, keeps the last 500."""
        # The trim logic: when len > 1000, keep [-500:]
        # 1000 entries: no trim; 1001: trim to 500; then fill to 1000 again
        # At 1502: trim to 500 again
        for i in range(1502):
            exporter.record_histogram("big_hist", float(i))
        assert len(exporter._histogram_buckets["big_hist"]) == 500
        # The last 500 values should be kept
        assert exporter._histogram_buckets["big_hist"][0] == 1002.0
        assert exporter._histogram_buckets["big_hist"][-1] == 1501.0

    def test_record_histogram_single_value(self, exporter: PrometheusExporter) -> None:
        exporter.record_histogram("single", 99.0)
        assert len(exporter._histogram_buckets["single"]) == 1


class TestPrometheusExporterExport:
    """Tests for export_metrics Prometheus text format output."""

    def test_export_metrics_empty(self, exporter: PrometheusExporter) -> None:
        output = exporter.export_metrics()
        assert output.endswith("\n")
        assert "exporter_scrape_count" in output
        # One metric line (+ trailing newline) for the scrape count
        assert output.count("\n") == 1

    def test_export_metrics_counter(self, exporter: PrometheusExporter) -> None:
        exporter.record_counter("requests_total", 42.0)
        output = exporter.export_metrics()
        assert "# HELP requests_total Counter: requests_total" in output
        assert "# TYPE requests_total counter" in output
        assert "requests_total 42.0" in output

    def test_export_metrics_gauge(self, exporter: PrometheusExporter) -> None:
        exporter.record_gauge("temperature", 98.6)
        output = exporter.export_metrics()
        assert "# HELP temperature Gauge: temperature" in output
        assert "# TYPE temperature gauge" in output
        assert "temperature 98.6" in output

    def test_export_metrics_histogram(self, exporter: PrometheusExporter) -> None:
        """Histogram export should include HELP, TYPE, avg, count, p50, p99."""
        for v in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
            exporter.record_histogram("response_time", float(v))
        output = exporter.export_metrics()
        assert "# HELP response_time Histogram: response_time" in output
        assert "# TYPE response_time histogram" in output
        assert "response_time_avg" in output
        assert "response_time_count 10" in output
        assert "response_time_p50" in output
        assert "response_time_p99" in output

    def test_export_metrics_histogram_with_labels(self, exporter: PrometheusExporter) -> None:
        """Histogram with labels should export under the base name."""
        exporter.record_histogram("latency", 0.5, {"endpoint": "/api"})
        output = exporter.export_metrics()
        assert "# HELP latency Histogram: latency" in output
        assert "# TYPE latency histogram" in output
        assert "latency_avg" in output

    def test_export_metrics_multiple_types(self, exporter: PrometheusExporter) -> None:
        """Export should include all metric types."""
        exporter.record_counter("ops", 5.0)
        exporter.record_gauge("temp", 36.6)
        exporter.record_histogram("resp", 0.1)
        output = exporter.export_metrics()
        assert "ops" in output
        assert "temp" in output
        assert "resp" in output

    def test_export_metrics_increments_count(self, exporter: PrometheusExporter) -> None:
        assert exporter.stats["total_exports"] == 0
        exporter.export_metrics()
        assert exporter.stats["total_exports"] == 1
        exporter.export_metrics()
        assert exporter.stats["total_exports"] == 2

    def test_export_metrics_scrape_count_in_output(self, exporter: PrometheusExporter) -> None:
        """The exporter_scrape_count in output should match total_exports."""
        exporter.export_metrics()
        output = exporter.export_metrics()
        assert "exporter_scrape_count 2" in output

    def test_export_metrics_counter_with_labels(self, exporter: PrometheusExporter) -> None:
        exporter.record_counter("db_queries", 10.0, {"db": "main", "status": "ok"})
        output = exporter.export_metrics()
        assert '# HELP db_queries' in output
        assert '# TYPE db_queries counter' in output
        # Labels appear in Prometheus exposition format
        assert 'db_queries{' in output
        assert '"main"' in output
        assert '"ok"' in output

    def test_export_metrics_same_name_counter_and_histogram(self, exporter: PrometheusExporter) -> None:
        """When same name exists as both counter and histogram, only counter data exports.

        The histogram data lines (avg/count/p50/p99) are skipped because they fall
        inside the ``if name not in exported`` guard in ``export_metrics``.
        """
        exporter.record_counter("latency", 5.0)
        exporter.record_histogram("latency", 0.5)
        output = exporter.export_metrics()
        # Counter HELP/TYPE should appear (exported first from _metrics)
        assert "# TYPE latency counter" in output
        # Histogram HELP/TYPE should NOT appear (name already exported)
        assert "# TYPE latency histogram" not in output
        # Histogram data lines are inside the name-not-in-exported guard, so skipped
        assert "latency_avg" not in output
        assert "latency_count" not in output

    def test_export_metrics_empty_histogram_buckets(self, exporter: PrometheusExporter) -> None:
        """Empty histogram buckets should be skipped during export."""
        exporter._histogram_buckets["empty"] = []
        output = exporter.export_metrics()
        assert "empty" not in output

    def test_export_metrics_histogram_single_value(self, exporter: PrometheusExporter) -> None:
        """Histogram with one value: p50 and p99 equal that value."""
        exporter.record_histogram("single_val", 42.0)
        output = exporter.export_metrics()
        assert "single_val_p50 42.0" in output
        assert "single_val_p99 42.0" in output


class TestPrometheusExporterRender:
    """Tests for the render() alias."""

    def test_render_equals_export_metrics(self, exporter: PrometheusExporter) -> None:
        """render() should produce the same format as export_metrics()."""
        exporter.record_counter("test_metric", 1.0)
        exporter.record_gauge("cpu", 50.0)
        exporter.record_histogram("resp", 0.5)
        render_output = exporter.render()
        # Both produce valid Prometheus exposition format with the same metric data
        assert "test_metric" in render_output
        assert "cpu" in render_output
        assert "resp" in render_output
        assert "HELP" in render_output
        assert "TYPE" in render_output

    def test_render_increments_export_count(self, exporter: PrometheusExporter) -> None:
        """render() should also increment total_exports (it calls export_metrics)."""
        exporter.render()
        assert exporter.stats["total_exports"] == 1
        exporter.render()
        assert exporter.stats["total_exports"] == 2


class TestPrometheusExporterGetMetric:
    """Tests for get_metric retrieval."""

    def test_get_metric_found(self, exporter: PrometheusExporter) -> None:
        exporter.record_gauge("cpu_usage", 45.0)
        metric = exporter.get_metric("cpu_usage")
        assert metric is not None
        assert metric.name == "cpu_usage"
        assert metric.value == 45.0

    def test_get_metric_not_found(self, exporter: PrometheusExporter) -> None:
        assert exporter.get_metric("non_existent") is None

    def test_get_metric_after_counter(self, exporter: PrometheusExporter) -> None:
        exporter.record_counter("events", 5.0)
        metric = exporter.get_metric("events")
        assert metric is not None
        assert metric.help_text == "Counter: events"

    def test_get_metric_after_gauge_overwrite(self, exporter: PrometheusExporter) -> None:
        exporter.record_gauge("value", 1.0)
        exporter.record_gauge("value", 99.0)
        metric = exporter.get_metric("value")
        assert metric is not None
        assert metric.value == 99.0


class TestPrometheusExporterCollectors:
    """Tests for collect_system_metrics and collect_l6_metrics."""

    def test_collect_system_metrics_all_fields(self, exporter: PrometheusExporter) -> None:
        exporter.collect_system_metrics(
            agent_count=10,
            skill_count=50,
            pipeline_throughput=1000.0,
            event_bus_events=500,
            event_bus_dropped=2,
            memory_usage_mb=256.0,
        )
        assert exporter.get_metric("fungal_cortex_agents_total").value == 10.0
        assert exporter.get_metric("fungal_cortex_skills_total").value == 50.0
        assert exporter.get_metric("fungal_cortex_pipeline_throughput").value == 1000.0
        assert exporter.get_metric("fungal_cortex_events_total").value == 500.0
        assert exporter.get_metric("fungal_cortex_events_dropped").value == 2.0
        assert exporter.get_metric("fungal_cortex_memory_mb").value == 256.0

    def test_collect_system_metrics_defaults(self, exporter: PrometheusExporter) -> None:
        """All system metrics should be registered with default values."""
        exporter.collect_system_metrics()
        assert exporter.get_metric("fungal_cortex_agents_total").value == 0.0
        assert exporter.get_metric("fungal_cortex_skills_total").value == 0.0
        assert exporter.get_metric("fungal_cortex_memory_mb").value == 0.0

    def test_collect_l6_metrics_all_fields(self, exporter: PrometheusExporter) -> None:
        exporter.collect_l6_metrics(
            health_score=0.85,
            open_issues=12,
            crystallized_skills=30,
            emergence_events=5,
            refactor_pending=3,
        )
        assert exporter.get_metric("fungal_cortex_l6_health_score").value == 0.85
        assert exporter.get_metric("fungal_cortex_l6_open_issues").value == 12.0
        assert exporter.get_metric("fungal_cortex_l6_crystallized_total").value == 30.0
        assert exporter.get_metric("fungal_cortex_l6_emergence_total").value == 5.0
        assert exporter.get_metric("fungal_cortex_l6_refactor_pending").value == 3.0

    def test_collect_l6_metrics_defaults(self, exporter: PrometheusExporter) -> None:
        """All L6 metrics should be registered with default values."""
        exporter.collect_l6_metrics()
        assert exporter.get_metric("fungal_cortex_l6_health_score").value == 0.0
        assert exporter.get_metric("fungal_cortex_l6_open_issues").value == 0.0

    def test_collect_then_export(self, exporter: PrometheusExporter) -> None:
        """System metrics should appear in export output."""
        exporter.collect_system_metrics(agent_count=5)
        output = exporter.export_metrics()
        assert "fungal_cortex_agents_total" in output

    def test_collect_l6_then_export(self, exporter: PrometheusExporter) -> None:
        """L6 metrics should appear in export output."""
        exporter.collect_l6_metrics(health_score=0.9)
        output = exporter.export_metrics()
        assert "fungal_cortex_l6_health_score" in output


class TestPrometheusExporterHttpServer:
    """Tests for HTTP server start/stop (logging-only methods)."""

    def test_start_http_server(self, exporter: PrometheusExporter) -> None:
        """Starting the HTTP server should not raise."""
        exporter.start_http_server()
        # No-op in current implementation; just verify no exception

    def test_stop_http_server(self, exporter: PrometheusExporter) -> None:
        """Stopping the HTTP server should not raise."""
        exporter.stop_http_server()

    def test_start_then_stop(self, exporter: PrometheusExporter) -> None:
        """Starting then stopping should work."""
        exporter.start_http_server()
        exporter.stop_http_server()


class TestPrometheusExporterStats:
    """Tests for the stats property."""

    def test_stats_after_counter(self, exporter: PrometheusExporter) -> None:
        exporter.record_counter("a", 1.0)
        stats = exporter.stats
        assert stats["total_metrics"] == 1

    def test_stats_after_counter_and_gauge(self, exporter: PrometheusExporter) -> None:
        exporter.record_counter("a", 1.0)
        exporter.record_gauge("b", 2.0)
        stats = exporter.stats
        assert stats["total_metrics"] == 2

    def test_stats_after_histogram(self, exporter: PrometheusExporter) -> None:
        """Histograms are tracked in total_histograms, not total_metrics."""
        exporter.record_histogram("lat", 0.5)
        stats = exporter.stats
        assert stats["total_metrics"] == 0  # histograms not in _metrics
        assert stats["total_histograms"] == 1

    def test_stats_after_export(self, exporter: PrometheusExporter) -> None:
        exporter.export_metrics()
        assert exporter.stats["total_exports"] == 1


class TestPrometheusExporterEdgeCases:
    """Edge case and boundary tests."""

    def test_metric_key_static(self) -> None:
        """_metric_key should generate consistent keys."""
        assert PrometheusExporter._metric_key("test", {}) == "test"
        assert PrometheusExporter._metric_key("test", {"a": "1"}) == "test{a=1}"
        # Labels should be sorted
        assert PrometheusExporter._metric_key("test", {"b": "2", "a": "1"}) == "test{a=1,b=2}"

    def test_record_counter_many_metrics(self, exporter: PrometheusExporter) -> None:
        """Record many unique counters."""
        for i in range(100):
            exporter.record_counter(f"metric_{i}", float(i))
        assert exporter.stats["total_metrics"] == 100

    def test_histogram_with_large_values(self, exporter: PrometheusExporter) -> None:
        """Histogram should handle large values."""
        exporter.record_histogram("large", 1e9)
        output = exporter.export_metrics()
        assert "large_avg 1000000000.0" in output

    def test_counter_accumulates_many_calls(self, exporter: PrometheusExporter) -> None:
        """Counter should accumulate correctly over many calls."""
        for _ in range(1000):
            exporter.record_counter("accum", 0.5)
        metric = exporter.get_metric("accum")
        assert metric is not None
        assert metric.value == 500.0
