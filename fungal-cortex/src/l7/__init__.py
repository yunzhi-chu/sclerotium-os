"""L7: World Model + Digital Twin Layer (Phase 4 v4.0).

Biological Metaphor:
  Prefrontal cortex + hippocampus — the brain's simulation engine.
  The prefrontal cortex generates "what-if" scenarios (counterfactual simulation)
  while the hippocampus encodes the spatial-temporal world model. Together they
  enable planning, prediction, and intervention — the hallmarks of intelligence.

  Active Inference (Friston): The brain minimizes variational free energy through
  perception (updating beliefs) and action (sampling preferred observations).
  The generative model P(s',o|s,a) is continuously refined through experience.

  Active Digital Twin (PoliMi 2025-2026): Real-time digital mirror of a physical
  system, equipped with Active Inference for predictive reasoning and intervention
  planning. Generalized from structural health monitoring to any complex system.
"""

from src.l7.active_inference_agent import (
    Action,
    ActiveInferenceAgent,
    ActiveInferenceConfig,
    Belief,
    GenerativeModel,
    Observation,
    Policy,
    PolicyType,
    Trajectory,
)
from src.l7.digital_twin_engine import (
    AnomalyReport,
    AnomalySeverity,
    DTEConfig,
    DigitalState,
    DigitalTwinEngine,
    HealthReport,
    InterventionPlan,
    PhysicalState,
    PredictedState,
)

__all__ = [
    # Active Inference Agent
    "ActiveInferenceAgent",
    "ActiveInferenceConfig",
    "GenerativeModel",
    "Belief",
    "Observation",
    "Policy",
    "PolicyType",
    "Action",
    "Trajectory",
    # Digital Twin Engine
    "DigitalTwinEngine",
    "DTEConfig",
    "PhysicalState",
    "DigitalState",
    "PredictedState",
    "AnomalyReport",
    "AnomalySeverity",
    "InterventionPlan",
    "HealthReport",
]
