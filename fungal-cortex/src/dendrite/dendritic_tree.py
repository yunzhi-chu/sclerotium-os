"""Dendritic Tree — fractal branching structure for multi-source signal integration.

Pyramidal neuron dendrites form fractal trees where each branch point is a
nonlinear computation unit. Branching factor (avg 3 children/node) and depth
create exponential input capacity.

Key properties:
- Branching: each node can have multiple children → parallel signal processing
- Supralinear activation: coincident inputs → Ca²⁺ spike (>linear sum)
- bAP probability gate: backward-propagating action potentials open coincidence window
- Spine neck resistance (R_neck): tunable that accelerates EPSP kinetics (3× faster)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DendriticSignal:
    """A signal arriving at a dendritic branch."""

    source: str  # e.g., "strategy_signal", "risk_signal", "market_data"
    amplitude: float  # Signal strength
    arrival_time_ms: float  # Arrival timestamp (ms)
    weight: float = 1.0  # Synaptic weight
    spine_resistance: float = 1.0  # R_neck (normalized): <1=accelerated, >1=attenuated


@dataclass
class DendriticNode:
    """A single node in the dendritic tree — nonlinear coincidence detector."""

    node_id: str
    depth: int  # Distance from soma (root=0)
    spine_resistance: float  # R_neck (1.0=baseline)
    children: list[DendriticNode] = field(default_factory=list)
    signals: list[DendriticSignal] = field(default_factory=list)
    membrane_potential: float = 0.0
    nmda_spike_threshold: float = 0.6
    bap_probability: float = 0.3  # Probability of back-propagating AP


class DendriticTree:
    """Fractal dendritic tree for parallel multi-source signal integration.

    The tree receives signals across its branches, detects coincident arrivals
    (Δt within coincidence window), and integrates them toward the soma.

    Branching rule: each node generates child_count ~ Poisson(branching_factor)
    branches at depth < max_depth.
    """

    def __init__(
        self,
        branching_factor: float = 3.0,
        max_depth: int = 6,
        supralinear_exponent: float = 1.5,
        seed: int | None = None,
    ) -> None:
        self._branching_factor = branching_factor
        self._max_depth = max_depth
        self._supralinear_exp = supralinear_exponent
        self._root = DendriticNode(node_id="soma", depth=0, spine_resistance=1.0)
        self._node_count = 1
        self._grow_tree(self._root)
        if seed is not None:
            random.seed(seed)

    def _grow_tree(self, parent: DendriticNode) -> None:
        """Recursively grow the dendritic tree with fractal branching."""
        if parent.depth >= self._max_depth:
            return

        child_count = max(1, int(random.gauss(self._branching_factor, 0.5)))
        for i in range(child_count):
            child_id = f"{parent.node_id}.b{i}"
            r_neck = max(0.1, random.gauss(1.0, 0.3))  # Tunable spine resistance
            child = DendriticNode(
                node_id=child_id,
                depth=parent.depth + 1,
                spine_resistance=r_neck,
            )
            parent.children.append(child)
            self._node_count += 1
            self._grow_tree(child)

    def inject_signal(self, signal: DendriticSignal, target_node_id: str | None = None) -> None:
        """Inject a signal at a specific node (or broadcast to leaves if None)."""
        if target_node_id:
            node = self._find_node(target_node_id)
            if node:
                node.signals.append(signal)
        else:
            # Broadcast to all leaf nodes
            leaves = self._get_leaves()
            for leaf in leaves:
                leaf.signals.append(signal)

    def integrate(self, current_time_ms: float, coincidence_window_ms: float = 25.0) -> float:
        """Integrate all signals through the tree toward soma (bottom-up).

        Returns the somatic membrane potential after integration.

        Algorithm:
        1. Each node sums its signals within the coincidence window
        2. Supralinear activation: integrated_signal^supralinear_exp
        3. bAP gate: probabilistic modulation of coincidence detection
        4. Propagate upward to soma, weighted by spine resistances
        """
        return self._integrate_node(self._root, current_time_ms, coincidence_window_ms)

    def _integrate_node(
        self, node: DendriticNode, current_time_ms: float, coincidence_window_ms: float
    ) -> float:
        # 1. Sum children's integrated signals
        child_sum = 0.0
        for child in node.children:
            child_sum += self._integrate_node(child, current_time_ms, coincidence_window_ms)

        # 2. Detect coincident signals at this node
        coincident_signals = [
            s for s in node.signals
            if abs(s.arrival_time_ms - current_time_ms) <= coincidence_window_ms
        ]

        local_sum = sum(s.amplitude * s.weight / s.spine_resistance for s in coincident_signals)

        # 3. Nonlinear integration: supralinear activation
        total_input = local_sum + child_sum
        if total_input > 0:
            activated = total_input ** self._supralinear_exp
        else:
            activated = 0.0

        # 4. bAP probability gate: random gating of coincidence detection
        if random.random() < node.bap_probability * (1.0 / (1.0 + node.spine_resistance)):
            activated *= 1.5  # bAP boosts NMDA spike

        # 5. Spine resistance modulates amplitude and speed
        activated /= node.spine_resistance

        node.membrane_potential = activated

        # Clear processed signals
        node.signals.clear()

        return activated

    def _find_node(self, node_id: str, current: DendriticNode | None = None) -> DendriticNode | None:
        if current is None:
            current = self._root
        if current.node_id == node_id:
            return current
        for child in current.children:
            found = self._find_node(node_id, child)
            if found is not None:
                return found
        return None

    def _get_leaves(self, node: DendriticNode | None = None) -> list[DendriticNode]:
        if node is None:
            node = self._root
        if not node.children:
            return [node]
        leaves: list[DendriticNode] = []
        for child in node.children:
            leaves.extend(self._get_leaves(child))
        return leaves

    def get_soma_potential(self) -> float:
        return self._root.membrane_potential

    def reset(self) -> None:
        """Reset all membrane potentials."""
        def _reset_node(node: DendriticNode) -> None:
            node.membrane_potential = 0.0
            node.signals.clear()
            for child in node.children:
                _reset_node(child)

        _reset_node(self._root)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "node_count": self._node_count,
            "max_depth": self._max_depth,
            "branching_factor": self._branching_factor,
            "soma_potential": self._root.membrane_potential,
            "leaf_count": len(self._get_leaves()),
        }
