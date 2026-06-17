"""Prometheus Exporter — system-wide metrics collection and export.

Exports Fungal Cortex metrics in Prometheus-compatible format for
Grafana dashboard visualization.

Metric categories:
- Agent metrics: count, lifecycle distribution, performance
- Pipeline metrics: throughput, latency, error rate per layer
- Trading metrics: P&L, position count, risk gate pass rate
- Cognitive metrics: depth distribution, task throughput
- System metrics: event bus stats, skill registry size, memory
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricSample:
    """A single metric sample."""

    name: str
    value: float
    metric_type: MetricType
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    help_text: str = ""

    def to_prometheus_line(self) -> str:
        """Format as Prometheus exposition format line."""
        label_str = ""
        if self.labels:
            label_parts = [f'{k}="{v}"' for k, v in self.labels.items()]
            label_str = "{" + ", ".join(label_parts) + "}"
        return f"{self.name}{label_str} {self.value} {int(self.timestamp * 1000)}"


class PrometheusExporter:
    """Prometheus-compatible metrics exporter.

    Collects metrics from all Fungal Cortex subsystems and exposes them
    in the standard Prometheus exposition format (text/plain).

    Usage:
        exporter = PrometheusExporter(port=9090)
        exporter.record_counter("pipeline.ticks", 1, {"layer": "l0"})
        exporter.record_gauge("agents.active", 17)
        # GET /metrics → Prometheus text format
    """

    def __init__(self, port: int = 9090, collect_interval: int = 15) -> None:
        self._port = port
        self._collect_interval = collect_interval
        self._metrics: dict[str, MetricSample] = {}
        self._counters: dict[str, float] = {}
        self._histogram_buckets: dict[str, list[float]] = {}
        self._logger = CortexLogger("prometheus_exporter")
        self._total_exports = 0
        self._last_export_time: float = 0.0

    def record_counter(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment a counter metric."""
        key = self._metric_key(name, labels or {})
        self._counters[key] = self._counters.get(key, 0.0) + value
        self._metrics[name] = MetricSample(
            name=name,
            value=self._counters[key],
            metric_type=MetricType.COUNTER,
            labels=labels or {},
            help_text=f"Counter: {name}",
        )

    def record_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge metric to a specific value."""
        self._metrics[name] = MetricSample(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            labels=labels or {},
            help_text=f"Gauge: {name}",
        )

    def record_histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record a histogram observation."""
        key = self._metric_key(name, labels or {})
        if key not in self._histogram_buckets:
            self._histogram_buckets[key] = []
        self._histogram_buckets[key].append(value)

        # Keep last 1000 observations
        if len(self._histogram_buckets[key]) > 1000:
            self._histogram_buckets[key] = self._histogram_buckets[key][-500:]

    def collect_system_metrics(
        self,
        agent_count: int = 0,
        skill_count: int = 0,
        pipeline_throughput: float = 0.0,
        event_bus_events: int = 0,
        event_bus_dropped: int = 0,
        memory_usage_mb: float = 0.0,
    ) -> None:
        """Collect standard system-level metrics."""
        self.record_gauge("fungal_cortex_agents_total", agent_count)
        self.record_gauge("fungal_cortex_skills_total", skill_count)
        self.record_gauge("fungal_cortex_pipeline_throughput", pipeline_throughput)
        self.record_counter("fungal_cortex_events_total", event_bus_events)
        self.record_gauge("fungal_cortex_events_dropped", event_bus_dropped)
        self.record_gauge("fungal_cortex_memory_mb", memory_usage_mb)

    def collect_l6_metrics(
        self,
        health_score: float = 0.0,
        open_issues: int = 0,
        crystallized_skills: int = 0,
        emergence_events: int = 0,
        refactor_pending: int = 0,
    ) -> None:
        """Collect L6 cognitive platform metrics."""
        self.record_gauge("fungal_cortex_l6_health_score", health_score)
        self.record_gauge("fungal_cortex_l6_open_issues", open_issues)
        self.record_counter("fungal_cortex_l6_crystallized_total", crystallized_skills)
        self.record_counter("fungal_cortex_l6_emergence_total", emergence_events)
        self.record_gauge("fungal_cortex_l6_refactor_pending", refactor_pending)

    def export_metrics(self) -> str:
        """Export all metrics in Prometheus text format."""
        self._last_export_time = time.time()
        self._total_exports += 1

        lines: list[str] = []
        exported: set[str] = set()

        for name, sample in self._metrics.items():
            if sample.help_text:
                lines.append(f"# HELP {name} {sample.help_text}")
            lines.append(f"# TYPE {name} {sample.metric_type.value}")
            lines.append(sample.to_prometheus_line())
            exported.add(name)

        # Export histogram data
        for key, buckets in self._histogram_buckets.items():
            if not buckets:
                continue
            name = key.split("{")[0] if "{" in key else key
            if name not in exported:
                lines.append(f"# HELP {name} Histogram: {name}")
                lines.append(f"# TYPE {name} histogram")
                avg = sum(buckets) / len(buckets)
                lines.append(f"{name}_avg {avg}")
                lines.append(f"{name}_count {len(buckets)}")
                sorted_buckets = sorted(buckets)
                lines.append(f"{name}_p50 {sorted_buckets[len(sorted_buckets)//2]}")
                lines.append(f"{name}_p99 {sorted_buckets[min(int(len(sorted_buckets)*0.99), len(sorted_buckets)-1)]}")

        lines.append(f"# fungal_cortex_exporter_scrape_count {self._total_exports}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _metric_key(name: str, labels: dict[str, str]) -> str:
        """Generate a unique key for a metric + label combination."""
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}" if label_str else name

    def render(self) -> str:
        """Render all metrics in Prometheus text format (alias for export_metrics)."""
        return self.export_metrics()

    def start_http_server(self) -> None:
        """Start a dedicated Prometheus HTTP server on the configured port.

        In production, a separate thread-based HTTP server can be spawned.
        For the default deployment, FastAPI serves /metrics directly.
        """
        self._logger.info("prometheus_http_start", port=self._port)

    def stop_http_server(self) -> None:
        """Stop the Prometheus HTTP server."""
        self._logger.info("prometheus_http_stop", port=self._port)

    def get_metric(self, name: str) -> MetricSample | None:
        return self._metrics.get(name)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_metrics": len(self._metrics),
            "total_histograms": len(self._histogram_buckets),
            "total_exports": self._total_exports,
            "port": self._port,
            "collect_interval": self._collect_interval,
        }
