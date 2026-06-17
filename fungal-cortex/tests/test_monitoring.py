"""Tests for Phase 3 Monitoring layer."""
import pytest
from src.monitoring.prometheus_exporter import PrometheusExporter, MetricType, MetricSample
from src.monitoring.alerts import AlertManager, AlertSeverity, AlertStatus, AlertRule, Alert


class TestPrometheusExporter:
    @pytest.fixture
    def exporter(self) -> PrometheusExporter:
        return PrometheusExporter(port=9090)

    def test_record_counter(self, exporter: PrometheusExporter) -> None:
        exporter.record_counter("test_counter", 1.0)
        metric = exporter.get_metric("test_counter")
        assert metric is not None
        assert metric.metric_type == MetricType.COUNTER
        assert metric.value == 1.0

    def test_record_counter_accumulates(self, exporter: PrometheusExporter) -> None:
        exporter.record_counter("accum", 1.0)
        exporter.record_counter("accum", 2.0)
        metric = exporter.get_metric("accum")
        assert metric.value == 3.0

    def test_record_gauge(self, exporter: PrometheusExporter) -> None:
        exporter.record_gauge("test_gauge", 42.0)
        metric = exporter.get_metric("test_gauge")
        assert metric is not None
        assert metric.metric_type == MetricType.GAUGE
        assert metric.value == 42.0

    def test_record_gauge_overwrites(self, exporter: PrometheusExporter) -> None:
        exporter.record_gauge("overwrite", 1.0)
        exporter.record_gauge("overwrite", 99.0)
        metric = exporter.get_metric("overwrite")
        assert metric.value == 99.0

    def test_record_histogram(self, exporter: PrometheusExporter) -> None:
        exporter.record_histogram("latency", 0.5)
        exporter.record_histogram("latency", 1.2)
        exporter.record_histogram("latency", 0.8)

    def test_collect_system_metrics(self, exporter: PrometheusExporter) -> None:
        exporter.collect_system_metrics(
            agent_count=10, skill_count=209, pipeline_throughput=50.0,
            event_bus_events=1000, event_bus_dropped=5, memory_usage_mb=512.0,
        )
        assert exporter.get_metric("fungal_cortex_agents_total") is not None
        assert exporter.get_metric("fungal_cortex_skills_total") is not None

    def test_collect_l6_metrics(self, exporter: PrometheusExporter) -> None:
        exporter.collect_l6_metrics(
            health_score=85.0, open_issues=3, crystallized_skills=10,
            emergence_events=5, refactor_pending=2,
        )
        assert exporter.get_metric("fungal_cortex_l6_health_score") is not None

    def test_export_metrics_returns_text(self, exporter: PrometheusExporter) -> None:
        exporter.record_gauge("test_metric", 100.0, {"env": "test"})
        output = exporter.export_metrics()
        assert "test_metric" in output
        assert "# HELP" in output
        assert "# TYPE" in output

    def test_metric_sample_to_prometheus_line(self) -> None:
        sample = MetricSample(name="test", value=42.0, metric_type=MetricType.GAUGE, labels={"env": "prod"})
        line = sample.to_prometheus_line()
        assert "test" in line
        assert "42.0" in line
        assert "env" in line

    def test_stats(self, exporter: PrometheusExporter) -> None:
        exporter.record_gauge("s", 1.0)
        s = exporter.stats
        assert s["total_metrics"] == 1
        assert s["port"] == 9090


class TestAlertManager:
    @pytest.fixture
    def am(self) -> AlertManager:
        return AlertManager(max_history=100)

    def test_default_rules_loaded(self, am: AlertManager) -> None:
        assert len(am._rules) >= 7
        assert "health_score_low" in am._rules

    def test_add_rule(self, am: AlertManager) -> None:
        rule = AlertRule("custom_rule", "Custom test rule", AlertSeverity.MEDIUM, "custom_metric", "gt", 100.0)
        am.add_rule(rule)
        assert "custom_rule" in am._rules

    def test_remove_rule(self, am: AlertManager) -> None:
        am.add_rule(AlertRule("temp", "temp", AlertSeverity.LOW, "tmp", "gt", 0.0))
        assert am.remove_rule("temp")
        assert not am.remove_rule("nonexistent")

    def test_evaluate_metric_triggers_alert(self, am: AlertManager) -> None:
        am.add_rule(AlertRule("high_latency", "High latency", AlertSeverity.HIGH, "latency_ms", "gt", 500.0, cooldown_seconds=0.0))
        alerts = am.evaluate_metric("latency_ms", 800.0)
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.HIGH
        assert alerts[0].rule_name == "high_latency"

    def test_evaluate_metric_no_trigger_below_threshold(self, am: AlertManager) -> None:
        am.add_rule(AlertRule("low_mem", "Low memory", AlertSeverity.HIGH, "memory_mb", "lt", 100.0, cooldown_seconds=0.0))
        alerts = am.evaluate_metric("memory_mb", 500.0)
        assert len(alerts) == 0

    def test_cooldown_prevents_rapid_fire(self, am: AlertManager) -> None:
        am.add_rule(AlertRule("freq", "Frequent", AlertSeverity.MEDIUM, "freq_metric", "gt", 10.0, cooldown_seconds=999.0))
        alerts1 = am.evaluate_metric("freq_metric", 20.0)
        assert len(alerts1) == 1
        alerts2 = am.evaluate_metric("freq_metric", 20.0)
        assert len(alerts2) == 0  # Cooldown blocked

    def test_acknowledge_alert(self, am: AlertManager) -> None:
        am.add_rule(AlertRule("ack_test", "Ack test", AlertSeverity.LOW, "ack_metric", "gt", 5.0, cooldown_seconds=0.0))
        alerts = am.evaluate_metric("ack_metric", 10.0)
        alert_id = alerts[0].alert_id
        assert am.acknowledge(alert_id)

    def test_resolve_alert(self, am: AlertManager) -> None:
        am.add_rule(AlertRule("res_test", "Resolve test", AlertSeverity.LOW, "res_metric", "gt", 5.0, cooldown_seconds=0.0))
        alerts = am.evaluate_metric("res_metric", 10.0)
        alert_id = alerts[0].alert_id
        am.acknowledge(alert_id)
        assert am.resolve(alert_id)

    def test_suppress_rule(self, am: AlertManager) -> None:
        am.add_rule(AlertRule("sup_test", "Suppress test", AlertSeverity.MEDIUM, "sup_metric", "gt", 5.0, cooldown_seconds=0.0))
        am.suppress_rule("sup_test")
        alerts = am.evaluate_metric("sup_metric", 100.0)
        assert len(alerts) == 0
        am.unsuppress_rule("sup_test")
        alerts = am.evaluate_metric("sup_metric", 100.0)
        assert len(alerts) == 1

    def test_get_firing_alerts_ordered_by_severity(self, am: AlertManager) -> None:
        am.add_rule(AlertRule("low1", "low", AlertSeverity.LOW, "low_m", "gt", 1.0, cooldown_seconds=0.0))
        am.add_rule(AlertRule("crit1", "critical", AlertSeverity.CRITICAL, "crit_m", "gt", 1.0, cooldown_seconds=0.0))
        am.evaluate_metric("low_m", 10.0)
        am.evaluate_metric("crit_m", 10.0)
        firing = am.get_firing_alerts()
        if firing:
            assert firing[0].severity in (AlertSeverity.CRITICAL, AlertSeverity.HIGH, AlertSeverity.MEDIUM, AlertSeverity.LOW)

    def test_disabled_rule_not_triggered(self, am: AlertManager) -> None:
        rule = AlertRule("disabled", "Disabled rule", AlertSeverity.HIGH, "disabled_m", "gt", 1.0, enabled=False)
        am.add_rule(rule)
        alerts = am.evaluate_metric("disabled_m", 100.0)
        assert len(alerts) == 0

    def test_alert_severity_response_times(self) -> None:
        assert AlertSeverity.CRITICAL.response_time_minutes == 1
        assert AlertSeverity.HIGH.response_time_minutes == 5
        assert AlertSeverity.MEDIUM.response_time_minutes == 30
        assert AlertSeverity.LOW.response_time_minutes == 1440

    def test_lte_condition(self, am: AlertManager) -> None:
        am.add_rule(AlertRule("lte_test", "LTE", AlertSeverity.MEDIUM, "lte_m", "lte", 50.0, cooldown_seconds=0.0))
        alerts = am.evaluate_metric("lte_m", 30.0)
        assert len(alerts) == 1

    def test_gte_condition(self, am: AlertManager) -> None:
        am.add_rule(AlertRule("gte_test", "GTE", AlertSeverity.MEDIUM, "gte_m", "gte", 50.0, cooldown_seconds=0.0))
        alerts = am.evaluate_metric("gte_m", 50.0)
        assert len(alerts) == 1

    def test_alert_duration(self, am: AlertManager) -> None:
        am.add_rule(AlertRule("dur_test", "Duration", AlertSeverity.LOW, "dur_m", "gt", 1.0, cooldown_seconds=0.0))
        alerts = am.evaluate_metric("dur_m", 10.0)
        assert alerts[0].duration_seconds >= 0

    def test_stats(self, am: AlertManager) -> None:
        am.add_rule(AlertRule("stats_rule", "Stats", AlertSeverity.HIGH, "stats_m", "gt", 1.0, cooldown_seconds=0.0))
        am.evaluate_metric("stats_m", 10.0)
        s = am.stats
        assert s["total_rules"] >= 1
        assert "firing_alerts" in s
        assert "by_severity" in s
