"""Digital Twin Engine — 主动数字孪生引擎.

Biological Metaphor:
  The brain's "body schema" — continuously updated internal representation of
  the body's position and state in space. You don't need to look at your hand
  to know where it is; the brain maintains a real-time digital twin of the body.

  Active Digital Twin (ADT) extends this:
    - Not just a passive mirror — it actively REASONS about the future
    - "If I don't intervene now, the system will fail in T minutes"
    - Uses Active Inference to evaluate interventions before executing them

Key Innovation (v4.0):
  Real-time physical-to-digital synchronization. What-If counterfactual
  simulation using the generative model. Anomaly detection via predictive
  distribution tail probability. Intervention recommendation through
  expected free energy minimization over the forward horizon. Generalized
  structural health monitoring applicable to any "structure" — bridges,
  buildings, organizations, financial systems, software systems.

References:
  - Active Digital Twin (PoliMi 2025-2026): POMDP + Active Inference
  - Torzoni et al. (2025): Structural health monitoring via ADT
  - FEPS (PLOS ONE 2025): Free energy projection simulation
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from src.config import L7WorldModelConfig, get_config
from src.utils.logging import CortexLogger


# ═══════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════


class AnomalySeverity(Enum):
    """Severity levels for detected anomalies."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class PhysicalState:
    """A snapshot of the physical system state."""

    state_id: str
    vector: np.ndarray  # Multi-dimensional state vector
    sensor_readings: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class DigitalState:
    """The digital mirror of the physical state — enriched with predictions."""

    state_id: str
    physical_source_id: str
    mean: np.ndarray  # Estimated state mean
    uncertainty: np.ndarray  # State uncertainty (diagonal covariance)
    predicted_mean: np.ndarray | None = None  # One-step-ahead prediction
    prediction_error: float = 0.0
    free_energy: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def state_norm(self) -> float:
        return float(np.linalg.norm(self.mean))


@dataclass
class PredictedState:
    """A future state predicted by forward simulation."""

    step: int
    state_mean: np.ndarray
    state_uncertainty: np.ndarray
    observation_mean: np.ndarray
    free_energy: float = 0.0
    anomaly_probability: float = 0.0
    timestamp: float = 0.0  # Absolute time if known


@dataclass
class AnomalyReport:
    """Report of detected anomaly in the digital twin."""

    anomaly_id: str
    severity: AnomalySeverity
    description: str
    affected_state_ids: list[str] = field(default_factory=list)
    tail_probability: float = 0.0  # P(actual | predicted)
    sigma_deviation: float = 0.0
    recommended_intervention: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class InterventionPlan:
    """A recommended intervention sequence to restore system health."""

    plan_id: str
    description: str
    actions: list[np.ndarray] = field(default_factory=list)
    predicted_outcome_states: list[PredictedState] = field(default_factory=list)
    expected_free_energy: float = float("inf")
    estimated_success_probability: float = 0.0
    risk_level: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class HealthReport:
    """Structural health report for any monitored system."""

    report_id: str
    overall_health: float  # 0-1, higher = healthier
    anomaly_count: int = 0
    critical_count: int = 0
    warning_count: int = 0
    trend: str = "stable"  # "stable", "deteriorating", "improving", "critical"
    mean_free_energy: float = 0.0
    free_energy_trend: float = 0.0  # Positive = increasing (bad)
    recommendations: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class DTEConfig:
    """Runtime configuration for Digital Twin Engine."""

    state_dim: int = 64
    sync_interval_ms: float = 100.0
    simulation_horizon_steps: int = 100
    anomaly_threshold_sigma: float = 3.0
    min_anomaly_probability: float = 0.01
    max_interventions_per_cycle: int = 5
    health_check_interval_steps: int = 50
    history_window: int = 500

    @classmethod
    def from_l7_config(cls, cfg: L7WorldModelConfig) -> DTEConfig:
        return cls(
            state_dim=cfg.ai_hidden_state_dim,
            sync_interval_ms=cfg.dt_sync_interval_ms,
            simulation_horizon_steps=cfg.dt_simulation_horizon_steps,
            anomaly_threshold_sigma=cfg.dt_anomaly_threshold_sigma,
            min_anomaly_probability=cfg.dt_min_anomaly_probability,
            max_interventions_per_cycle=cfg.dt_max_interventions_per_cycle,
            health_check_interval_steps=cfg.dt_health_check_interval_steps,
        )


# ═══════════════════════════════════════════════════════════════════════
# Core Engine
# ═══════════════════════════════════════════════════════════════════════


class DigitalTwinEngine:
    """Active Digital Twin Engine — real-time mirror + predictive reasoning.

    Core capabilities:
      1. SYNCHRONIZE: Mirror physical system state in real-time
      2. SIMULATE: Forward "what-if" simulation for candidate interventions
      3. DETECT: Anomaly detection via predictive distribution tail probability
      4. RECOMMEND: Active inference-based intervention planning
      5. MONITOR: Generalized structural health assessment
    """

    def __init__(self, config: DTEConfig | None = None) -> None:
        self._config = config or DTEConfig.from_l7_config(get_config().l7)
        self._logger = CortexLogger(module="l7_digital_twin")

        # State tracking
        self._digital_state: DigitalState | None = None
        self._state_history: deque[DigitalState] = deque(maxlen=self._config.history_window)
        self._physical_history: deque[PhysicalState] = deque(maxlen=self._config.history_window)

        # Anomaly tracking
        self._anomalies: list[AnomalyReport] = []
        self._interventions: list[InterventionPlan] = []

        # Transition model: A (learned from sync data)
        sd = self._config.state_dim
        rng = np.random.RandomState(42)
        self._A = rng.randn(sd, sd) * 0.05
        self._observation_model = rng.randn(sd, sd) * 0.05
        self._process_noise = 0.05
        self._observation_noise = 0.1

        # Health monitoring
        self._step_count: int = 0
        self._free_energy_history: deque[float] = deque(maxlen=100)

    # ═══════════════════════════════════════════════════════════════════
    # Synchronization — Physical → Digital Mirroring
    # ═══════════════════════════════════════════════════════════════════

    def synchronize(self, physical_state: PhysicalState) -> DigitalState:
        """Synchronize digital twin with latest physical state.

        Performs Bayesian update: the digital state is refined using the
        new physical measurement, weighted by observation noise.

        Args:
            physical_state: Latest physical system snapshot

        Returns:
            Updated digital state with prediction error
        """
        vec = physical_state.vector
        if len(vec) != self._config.state_dim:
            vec = self._project_to_dim(vec, self._config.state_dim)

        # Predict: one-step-ahead using transition model
        if self._digital_state is not None:
            predicted = self._A @ self._digital_state.mean
        else:
            predicted = np.zeros(self._config.state_dim)

        # Kalman-like update: blend prediction with observation
        # Kalman gain: K = P_pred / (P_pred + R)
        if self._digital_state is not None:
            pred_cov = self._process_noise ** 2
            obs_cov = self._observation_noise ** 2
            kalman_gain = pred_cov / (pred_cov + obs_cov)
        else:
            kalman_gain = 0.5  # Initial: equal trust

        # Update: mean = pred + K * (obs - pred)
        updated_mean = predicted + kalman_gain * (vec - predicted)
        updated_uncertainty = np.full_like(updated_mean, self._observation_noise ** 2 * (1 - kalman_gain))

        # Compute prediction error and free energy
        pred_error = float(np.linalg.norm(vec - predicted))
        free_energy = 0.5 * (pred_error ** 2) / self._observation_noise ** 2

        digital = DigitalState(
            state_id=self._hash_id(f"digital-{physical_state.state_id}"),
            physical_source_id=physical_state.state_id,
            mean=updated_mean,
            uncertainty=updated_uncertainty,
            predicted_mean=predicted,
            prediction_error=round(pred_error, 6),
            free_energy=round(free_energy, 6),
        )

        self._digital_state = digital
        self._state_history.append(digital)
        self._physical_history.append(physical_state)
        self._step_count += 1

        self._logger.info(
            "synchronized",
            state_id=digital.state_id,
            pred_error=round(pred_error, 4),
            free_energy=round(free_energy, 4),
        )

        # Periodic health check
        if self._step_count % self._config.health_check_interval_steps == 0:
            self.structural_health_monitoring()

        return digital

    # ═══════════════════════════════════════════════════════════════════
    # What-If Simulation — Forward Counterfactual Reasoning
    # ═══════════════════════════════════════════════════════════════════

    def simulate_what_if(
        self,
        intervention: np.ndarray | None = None,
        horizon: int | None = None,
        from_state: DigitalState | None = None,
    ) -> list[PredictedState]:
        """Forward simulate: "What if I apply intervention X?"

        Uses the learned transition model to project the system state forward.
        Each step accumulates uncertainty (process noise).

        Args:
            intervention: Optional control action to apply at each step
            horizon: Number of steps to simulate (default from config)
            from_state: Starting state (defaults to current digital state)

        Returns:
            List of predicted states for each forward step
        """
        horizon = horizon or self._config.simulation_horizon_steps
        start = from_state or self._digital_state

        if start is None:
            return []

        current = start.mean.copy()
        uncertainty = start.uncertainty.copy() if start.uncertainty is not None else np.ones_like(current) * 0.1

        predictions: list[PredictedState] = []

        for step in range(horizon):
            # Apply intervention if provided
            if intervention is not None:
                current = current + intervention * (1.0 / (step + 1))

            # Predict next state
            current = self._A @ current
            uncertainty = uncertainty + np.full_like(uncertainty, self._process_noise ** 2)

            # Predict observation
            obs = self._observation_model @ current

            # Anomaly probability: how likely is this state under the model?
            # Very high norm → likely anomaly
            state_norm = float(np.linalg.norm(current))
            # Sigmoid anomaly probability
            anomaly_prob = 1.0 / (1.0 + math.exp(-(state_norm - 3.0)))

            predictions.append(PredictedState(
                step=step + 1,
                state_mean=current.copy(),
                state_uncertainty=uncertainty.copy(),
                observation_mean=obs.copy(),
                anomaly_probability=round(anomaly_prob, 6),
            ))

        return predictions

    # ═══════════════════════════════════════════════════════════════════

    def simulate_multiple_what_ifs(
        self,
        interventions: list[np.ndarray],
        horizon: int | None = None,
    ) -> list[list[PredictedState]]:
        """Simulate multiple intervention scenarios in parallel.

        Args:
            interventions: List of intervention vectors to test
            horizon: Simulation horizon

        Returns:
            List of predicted trajectories, one per intervention
        """
        results: list[list[PredictedState]] = []
        for intervention in interventions:
            trajectory = self.simulate_what_if(intervention, horizon)
            results.append(trajectory)
        return results

    # ═══════════════════════════════════════════════════════════════════
    # Anomaly Detection
    # ═══════════════════════════════════════════════════════════════════

    def detect_anomaly(
        self,
        actual_state: PhysicalState | None = None,
        predicted: list[PredictedState] | None = None,
    ) -> AnomalyReport | None:
        """Detect anomalies by comparing actual state against predictive distribution.

        An anomaly is flagged when:
          P(actual | predicted) < min_anomaly_probability
        i.e., the actual state falls in the tail of the predicted distribution.

        Args:
            actual_state: The actual physical state (defaults to last sync)
            predicted: Forward predictions to compare against

        Returns:
            AnomalyReport if anomaly detected, None otherwise
        """
        if actual_state is None:
            if not self._physical_history:
                return None
            actual_state = self._physical_history[-1]

        if self._digital_state is None:
            return None

        actual = actual_state.vector
        predicted_mean = self._digital_state.predicted_mean
        if predicted_mean is None:
            predicted_mean = self._digital_state.mean

        if len(actual) != len(predicted_mean):
            actual = self._project_to_dim(actual, len(predicted_mean))

        # Compute z-score: how many sigma away from prediction
        deviation = actual - predicted_mean
        sigma = np.std(deviation) if len(deviation) > 1 else float(np.abs(deviation[0]))
        if sigma < 1e-8:
            return None

        z_score = float(np.max(np.abs(deviation))) / sigma

        # Gaussian tail probability
        tail_prob = float(2.0 * (1.0 - _approx_erf(z_score / math.sqrt(2))))

        if tail_prob < self._config.min_anomaly_probability or z_score > self._config.anomaly_threshold_sigma:
            severity = AnomalySeverity.WARNING
            if z_score > self._config.anomaly_threshold_sigma * 1.5:
                severity = AnomalySeverity.CRITICAL
            if z_score > self._config.anomaly_threshold_sigma * 2.0:
                severity = AnomalySeverity.EMERGENCY

            report = AnomalyReport(
                anomaly_id=self._hash_id(f"anomaly-{actual_state.state_id}-{time.time()}"),
                severity=severity,
                description=f"State deviation: {z_score:.2f}σ (p={tail_prob:.6f})",
                affected_state_ids=[actual_state.state_id],
                tail_probability=round(tail_prob, 8),
                sigma_deviation=round(z_score, 4),
                recommended_intervention=self._generate_anomaly_response(severity, z_score),
            )

            self._anomalies.append(report)
            self._logger.warn(
                "anomaly_detected",
                severity=severity.value,
                sigma=round(z_score, 4),
                tail_prob=round(tail_prob, 6),
            )
            return report

        return None

    def _generate_anomaly_response(self, severity: AnomalySeverity, z_score: float) -> str:
        """Generate recommended response based on anomaly severity."""
        if severity == AnomalySeverity.EMERGENCY:
            return "IMMEDIATE_SHUTDOWN: System state deviates catastrophically from predictions"
        elif severity == AnomalySeverity.CRITICAL:
            return "ROLLBACK: Revert to last known safe state and diagnose root cause"
        elif severity == AnomalySeverity.WARNING:
            return "INVESTIGATE: Schedule diagnostic scan, increase monitoring frequency"
        return "LOG: Minor deviation within acceptable bounds"

    # ═══════════════════════════════════════════════════════════════════
    # Intervention Recommendation
    # ═══════════════════════════════════════════════════════════════════

    def recommend_intervention(
        self,
        current_state: DigitalState | None = None,
        goal_state: np.ndarray | None = None,
        num_candidates: int | None = None,
    ) -> InterventionPlan:
        """Recommend intervention to move system from current to goal state.

        Evaluates multiple candidate interventions via forward simulation
        and selects the one with minimum expected free energy.

        Args:
            current_state: Starting state (defaults to digital twin state)
            goal_state: Desired target state vector
            num_candidates: Number of intervention candidates to evaluate

        Returns:
            Best InterventionPlan
        """
        current_state = current_state or self._digital_state
        if current_state is None:
            return InterventionPlan(
                plan_id="no-state",
                description="No current state available",
            )

        # Project goal to state dimension if needed
        if goal_state is not None and len(goal_state) != self._config.state_dim:
            goal_state = self._project_to_dim(goal_state, self._config.state_dim)

        num_candidates = num_candidates or self._config.max_interventions_per_cycle

        # Generate candidate interventions
        candidates: list[tuple[np.ndarray, float]] = []

        for i in range(num_candidates):
            # Generate diverse intervention vectors
            direction = np.random.RandomState(42 + i).randn(self._config.state_dim) * 0.1
            if goal_state is not None:
                direction = (goal_state - current_state.mean) * 0.1 / (i + 1)

            # Simulate forward
            trajectory = self.simulate_what_if(direction, horizon=min(50, self._config.simulation_horizon_steps))

            # Compute expected free energy of this trajectory
            if trajectory:
                final = trajectory[-1]
                if goal_state is not None:
                    goal_error = np.sum((final.state_mean - goal_state) ** 2)
                else:
                    goal_error = float(np.linalg.norm(final.state_mean))

                free_energy = goal_error + final.anomaly_probability * 10.0
            else:
                free_energy = float("inf")

            candidates.append((direction, free_energy))

        # Select best candidate
        if not candidates:
            return InterventionPlan(
                plan_id="no-candidates",
                description="No valid interventions found",
            )

        best_direction, best_energy = min(candidates, key=lambda x: x[1])
        best_trajectory = self.simulate_what_if(best_direction)

        success_prob = 1.0 / (1.0 + math.exp(-best_energy))

        plan = InterventionPlan(
            plan_id=self._hash_id(f"intervention-{time.time()}"),
            description=f"Recommended intervention with E[G]={best_energy:.4f}",
            actions=[best_direction],
            predicted_outcome_states=best_trajectory,
            expected_free_energy=round(best_energy, 4),
            estimated_success_probability=round(float(success_prob), 4),
            risk_level=round(0.1 + 0.9 * float(np.linalg.norm(best_direction)), 4),
        )

        self._interventions.append(plan)
        self._logger.info(
            "intervention_recommended",
            plan_id=plan.plan_id,
            expected_g=round(best_energy, 4),
            success_prob=round(float(success_prob), 4),
        )
        return plan

    # ═══════════════════════════════════════════════════════════════════
    # Structural Health Monitoring
    # ═══════════════════════════════════════════════════════════════════

    def structural_health_monitoring(self) -> HealthReport:
        """Assess overall structural health of the monitored system.

        Generalized from structural engineering (Torzoni et al.) to any
        "structure" — organizations, financial systems, software systems.

        Returns:
            HealthReport with 0-1 health score and trend analysis
        """
        # Compute free energies
        if self._state_history:
            recent_fes = [s.free_energy for s in list(self._state_history)[-50:]]
            mean_fe = sum(recent_fes) / len(recent_fes)
            self._free_energy_history.append(mean_fe)
        else:
            mean_fe = float("inf")
            self._free_energy_history.append(mean_fe)

        # Analyze trend
        fe_list = list(self._free_energy_history)
        if len(fe_list) >= 10:
            x = np.arange(len(fe_list))
            y = np.array(fe_list)
            trend_slope = float(np.polyfit(x, y, 1)[0])
        else:
            trend_slope = 0.0

        # Trend classification
        if trend_slope > 0.01:
            trend = "deteriorating"
        elif trend_slope < -0.01:
            trend = "improving"
        else:
            trend = "stable"

        # Count anomalies by severity
        critical_count = sum(1 for a in self._anomalies if a.severity == AnomalySeverity.CRITICAL)
        warning_count = sum(1 for a in self._anomalies if a.severity == AnomalySeverity.WARNING)

        # Health score: 1.0 (perfect) → 0.0 (critical failure)
        anomaly_penalty = critical_count * 0.15 + warning_count * 0.05
        fe_penalty = min(1.0, mean_fe / 100.0) if mean_fe < float("inf") else 0.5
        health = max(0.0, 1.0 - anomaly_penalty - fe_penalty * 0.3)

        # Generate recommendations
        recommendations: list[str] = []
        if trend == "deteriorating":
            recommendations.append("System health trend is deteriorating — investigate root cause")
        if critical_count > 0:
            recommendations.append(f"{critical_count} critical anomalies require immediate attention")
        if warning_count > 3:
            recommendations.append("High warning count — consider proactive maintenance")
        if health < 0.5:
            recommendations.append("URGENT: System health critically low — activate recovery protocol")

        report = HealthReport(
            report_id=self._hash_id(f"health-{time.time()}"),
            overall_health=round(health, 4),
            anomaly_count=len(self._anomalies),
            critical_count=critical_count,
            warning_count=warning_count,
            trend=trend,
            mean_free_energy=round(mean_fe, 6) if mean_fe < float("inf") else 0.0,
            free_energy_trend=round(float(trend_slope), 6),
            recommendations=recommendations,
        )

        self._logger.info(
            "health_report",
            health=round(health, 4),
            trend=trend,
            criticals=critical_count,
            recommendations=len(recommendations),
        )
        return report

    # ═══════════════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════════════

    def get_current_state(self) -> DigitalState | None:
        """Get the current digital twin state."""
        return self._digital_state

    def get_anomalies(self, severity: AnomalySeverity | None = None) -> list[AnomalyReport]:
        """Get detected anomalies, optionally filtered by severity."""
        if severity:
            return [a for a in self._anomalies if a.severity == severity]
        return list(self._anomalies)

    @staticmethod
    def _hash_id(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _project_to_dim(vec: np.ndarray, target_dim: int) -> np.ndarray:
        """Project vector to target dimension."""
        if len(vec) == target_dim:
            return vec
        if len(vec) > target_dim:
            return vec[:target_dim]
        padded = np.zeros(target_dim)
        padded[:len(vec)] = vec
        return padded

    @property
    def stats(self) -> dict[str, Any]:
        """Current engine statistics."""
        return {
            "step_count": self._step_count,
            "state_history_size": len(self._state_history),
            "anomaly_count": len(self._anomalies),
            "intervention_count": len(self._interventions),
            "current_free_energy": round(self._digital_state.free_energy, 6) if self._digital_state else 0.0,
            "prediction_error": round(self._digital_state.prediction_error, 6) if self._digital_state else 0.0,
        }

    def reset(self) -> None:
        """Reset all internal state (for testing)."""
        self._digital_state = None
        self._state_history.clear()
        self._physical_history.clear()
        self._anomalies.clear()
        self._interventions.clear()
        self._free_energy_history.clear()
        self._step_count = 0
        self._logger.debug("dte_reset")


# ═══════════════════════════════════════════════════════════════════════
# Helper: Approximate Error Function
# ═══════════════════════════════════════════════════════════════════════


def _approx_erf(x: float) -> float:
    """Approximate the error function erf(x)."""
    # Abramowitz & Stegun 7.1.26 approximation
    sign = 1.0 if x >= 0 else -1.0
    x = abs(x)
    t = 1.0 / (1.0 + 0.3275911 * x)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * math.exp(-x * x)
    return sign * y
