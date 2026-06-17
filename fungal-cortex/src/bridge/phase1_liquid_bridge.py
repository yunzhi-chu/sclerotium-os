"""Phase 1 Liquid Bridge — L1 Perception → L2 Routing integration with existing v3.0.

This bridge is the "spinal cord" connecting the new v4.0 liquid processing layers
to the existing v3.0 adaptive engine. It runs alongside (not replacing) the
existing HMM/CUSUM/HyperNetwork stack, enabling gradual migration.

Architecture:
  Data Source → [v3.0 Path: HMM→CUSUM→HyperNetwork] → L3+ (unchanged)
              → [v4.0 Path: LiquidPerceptor→LiquidTimeConstantNet→MultiModelRouter] → L3+ (enhanced)

The bridge:
  1. Accepts raw data points in any modality
  2. Routes through L1 (liquid perception) → L2 (liquid routing)
  3. Exposes results to the existing pipeline via L0→L7 bridge
  4. Maintains backward compatibility with v3.0 event bus
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Optional

import numpy as np

from src.config import L1Config, L2Config, get_config
from src.l1.liquid_perceptor import (
    DataPoint,
    LiquidPerceptor,
    LiquidPerceptorConfig,
    ModalityType,
    Percept,
)
from src.l1.snn_spiking_encoder import (
    EncodingMethod,
    SNNSpikingEncoder,
    SpikeEncoderConfig,
    SpikeTrain,
)
from src.l2.liquid_time_constant_net import (
    HyperParameters,
    LiquidTimeConstantNet,
    TimeConstantConfig,
)
from src.l2.multi_model_router import (
    ModelProfile,
    MultiModelRouter,
    RouterConfig,
    RoutingDecision,
    create_default_model_pool,
)
from src.utils.logging import CortexLogger


# ═══════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════


class ProcessingPath(Enum):
    """Which processing path was used."""
    V3_LEGACY = "v3_legacy"      # Old HMM/CUSUM/HyperNetwork
    V4_LIQUID = "v4_liquid"      # New LiquidPerceptor/LTN/Router
    HYBRID = "hybrid"             # Both paths fused


@dataclass
class Phase1Result:
    """Complete Phase 1 processing result, ready for downstream consumption."""

    percept: Percept                          # L1 perception output
    hyper_params: HyperParameters             # L2a liquid hyper-parameters
    routing_decision: RoutingDecision | None  # L2b model routing decision
    spike_train: SpikeTrain | None            # L1b SNN encoding (optional)
    processing_path: ProcessingPath = ProcessingPath.V4_LIQUID
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════════════
# Core Bridge
# ═══════════════════════════════════════════════════════════════════════


class Phase1LiquidBridge:
    """Bridge connecting v4.0 liquid layers to the existing v3.0 pipeline.

    This is the primary integration point for Phase 1. It:
      - Runs L1 LiquidPerceptor in parallel with existing HMM/CUSUM
      - Feeds L1 percepts to L2 LiquidTimeConstantNet
      - Optionally routes through MultiModelRouter for LLM tasking
      - Publishes results to the v3.0 EventBus for downstream consumption
      - Supports gradual migration: v3.0 path stays active, v4.0 path enriches

    Usage::

        bridge = Phase1LiquidBridge()
        await bridge.initialize()

        # Process incoming data
        result = await bridge.process(data_point)

        # Access both v3.0 and v4.0 results
        print(result.percept.regime_hint)
        print(result.hyper_params.tau)

        await bridge.shutdown()
    """

    def __init__(
        self,
        l1_config: L1Config | None = None,
        l2_config: L2Config | None = None,
        enable_snn: bool = False,
        enable_routing: bool = True,
    ) -> None:
        self._logger = CortexLogger("phase1_bridge")

        # Load config from global or use defaults
        app_config = get_config()
        l1_cfg = l1_config or app_config.l1
        l2_cfg = l2_config or app_config.l2

        self._enable_snn = enable_snn
        self._enable_routing = enable_routing

        # --- L1: Liquid Perceptor ---
        self._perceptor = LiquidPerceptor(LiquidPerceptorConfig(
            n_hidden=l1_cfg.lnn_n_hidden,
            tau_default=l1_cfg.lnn_tau_default,
            tau_min=l1_cfg.lnn_tau_min,
            tau_max=l1_cfg.lnn_tau_max,
            ode_solver_steps_min=l1_cfg.lnn_solver_steps_min,
            ode_solver_steps_max=l1_cfg.lnn_solver_steps_max,
            surprise_ema_alpha=l1_cfg.lnn_surprise_ema_alpha,
            confidence_ema_alpha=l1_cfg.lnn_confidence_ema_alpha,
            adaptation_threshold=l1_cfg.lnn_adaptation_threshold,
        ))

        # --- L1b: SNN Encoder (optional — neuromorphic path) ---
        self._snn_encoder = SNNSpikingEncoder(SpikeEncoderConfig(
            n_neurons=l1_cfg.snn_n_neurons,
            n_input_features=l1_cfg.lnn_n_hidden,
            duration_ms=l1_cfg.snn_duration_ms,
            rate_max_hz=l1_cfg.snn_rate_max_hz,
            lif_tau_m=l1_cfg.snn_lif_tau_m,
            lif_v_threshold=l1_cfg.snn_lif_v_threshold,
        )) if enable_snn else None

        # --- L2a: Liquid Time Constant Net ---
        self._ltn = LiquidTimeConstantNet(TimeConstantConfig(
            input_dim=l2_cfg.ltn_input_dim,
            hidden_dim=l2_cfg.ltn_hidden_dim,
            n_strategies=l2_cfg.ltn_n_strategies,
            n_indicators=l2_cfg.ltn_n_indicators,
            n_safety_gates=l2_cfg.ltn_n_safety_gates,
            tau_default=l2_cfg.ltn_tau_default,
            alpha_surprise=l2_cfg.ltn_alpha_surprise,
            beta_confidence=l2_cfg.ltn_beta_confidence,
            tau_ema_alpha=l2_cfg.ltn_tau_ema_alpha,
            jit_enabled=l2_cfg.ltn_jit_enabled,
        ))

        # --- L2b: Multi-Model Router ---
        self._router = MultiModelRouter(RouterConfig(
            top_k=l2_cfg.router_top_k,
            quality_weight=l2_cfg.router_quality_weight,
            cost_weight=l2_cfg.router_cost_weight,
            latency_weight=l2_cfg.router_latency_weight,
            reliability_weight=l2_cfg.router_reliability_weight,
            max_cost_per_query_usd=l2_cfg.router_max_cost_per_query,
        )) if enable_routing else None

        # Register default model pool
        if self._router is not None:
            for model in create_default_model_pool():
                self._router.register_model(model)

        # --- State ---
        self._initialized: bool = False
        self._process_count: int = 0
        self._last_result: Phase1Result | None = None

        self._logger.info("phase1_bridge_created",
                          enable_snn=enable_snn,
                          enable_routing=enable_routing,
                          l1_hidden=l1_cfg.lnn_n_hidden,
                          l2_hidden=l2_cfg.ltn_hidden_dim,
                          router_top_k=l2_cfg.router_top_k)

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Initialize the Phase 1 bridge.

        Called during main.py lifespan startup.
        """
        self._initialized = True
        self._logger.info("phase1_bridge_initialized")

        # Attempt JIT compilation for L2 (non-blocking)
        if self._ltn._torch_available:
            loop = asyncio.get_event_loop()
            compiled = await loop.run_in_executor(None, self._ltn.compile_jit)
            if compiled:
                self._logger.info("ltn_jit_compiled")

    async def shutdown(self) -> None:
        """Gracefully shutdown the Phase 1 bridge.

        Called during main.py lifespan shutdown.
        """
        self._initialized = False
        self._logger.info("phase1_bridge_shutdown",
                          total_processed=self._process_count)

    # ── Main Processing Pipeline ──────────────────────────────────────

    async def process(
        self,
        data: DataPoint,
        task_description: str | None = None,
        task_complexity: float = 0.5,
    ) -> Phase1Result:
        """Process a data point through the full L1→L2 liquid pipeline.

        This is the MAIN entry point for Phase 1 integration.

        Args:
            data: Raw multimodal data point
            task_description: Optional task description for model routing
            task_complexity: 0-1 estimate of task difficulty

        Returns:
            Phase1Result with all L1/L2 processing outputs
        """
        t_start = time.time()
        self._process_count += 1

        # Step 1: L1 — Liquid perception
        percept = await self._perceptor.perceive(data)

        # Step 2: L1b — SNN encoding (optional neuromorphic path)
        spike_train = None
        if self._snn_encoder is not None:
            spike_train = self._snn_encoder.encode(
                percept.vector, method=EncodingMethod.RATE,
            )

        # Step 3: L2a — Liquid time constant hyper-parameters
        hyper_params = self._ltn.forward(
            percept.vector,
            surprise=percept.surprise,
            confidence=percept.confidence,
        )

        # Step 4: Feedback — L2 tau → L1 for next processing cycle
        self._perceptor._state.tau = hyper_params.tau

        # Step 5: L2b — Model routing (optional)
        routing_decision = None
        if self._router is not None and task_description is not None:
            routing_decision = self._router.route(
                task_description,
                task_complexity=task_complexity,
            )

        # Step 6: Build result
        latency = (time.time() - t_start) * 1000.0

        result = Phase1Result(
            percept=percept,
            hyper_params=hyper_params,
            routing_decision=routing_decision,
            spike_train=spike_train,
            processing_path=ProcessingPath.V4_LIQUID,
            latency_ms=round(latency, 2),
        )
        self._last_result = result

        self._logger.debug("phase1_processed",
                           modality=data.modality.value,
                           regime=percept.regime_hint,
                           tau=hyper_params.tau,
                           surprise=percept.surprise,
                           latency_ms=round(latency, 2))

        return result

    async def process_batch(
        self,
        batch: list[DataPoint],
        task_description: str | None = None,
    ) -> list[Phase1Result]:
        """Process a batch of data points.

        Each data point is processed sequentially (maintaining ODE continuity).
        """
        results: list[Phase1Result] = []
        for data in batch:
            result = await self.process(data, task_description)
            results.append(result)
        return results

    async def process_stream(
        self,
        stream: AsyncIterator[DataPoint],
    ) -> AsyncIterator[Phase1Result]:
        """Process a continuous stream of data points.

        Like the retina processing a continuous stream of photons.
        """
        async for data_point in stream:
            yield await self.process(data_point)

    # ── Legacy Compatibility ──────────────────────────────────────────

    def to_regime_context(self, result: Phase1Result) -> list[float]:
        """Convert Phase 1 result to v3.0-compatible regime context.

        The v3.0 AdaptiveHyperNetwork expects a 6-dim regime distribution.
        We synthesize this from the L1 percept to maintain backward compatibility.

        Args:
            result: Phase 1 processing result

        Returns:
            6-dim regime distribution suitable for AdaptiveHyperNetwork.forward()
        """
        percept = result.percept.vector
        regime = result.percept.regime_hint

        # Map regime hint to v3.0 distribution format
        # [trending_up, trending_down, high_vol, low_vol, sideways, transition]
        distribution = [0.0] * 6

        if regime == "trending_up":
            distribution[0] = 0.7
            distribution[4] = 0.2
            distribution[5] = 0.1
        elif regime == "trending_down":
            distribution[1] = 0.7
            distribution[4] = 0.2
            distribution[5] = 0.1
        elif regime == "high_volatility":
            distribution[2] = 0.6
            distribution[5] = 0.3
            distribution[4] = 0.1
        elif regime == "calm":
            distribution[3] = 0.7
            distribution[4] = 0.3
        elif regime == "transition":
            distribution[5] = 0.6
            distribution[2] = 0.2
            distribution[4] = 0.2
        else:  # sideways
            distribution[4] = 0.5
            distribution[3] = 0.3
            distribution[5] = 0.2

        return distribution

    def to_strategy_weights(self, result: Phase1Result) -> list[float]:
        """Extract strategy weights from Phase 1 result.

        Compatible with v3.0 StrategyAdapter format.
        """
        return [float(w) for w in result.hyper_params.strategy_weights]

    def to_safety_thresholds(self, result: Phase1Result) -> list[float]:
        """Extract safety thresholds from Phase 1 result.

        Compatible with v3.0 SafetyGateAdapter format.
        """
        return [float(t) for t in result.hyper_params.safety_thresholds]

    # ── Direct Model Registration ─────────────────────────────────────

    def register_model(self, profile: ModelProfile) -> None:
        """Register a custom model in the routing pool."""
        if self._router is not None:
            self._router.register_model(profile)

    def list_registered_models(self) -> list[str]:
        """List all registered model IDs."""
        if self._router is not None:
            return self._router.registered_models
        return []

    # ── SNN Inference (Neuromorphic Path) ─────────────────────────────

    def infer_snn(self, data: np.ndarray) -> np.ndarray:
        """Run inference through the SNN encoder (neuromorphic path).

        This is a fast, low-power inference path for edge deployment.
        """
        if self._snn_encoder is None:
            raise RuntimeError("SNN encoder not enabled (set enable_snn=True)")
        spike_train = self._snn_encoder.encode(data, method=EncodingMethod.RATE)
        return self._snn_encoder.infer(spike_train)

    # ── Properties ────────────────────────────────────────────────────

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def perceptor(self) -> LiquidPerceptor:
        return self._perceptor

    @property
    def ltn(self) -> LiquidTimeConstantNet:
        return self._ltn

    @property
    def router(self) -> MultiModelRouter | None:
        return self._router

    @property
    def stats(self) -> dict[str, Any]:
        """Bridge-level statistics aggregating all Phase 1 components."""
        stats: dict[str, Any] = {
            "initialized": self._initialized,
            "process_count": self._process_count,
            "enable_snn": self._enable_snn,
            "enable_routing": self._enable_routing,
            "l1": self._perceptor.stats,
            "l2_ltn": self._ltn.stats,
        }
        if self._snn_encoder is not None:
            stats["l1_snn"] = self._snn_encoder.stats
        if self._router is not None:
            stats["l2_router"] = self._router.stats
        if self._last_result is not None:
            stats["last_result"] = {
                "regime": self._last_result.percept.regime_hint,
                "tau": self._last_result.hyper_params.tau,
                "latency_ms": self._last_result.latency_ms,
            }
        return stats

    def reset(self) -> None:
        """Reset all Phase 1 components for testing."""
        self._perceptor.reset()
        if self._snn_encoder is not None:
            self._snn_encoder.reset()
        self._ltn.reset()
        if self._router is not None:
            self._router.reset()
        self._process_count = 0
        self._last_result = None
        self._logger.debug("phase1_bridge_reset")
