"""Constraint Closure — strategy ↔ risk ↔ evolution closed loop detection.

Constraint closure is the second half of autopoietic self-maintenance:
- Catalytic closure: Skills catalyze each other's execution (skill_catalysis_graph.py)
- Constraint closure: The system's constraints are themselves products of the system

Per Kauffman (2026): "Constraint A constrains process 1 to build constraint B;
B constrains process 2 to build C; C constrains process 3 to build A."
The system does thermodynamic work to build its own constraints.

In Fungal Cortex:
- Strategy generates signals → constrained by risk rules
- Risk rules evolve → constrained by evolution process
- Evolution process adapts → constrained by strategy performance
- This forms a closed loop: strategy ⇄ risk ⇄ evolution ⇄ strategy
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class Constraint:
    """A single constraint in the system."""

    name: str
    constraint_type: str  # risk, capital, compliance, performance, resource
    source: str  # Which process produced this constraint
    targets: list[str]  # Which processes this constraint affects
    value: Any = None
    min_value: float | None = None
    max_value: float | None = None
    active: bool = True
    created_at: float = field(default_factory=time.time)


@dataclass
class ClosureReport:
    """Report on constraint closure status."""

    total_constraints: int
    active_constraints: int
    closed_loops: int  # Number of complete constraint cycles
    closure_achieved: bool  # At least one full cycle exists
    orphan_constraints: list[str]  # Constraints not part of any cycle
    constraint_graph_density: float  # Edge density of the constraint graph
    timestamp: float = field(default_factory=time.time)


class ConstraintClosure:
    """Detects and monitors constraint closure in the system.

    Three constraint domains:
    1. Strategy → Risk: Strategy outputs are constrained by risk rules
    2. Risk → Evolution: Risk rules are modified by evolution
    3. Evolution → Strategy: Evolution shapes strategy generation

    Full closure: All three domains form a closed loop.
    """

    DOMAINS = ["strategy", "risk", "evolution"]

    def __init__(self, check_interval: int = 3600) -> None:
        self._constraints: dict[str, Constraint] = {}
        self._check_interval = check_interval
        self._last_check: float = 0.0
        self._logger = CortexLogger("constraint_closure")
        self._closure_history: list[ClosureReport] = []

    def add_constraint(
        self,
        name: str,
        constraint_type: str,
        source: str,
        targets: list[str],
        value: Any = None,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> Constraint:
        """Add a constraint to the system."""
        constraint = Constraint(
            name=name,
            constraint_type=constraint_type,
            source=source,
            targets=targets,
            value=value,
            min_value=min_value,
            max_value=max_value,
        )
        self._constraints[name] = constraint
        self._logger.info("constraint_added", name=name, source=source, targets=targets)
        return constraint

    def remove_constraint(self, name: str) -> bool:
        """Remove a constraint."""
        if name in self._constraints:
            del self._constraints[name]
            return True
        return False

    def check_closure(self) -> ClosureReport:
        """Check if the constraint system has achieved closure.

        Closure means: every domain constrains and is constrained by others,
        forming at least one complete cycle (strategy→risk→evolution→strategy).
        """
        self._last_check = time.time()

        # Build constraint graph
        graph: dict[str, list[str]] = {d: [] for d in self.DOMAINS}
        for c in self._constraints.values():
            if c.active and c.source in graph:
                for t in c.targets:
                    if t in graph:
                        graph[c.source].append(t)

        # Detect cycles
        cycles = self._find_cycles(graph)

        # Find orphan constraints (not part of any cycle)
        in_cycle: set[str] = set()
        for cycle in cycles:
            in_cycle.update(cycle)

        all_domain_constraints: dict[str, list[str]] = {d: [] for d in self.DOMAINS}
        for c in self._constraints.values():
            if c.active and c.source in all_domain_constraints:
                all_domain_constraints[c.source].append(c.name)

        orphans: list[str] = []
        for domain, c_names in all_domain_constraints.items():
            if domain not in in_cycle:
                orphans.extend(c_names)

        # Graph density
        all_edges = sum(len(v) for v in graph.values())
        max_edges = len(self.DOMAINS) ** 2
        density = all_edges / max_edges if max_edges > 0 else 0.0

        report = ClosureReport(
            total_constraints=len(self._constraints),
            active_constraints=sum(1 for c in self._constraints.values() if c.active),
            closed_loops=len(cycles),
            closure_achieved=len(cycles) >= 1,
            orphan_constraints=orphans,
            constraint_graph_density=density,
        )
        self._closure_history.append(report)
        if len(self._closure_history) > 100:
            self._closure_history = self._closure_history[-100:]

        self._logger.info("closure_check", achieved=report.closure_achieved, cycles=report.closed_loops, orphans=len(orphans))
        return report

    def _find_cycles(self, graph: dict[str, list[str]]) -> list[list[str]]:
        """Find cycles in the constraint graph using DFS."""
        cycles: list[list[str]] = []
        visited: set[str] = set()

        for node in graph:
            if node in visited:
                continue
            path: list[str] = []
            path_set: set[str] = set()
            self._dfs_constraint_cycles(node, node, graph, path, path_set, visited, cycles)

        return cycles

    def _dfs_constraint_cycles(
        self,
        start: str,
        current: str,
        graph: dict[str, list[str]],
        path: list[str],
        path_set: set[str],
        visited: set[str],
        cycles: list[list[str]],
    ) -> None:
        """DFS for constraint graph cycles."""
        path.append(current)
        path_set.add(current)

        for neighbor in graph.get(current, []):
            if neighbor == start and len(path) >= 2:
                cycles.append(list(path) + [start])
            elif neighbor not in path_set and neighbor not in visited:
                self._dfs_constraint_cycles(start, neighbor, graph, path, path_set, visited, cycles)

        path.pop()
        path_set.discard(current)
        if current == start:
            visited.add(current)

    def get_domain_constraints(self, domain: str) -> list[Constraint]:
        """Get all constraints from a specific domain."""
        return [c for c in self._constraints.values() if c.source == domain]

    @property
    def stats(self) -> dict[str, Any]:
        report = self.check_closure()
        return {
            "total_constraints": report.total_constraints,
            "active_constraints": report.active_constraints,
            "closed_loops": report.closed_loops,
            "closure_achieved": report.closure_achieved,
            "orphan_count": len(report.orphan_constraints),
            "graph_density": round(report.constraint_graph_density, 3),
        }
