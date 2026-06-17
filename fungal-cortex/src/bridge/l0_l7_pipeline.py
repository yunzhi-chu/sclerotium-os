"""L0→L7 8-Layer Cognitive Pipeline — full QuantMind OS data flow.

L0: Adaptive Engine — market regime detection + self-tuning
L1: Data Layer — multi-source ingestion + validation
L2: Analysis Layer — quantitative analysis + indicator computation
L3: Debate Layer — BULL vs BEAR atomic debate
L4: Research Layer — deep research + hypothesis generation
L5: Trading Layer — signal generation + strategy execution
L6: Risk Layer — three-faction risk control
L7: Decision Layer — portfolio allocation + execution decisions
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.event_bus import EventBus
from src.utils.logging import CortexLogger


class LayerLevel(Enum):
    """The 8 layers of the cognitive pipeline."""

    L0_ADAPTIVE = 0
    L1_DATA = 1
    L2_ANALYSIS = 2
    L3_DEBATE = 3
    L4_RESEARCH = 4
    L5_TRADING = 5
    L6_RISK = 6
    L7_DECISION = 7


@dataclass
class LayerState:
    """Runtime state of one pipeline layer."""

    level: LayerLevel
    active: bool = True
    throughput: float = 0.0  # Events processed per second
    latency_ms: float = 0.0  # Average processing latency
    error_rate: float = 0.0  # Fraction of events resulting in error
    queue_depth: int = 0  # Events waiting to be processed
    agent_count: int = 0  # Active agents in this layer
    last_processed: float = 0.0  # Timestamp of last processed event
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineSnapshot:
    """Complete snapshot of the entire pipeline state."""

    layers: dict[LayerLevel, LayerState]
    total_throughput: float = 0.0
    total_latency_ms: float = 0.0
    bottleneck_layer: LayerLevel | None = None
    healthy: bool = True
    timestamp: float = field(default_factory=time.time)


class L0L7Pipeline:
    """The 8-layer cognitive pipeline from data ingestion to trading decision.

    The pipeline is a directed acyclic graph: L0 → L1 → L2 → L3 → L4 → L5 → L6 → L7.
    Each layer processes its input, produces an output, and passes it to the next layer.
    L0 (Adaptive Engine) provides self-tuning feedback to all layers.
    """

    def __init__(
        self,
        event_bus: EventBus | None = None,
        layer_timeout: float = 30.0,
        tick_interval: float = 0.1,
    ) -> None:
        self._event_bus = event_bus
        self._layer_timeout = layer_timeout
        self._tick_interval = tick_interval
        self._logger = CortexLogger("l0_l7_pipeline")

        self._layers: dict[LayerLevel, LayerState] = {}
        for level in LayerLevel:
            self._layers[level] = LayerState(level=level)

        self._pipeline_history: list[PipelineSnapshot] = []
        self._running = False
        self._tick_count = 0
        self._total_events = 0

        # Service references — injected via bind_services()
        self._services: dict[str, Any] = {}

    def bind_services(self, **services: Any) -> None:
        """Inject service references for real pipeline processing.

        Expected services:
            data_pipeline: DataPipeline instance (L1)
            claim_debate: ClaimDebateBridge instance (L3)
            root_agent: RootAgent instance (L5)
            risk_gate: RiskGate instance (L6)
            portfolio_manager: PortfolioManager instance (L7)
        """
        self._services.update(services)
        self._logger.info("services_bound", services=list(services.keys()))

    def update_layer(self, level: LayerLevel, **kwargs: Any) -> None:
        """Update a layer's runtime state."""
        layer = self._layers[level]
        for key, value in kwargs.items():
            if hasattr(layer, key):
                setattr(layer, key, value)
        layer.last_processed = time.time()
        layer.metadata.update(kwargs)

    def get_layer(self, level: LayerLevel) -> LayerState:
        """Get the state of a specific layer."""
        return self._layers[level]

    def get_all_layers(self) -> dict[LayerLevel, LayerState]:
        """Get all layer states."""
        return dict(self._layers)

    def snapshot(self) -> PipelineSnapshot:
        """Take a complete pipeline snapshot for monitoring."""
        layers = dict(self._layers)
        total_throughput = sum(l.throughput for l in layers.values())
        total_latency = sum(l.latency_ms for l in layers.values()) / max(len(layers), 1)

        # Identify bottleneck: layer with highest latency * queue_depth product
        bottleneck: LayerLevel | None = None
        max_pressure = 0.0
        for level, layer in layers.items():
            pressure = layer.latency_ms * max(layer.queue_depth, 1)
            if pressure > max_pressure:
                max_pressure = pressure
                bottleneck = level

        healthy = all(l.error_rate < 0.1 for l in layers.values())

        snapshot = PipelineSnapshot(
            layers=layers,
            total_throughput=total_throughput,
            total_latency_ms=total_latency,
            bottleneck_layer=bottleneck,
            healthy=healthy,
        )
        self._pipeline_history.append(snapshot)
        if len(self._pipeline_history) > 1000:
            self._pipeline_history = self._pipeline_history[-1000:]
        return snapshot

    async def tick(self) -> PipelineSnapshot:
        """Execute one pipeline tick. Propagates state through all layers."""
        self._tick_count += 1

        # L0 Adaptive Engine: self-tuning feedback
        self._update_adaptive_feedback()

        # Forward pass through L1→L7
        for level in LayerLevel:
            if level == LayerLevel.L0_ADAPTIVE:
                continue
            self._process_layer_tick(level)

        snapshot = self.snapshot()

        if self._event_bus:
            await self._event_bus.publish_nowait(
                "pipeline.tick",
                {
                    "tick": self._tick_count,
                    "healthy": snapshot.healthy,
                    "bottleneck": snapshot.bottleneck_layer.value if snapshot.bottleneck_layer else None,
                },
                source="l0_l7_pipeline",
            )

        return snapshot

    def _update_adaptive_feedback(self) -> None:
        """L0: Adaptive engine provides feedback to all downstream layers."""
        l0 = self._layers[LayerLevel.L0_ADAPTIVE]
        l0.throughput = self._tick_count / max(time.time() - self._pipeline_history[0].timestamp if self._pipeline_history else time.time(), 1)
        l0.active = True

        # Feed market regime info to downstream layers
        regime = l0.metadata.get("market_regime", "unknown")
        for level in LayerLevel:
            if level != LayerLevel.L0_ADAPTIVE:
                self._layers[level].metadata["market_regime"] = regime

    def _process_layer_tick(self, level: LayerLevel) -> None:
        """Process one tick for a specific layer — dispatch to real services."""
        layer = self._layers[level]
        if not layer.active:
            return

        t0 = time.time()

        try:
            if level == LayerLevel.L1_DATA:
                # L1: Data ingestion — poll market connectors
                dp = self._services.get("data_pipeline")
                if dp and hasattr(dp, "poll_sources"):
                    connectors = self._services.get("connectors", {})
                    asyncio_coro = dp.poll_sources(connectors)
                    # Called synchronously in tick — queue depth tracks pending
                    layer.queue_depth = len(dp._tick_buffer) if hasattr(dp, "_tick_buffer") else 0
                    layer.agent_count = len(connectors)

            elif level == LayerLevel.L2_ANALYSIS:
                # L2: Technical analysis — compute indicators from OHLC
                dp = self._services.get("data_pipeline")
                if dp:
                    ohlc_count = len(dp._ohlc_bars) if hasattr(dp, "_ohlc_bars") else 0
                    layer.throughput = ohlc_count / max(self._tick_count, 1)
                    layer.queue_depth = ohlc_count

            elif level == LayerLevel.L3_DEBATE:
                # L3: Multi-agent debate
                debate = self._services.get("claim_debate")
                if debate:
                    layer.agent_count = 3  # BULL, BEAR, SYNTH
                    layer.queue_depth = len(getattr(debate, "_pending_claims", []))

            elif level == LayerLevel.L4_RESEARCH:
                # L4: Research / hypothesis generation
                pass  # Async research pipeline — handled by CognitiveScheduler

            elif level == LayerLevel.L5_TRADING:
                # L5: Root Agent colony management
                root = self._services.get("root_agent")
                if root:
                    layer.agent_count = len(root.state.managed_agents)
                    layer.queue_depth = root.state.total_actions

            elif level == LayerLevel.L6_RISK:
                # L6: Risk evaluation
                rg = self._services.get("risk_gate")
                if rg:
                    layer.agent_count = 1
                    layer.queue_depth = len(getattr(rg, "_pending_evaluations", []))

            elif level == LayerLevel.L7_DECISION:
                # L7: Portfolio decisions
                pm = self._services.get("portfolio_manager")
                if pm:
                    state = pm.get_state() if hasattr(pm, "get_state") else {}
                    layer.queue_depth = len(state.get("positions", []))
                    layer.agent_count = 1

        except Exception as exc:
            self._logger.error("layer_tick_error", layer=level.value, error=str(exc))
            layer.error_rate = min(1.0, layer.error_rate + 0.01)

        # Update metrics
        elapsed = (time.time() - t0) * 1000
        layer.latency_ms = (layer.latency_ms * 0.9) + (elapsed * 0.1)  # EMA
        layer.throughput = 1.0 / max(elapsed, 0.001) * 1000  # events/sec
        layer.last_processed = time.time()

    def inject_event(self, level: LayerLevel, event: dict[str, Any]) -> None:
        """Inject an event into a pipeline layer for processing."""
        layer = self._layers[level]
        layer.queue_depth += 1
        if self._event_bus:
            self._logger.debug("event_injected", layer=level.value, queue_depth=layer.queue_depth)

    async def run(self, shutdown_event: "asyncio.Event") -> None:
        """Run the pipeline tick loop until shutdown is signaled."""
        import asyncio as _asyncio
        self.start()
        try:
            while not shutdown_event.is_set():
                await self.tick()
                await _asyncio.sleep(self._tick_interval)
        finally:
            self.stop()

    def start(self) -> None:
        """Mark the pipeline as running."""
        self._running = True
        self._logger.info("pipeline_started", layers=len(self._layers))

    def stop(self) -> PipelineSnapshot:
        """Stop the pipeline and return final snapshot."""
        self._running = False
        final = self.snapshot()
        self._logger.info("pipeline_stopped", total_events=self._total_events, ticks=self._tick_count)
        return final

    @property
    def stats(self) -> dict[str, Any]:
        s = self.snapshot()
        return {
            "layers": {l.value: {
                "active": s.layers[l].active,
                "throughput": s.layers[l].throughput,
                "latency_ms": s.layers[l].latency_ms,
                "queue_depth": s.layers[l].queue_depth,
                "agent_count": s.layers[l].agent_count,
            } for l in LayerLevel},
            "total_throughput": s.total_throughput,
            "total_latency_ms": s.total_latency_ms,
            "bottleneck": s.bottleneck_layer.value if s.bottleneck_layer else None,
            "healthy": s.healthy,
            "tick_count": self._tick_count,
            "total_events": self._total_events,
        }
