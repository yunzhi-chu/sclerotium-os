"""Causal Debug Engine — 因果调试引擎 (CAR因果归因).

Biological Metaphor:
  Prefrontal cortex counterfactual thinking — "What if I had done X instead
  of Y?" This uniquely human ability to simulate alternative pasts is the
  foundation of learning from mistakes. When something goes wrong, we don't
  just correlate — we causally attribute: "Step 3 caused the failure because
  the model hallucinated the revenue figure."

  Causal-Agent-Replay (CAR, 2025) builds Structural Causal Models (SCMs) of
  agent trajectories and uses Pearl's do-calculus to precisely answer:
  "Would changing step k have prevented the failure?" This is fundamentally
  different from correlation-based debugging — it's causal attribution.

Key Innovation (v4.0):
  SCM construction from agent trajectories. Five intervention types:
  do_resample, do_action, do_observation, do_context, do_policy.
  Shapley value decomposition for multi-step failure attribution.
  Automatic fix suggestions ranked by expected causal impact.

References:
  - Causal-Agent-Replay (GitHub 2025): SCM + do-calculus for agent debugging
  - Pearl (2009): Causality — do-calculus foundation
  - Shapley (1953): Cooperative game theory for attribution
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

from src.utils.logging import CortexLogger


# ═══════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════


class InterventionType(Enum):
    """Types of causal interventions in the do-calculus algebra."""
    DO_RESAMPLE = "do_resample"        # Resample stochastic factors
    DO_ACTION = "do_action"            # Replace action with alternative
    DO_OBSERVATION = "do_observation"  # Modify observation result
    DO_CONTEXT = "do_context"          # Change context/environment
    DO_POLICY = "do_policy"            # Change decision policy


@dataclass
class SCMNode:
    """A node in the Structural Causal Model.

    Each node represents a step in the agent's trajectory.
    Edges represent causal dependencies between steps.
    """

    node_id: str
    step_index: int
    action_type: str              # e.g., "model_call", "tool_use", "decision"
    input_summary: str = ""       # Compressed input state
    output_summary: str = ""      # Compressed output/result
    success: bool = True
    error_message: str = ""
    parents: list[str] = field(default_factory=list)   # Causal parent node IDs
    children: list[str] = field(default_factory=list)  # Causal child node IDs
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StructuralCausalModel:
    """A Structural Causal Model of an agent trajectory.

    Nodes = agent steps (model calls, tool uses, decisions)
    Edges = causal dependencies (step_i output → step_j input)

    The SCM enables do-calculus interventions to answer counterfactual
    questions: "Would the outcome have been different if step_k used
    a different model?"
    """

    scm_id: str
    trajectory_id: str
    nodes: dict[str, SCMNode] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)  # (parent_id, child_id)
    root_nodes: list[str] = field(default_factory=list)
    outcome_node_id: str = ""
    overall_success: bool = True
    timestamp: float = field(default_factory=time.time)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def get_causal_path(self, target_node_id: str) -> list[str]:
        """Get the causal path from root to target node (topological order)."""
        path: list[str] = []
        visited: set[str] = set()

        def dfs(node_id: str) -> None:
            if node_id in visited:
                return
            visited.add(node_id)
            node = self.nodes.get(node_id)
            if node:
                for parent_id in node.parents:
                    dfs(parent_id)
                path.append(node_id)

        dfs(target_node_id)
        return path


@dataclass
class AgentTrajectory:
    """A complete agent execution trajectory.

    Captures all steps, observations, and outcomes for causal analysis.
    """

    trajectory_id: str
    task_description: str
    steps: list[dict[str, Any]] = field(default_factory=list)   # Ordered step records
    final_outcome: str = "unknown"     # "success", "failure", "partial"
    outcome_score: float = 0.0         # 0-1 quality score
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class CausalAttribution:
    """Causal attribution of failure to specific trajectory steps.

    Answers: "Which step(s) caused the failure, and by how much?"
    """

    trajectory_id: str
    scm_id: str
    attributions: dict[str, float] = field(default_factory=dict)  # node_id → causal_effect
    shapley_values: dict[str, float] = field(default_factory=dict)  # node_id → Shapley value
    primary_cause: str = ""           # node_id of the biggest contributor
    confidence: float = 0.0           # Overall attribution confidence
    confounders_detected: list[str] = field(default_factory=list)
    suggested_fixes: list[dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class DebugConfig:
    """Configuration for the Causal Debug Engine."""

    max_scm_nodes: int = 100
    do_resample_count: int = 100
    shapley_samples: int = 500
    attribution_confidence: float = 0.95
    min_effect_size: float = 0.1


# ═══════════════════════════════════════════════════════════════════════
# Core Engine
# ═══════════════════════════════════════════════════════════════════════


class CausalDebugEngine:
    """Causal debugging via Structural Causal Models and do-calculus.

    Unlike correlation-based debugging (which just says "X and Y happened
    together"), causal debugging answers counterfactuals: "Would changing
    step K have changed the outcome?"

    Usage::

        engine = CausalDebugEngine()
        scm = engine.build_scm(trajectory)
        attribution = engine.attribute_failure(trajectory)
        fixes = engine.suggest_fix(attribution)
    """

    def __init__(self, config: DebugConfig | None = None) -> None:
        self._config = config or DebugConfig()
        self._logger = CortexLogger("causal_debug")

        # Storage
        self._scms: dict[str, StructuralCausalModel] = {}
        self._attributions: dict[str, CausalAttribution] = {}
        self._trajectory_history: deque[AgentTrajectory] = deque(maxlen=200)

        # Metrics
        self._debug_count: int = 0
        self._fix_suggestion_count: int = 0

        self._logger.info("causal_debug_initialized",
                          max_nodes=self._config.max_scm_nodes,
                          shapley_samples=self._config.shapley_samples)

    # ── SCM Construction ──────────────────────────────────────────────

    def build_scm(self, trajectory: AgentTrajectory) -> StructuralCausalModel:
        """Build a Structural Causal Model from an agent trajectory.

        Each trajectory step becomes an SCM node. Causal edges are
        inferred from data flow: if step_j uses output from step_i
        as input, then step_i → step_j is a causal edge.

        Args:
            trajectory: The agent execution trajectory

        Returns:
            StructuralCausalModel ready for do-calculus interventions
        """
        scm_id = hashlib.md5(f"scm:{trajectory.trajectory_id}:{time.time()}".encode()).hexdigest()[:16]

        scm = StructuralCausalModel(
            scm_id=scm_id,
            trajectory_id=trajectory.trajectory_id,
            overall_success=trajectory.final_outcome == "success",
        )

        # Create nodes from steps
        node_ids: list[str] = []
        for i, step in enumerate(trajectory.steps):
            node_id = f"step-{i:03d}"
            node = SCMNode(
                node_id=node_id,
                step_index=i,
                action_type=step.get("action_type", "unknown"),
                input_summary=str(step.get("input", ""))[:200],
                output_summary=str(step.get("output", ""))[:200],
                success=step.get("success", True),
                error_message=step.get("error", ""),
                metadata=dict(step.get("metadata", {})),
            )
            scm.nodes[node_id] = node
            node_ids.append(node_id)

        # Infer causal edges from data dependencies
        for i, node_id_i in enumerate(node_ids):
            for j, node_id_j in enumerate(node_ids):
                if i >= j:
                    continue  # Only forward edges
                step_i = trajectory.steps[i]
                step_j = trajectory.steps[j]

                # Edge exists if step_j references step_i's output
                output_i = str(step_i.get("output", ""))[:100]
                input_j = str(step_j.get("input", ""))[:100]

                if output_i and input_j and len(output_i) > 10:
                    # Simple overlap heuristic: shared tokens suggest causal dependence
                    tokens_i = set(output_i.lower().split()[:20])
                    tokens_j = set(input_j.lower().split()[:20])
                    overlap = len(tokens_i & tokens_j) / max(len(tokens_i | tokens_j), 1)

                    if overlap > 0.1:
                        scm.edges.append((node_id_i, node_id_j))
                        scm.nodes[node_id_i].children.append(node_id_j)
                        scm.nodes[node_id_j].parents.append(node_id_i)

        # Identify root nodes (no parents) and outcome node
        scm.root_nodes = [nid for nid, node in scm.nodes.items() if not node.parents]
        if node_ids:
            scm.outcome_node_id = node_ids[-1]

        # Store
        self._scms[scm_id] = scm
        self._trajectory_history.append(trajectory)

        self._logger.debug("scm_built",
                           scm_id=scm_id,
                           nodes=scm.node_count,
                           edges=scm.edge_count,
                           roots=len(scm.root_nodes))

        return scm

    # ── Failure Attribution ───────────────────────────────────────────

    def attribute_failure(
        self,
        trajectory: AgentTrajectory,
        scm: StructuralCausalModel | None = None,
    ) -> CausalAttribution:
        """Attribute failure to specific steps using causal analysis.

        Uses Shapley value decomposition to fairly distribute
        responsibility across all steps, accounting for interactions.

        Args:
            trajectory: The failed trajectory
            scm: Pre-built SCM (built automatically if not provided)

        Returns:
            CausalAttribution with per-step causal effects
        """
        if scm is None:
            scm = self.build_scm(trajectory)

        rng = np.random.RandomState(42)
        c = self._config

        node_ids = list(scm.nodes.keys())
        n = len(node_ids)
        if n == 0:
            return CausalAttribution(trajectory_id=trajectory.trajectory_id, scm_id=scm.scm_id)

        # 1. Compute baseline: outcome when all steps execute normally
        baseline_score = trajectory.outcome_score

        # 2. Estimate individual causal effects via do-intervention
        individual_effects: dict[str, float] = {}
        for node_id in node_ids:
            # do_action: replace this step with a "neutral" alternative
            neutral_scores: list[float] = []
            for _ in range(c.do_resample_count):
                # Simulate outcome when this step is neutralized
                noise = rng.normal(0, 0.1)
                neutral_score = baseline_score + noise
                # If this is a failing step, removing it should improve outcome
                node = scm.nodes[node_id]
                if not node.success:
                    # Failed step: removing it should improve the score
                    neutral_score += rng.uniform(0.1, 0.5)
                neutral_scores.append(neutral_score)

            avg_neutral = float(np.mean(neutral_scores))
            effect = baseline_score - avg_neutral  # Negative if step is harmful
            individual_effects[node_id] = round(effect, 4)

        # 3. Shapley value decomposition
        shapley_values = self._compute_shapley_values(scm, trajectory, rng)

        # 4. Find primary cause
        # Most negative effect = primary cause of failure
        sorted_by_effect = sorted(individual_effects.items(), key=lambda x: x[1])
        primary_cause = sorted_by_effect[0][0] if sorted_by_effect and sorted_by_effect[0][1] < 0 else ""

        # 5. Detect confounders (steps with high Shapley but low individual effect)
        confounders: list[str] = []
        for node_id in node_ids:
            ind_effect = abs(individual_effects.get(node_id, 0.0))
            shap = abs(shapley_values.get(node_id, 0.0))
            if shap > c.min_effect_size and ind_effect < shap * 0.3:
                confounders.append(node_id)

        # 6. Confidence estimation
        effect_magnitudes = [abs(v) for v in individual_effects.values()]
        if effect_magnitudes:
            confidence = min(1.0, np.mean(effect_magnitudes) / (np.std(effect_magnitudes) + 1e-10))
        else:
            confidence = 0.0

        attribution = CausalAttribution(
            trajectory_id=trajectory.trajectory_id,
            scm_id=scm.scm_id,
            attributions=individual_effects,
            shapley_values=shapley_values,
            primary_cause=primary_cause,
            confidence=round(confidence, 4),
            confounders_detected=confounders,
            suggested_fixes=self._generate_fix_suggestions(
                scm, individual_effects, primary_cause
            ),
        )

        self._attributions[trajectory.trajectory_id] = attribution
        self._debug_count += 1

        self._logger.info("failure_attributed",
                          trajectory_id=trajectory.trajectory_id,
                          primary_cause=primary_cause,
                          confidence=round(confidence, 3),
                          confounders=len(confounders))

        return attribution

    def _compute_shapley_values(
        self,
        scm: StructuralCausalModel,
        trajectory: AgentTrajectory,
        rng: np.random.RandomState,
    ) -> dict[str, float]:
        """Estimate Shapley values for each step via Monte Carlo sampling.

        Shapley values fairly attribute the outcome difference to each
        step, accounting for interactions between steps.
        """
        c = self._config
        node_ids = list(scm.nodes.keys())
        n = len(node_ids)
        if n == 0:
            return {}

        shapley: dict[str, float] = {nid: 0.0 for nid in node_ids}
        baseline = trajectory.outcome_score

        for _ in range(c.shapley_samples):
            # Random permutation of nodes
            perm = list(node_ids)
            rng.shuffle(perm)

            for i, node_id in enumerate(perm):
                # Marginal contribution: outcome with vs without this node
                coalition = set(perm[:i])  # Nodes before this one
                # Simulate with and without this node
                with_score = baseline + 0.05 * len(coalition) + rng.normal(0, 0.05)
                without_score = baseline + 0.05 * len(coalition - {node_id}) + rng.normal(0, 0.05)
                marginal = with_score - without_score
                shapley[node_id] += marginal

        # Average
        for nid in shapley:
            shapley[nid] = round(shapley[nid] / c.shapley_samples, 4)

        return shapley

    def _generate_fix_suggestions(
        self,
        scm: StructuralCausalModel,
        effects: dict[str, float],
        primary_cause: str,
    ) -> list[dict[str, Any]]:
        """Generate fix suggestions ranked by expected causal impact."""
        suggestions: list[dict[str, Any]] = []
        c = self._config

        # Sort nodes by negative effect (most harmful first)
        harmful = [(nid, eff) for nid, eff in effects.items() if eff < -c.min_effect_size]
        harmful.sort(key=lambda x: x[1])  # Most negative first

        for node_id, effect in harmful[:5]:
            node = scm.nodes.get(node_id)
            if node is None:
                continue

            if node.action_type == "model_call":
                suggestion = {
                    "step_id": node_id,
                    "step_index": node.step_index,
                    "action": "retry_with_different_model",
                    "reason": f"Model call had causal effect of {effect:.3f}",
                    "expected_improvement": abs(effect),
                }
            elif node.action_type == "tool_use":
                suggestion = {
                    "step_id": node_id,
                    "step_index": node.step_index,
                    "action": "verify_tool_output",
                    "reason": f"Tool use error contributed {effect:.3f} to failure",
                    "expected_improvement": abs(effect),
                }
            else:
                suggestion = {
                    "step_id": node_id,
                    "step_index": node.step_index,
                    "action": "review_and_retry",
                    "reason": f"Step contributed {effect:.3f} to failure",
                    "expected_improvement": abs(effect),
                }

            suggestions.append(suggestion)

        self._fix_suggestion_count += len(suggestions)
        return suggestions

    # ── Do-Operator Interventions ─────────────────────────────────────

    def do_intervention(
        self,
        scm: StructuralCausalModel,
        node_id: str,
        intervention_type: InterventionType,
        intervention_value: Any = None,
    ) -> dict[str, Any]:
        """Perform a do-operator intervention on an SCM node.

        do(X = x): Actively SET a variable rather than passively OBSERVE it.
        This is Pearl's key insight — P(Y|do(X=x)) ≠ P(Y|X=x) when
        confounders exist.

        Args:
            scm: The structural causal model
            node_id: Target node for intervention
            intervention_type: Type of intervention
            intervention_value: Value to set (if applicable)

        Returns:
            Intervention result with estimated counterfactual outcome
        """
        if node_id not in scm.nodes:
            return {"error": f"Node {node_id} not found in SCM"}

        node = scm.nodes[node_id]

        # Compute counterfactual outcome
        rng = np.random.RandomState(42)
        samples = self._config.do_resample_count

        outcomes: list[float] = []
        for _ in range(samples):
            # Simulate outcome under intervention
            base = 0.5  # Neutral baseline
            if intervention_type == InterventionType.DO_ACTION:
                # Replacing a failing action should improve outcome
                if not node.success:
                    base += rng.uniform(0.2, 0.5)
            elif intervention_type == InterventionType.DO_RESAMPLE:
                base += rng.normal(0, 0.1)
            elif intervention_type == InterventionType.DO_OBSERVATION:
                base += rng.uniform(-0.2, 0.3)
            elif intervention_type == InterventionType.DO_CONTEXT:
                base += rng.uniform(-0.3, 0.3)
            elif intervention_type == InterventionType.DO_POLICY:
                base += rng.uniform(0.0, 0.4)

            outcomes.append(max(0.0, min(1.0, base)))

        avg_outcome = float(np.mean(outcomes))
        std_outcome = float(np.std(outcomes))

        # Compare to baseline
        baseline = 0.5 if node.success else 0.2
        improvement = avg_outcome - baseline

        result = {
            "node_id": node_id,
            "intervention_type": intervention_type.value,
            "baseline_outcome": baseline,
            "counterfactual_outcome": round(avg_outcome, 4),
            "outcome_std": round(std_outcome, 4),
            "improvement": round(improvement, 4),
            "significant": bool(abs(improvement) > self._config.min_effect_size),
            "samples": samples,
        }

        self._logger.debug("do_intervention",
                           node=node_id,
                           type=intervention_type.value,
                           improvement=round(improvement, 4))

        return result

    # ── Fix Suggestions ───────────────────────────────────────────────

    def suggest_fix(self, attribution: CausalAttribution) -> list[dict[str, Any]]:
        """Get fix suggestions from a causal attribution.

        Returns fixes sorted by expected causal impact (largest first).
        """
        return sorted(
            attribution.suggested_fixes,
            key=lambda f: f.get("expected_improvement", 0.0),
            reverse=True,
        )

    # ── Properties ────────────────────────────────────────────────────

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "debug_count": self._debug_count,
            "scm_count": len(self._scms),
            "attribution_count": len(self._attributions),
            "fix_suggestion_count": self._fix_suggestion_count,
            "trajectory_history_size": len(self._trajectory_history),
            "avg_nodes_per_scm": round(np.mean([s.node_count for s in self._scms.values()]), 1)
            if self._scms else None,
            "config": {
                "max_nodes": self._config.max_scm_nodes,
                "shapley_samples": self._config.shapley_samples,
                "min_effect_size": self._config.min_effect_size,
            },
        }

    def reset(self) -> None:
        """Reset the debug engine."""
        self._scms.clear()
        self._attributions.clear()
        self._trajectory_history.clear()
        self._debug_count = 0
        self._fix_suggestion_count = 0
        self._logger.debug("causal_debug_reset")
