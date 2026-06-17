"""Skill Catalysis Graph — RAF set detection + catalytic cycle analysis.

Models skill relationships as a directed graph where:
- Nodes = Skills/Strategies
- Edges = Catalysis (skill A's output enhances skill B's execution)
- Cycles = Autocatalytic sets (RAF = Reflexively Autocatalytic and Food-generated)

A RAF set is:
1. Reflexively Autocatalytic: Every element is catalyzed by some element in the set
2. Food-generated: All elements can be built from a "food set" using only catalyzed reactions

This maps to skills: a set of skills that mutually enhance each other's performance,
capable of self-improvement without external intervention.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class CatalysisEdge:
    """An edge in the catalysis graph: source catalyzes target."""

    source: str
    target: str
    weight: float = 0.5  # Catalysis strength (0-1)
    evidence: str = ""  # Why this catalysis exists
    edge_type: str = "enhances"  # enhances, inhibits, requires


@dataclass
class RAFSet:
    """A detected Reflexively Autocatalytic and Food-generated set."""

    members: list[str]  # Skill names in the RAF set
    size: int = 0
    density: float = 0.0  # Edge density within the set
    cycles: list[list[str]] = field(default_factory=list)  # Detected catalytic cycles
    sustainability: float = 0.0  # How self-sustaining (0-1)

    def __post_init__(self) -> None:
        self.size = len(self.members)


class SkillCatalysisGraph:
    """Directed graph of skill catalysis relationships.

    Key algorithms:
    - add_catalysis(): Register a catalytic relationship between skills
    - find_catalytic_cycles(): Detect self-reinforcing skill clusters
    - find_raf_sets(): Find all RAF sets in the graph
    - compute_sustainability(): How self-sustaining is a skill set
    - topological_order(): Dependency-respecting skill load order
    """

    def __init__(self, max_nodes: int = 500) -> None:
        self._adjacency: dict[str, list[str]] = {}  # source → [targets]
        self._edges: dict[tuple[str, str], CatalysisEdge] = {}
        self._nodes: set[str] = set()
        self._max_nodes = max_nodes
        self._logger = CortexLogger("skill_catalysis_graph")

    def add_node(self, skill_name: str) -> bool:
        """Add a skill node. Returns False if at capacity."""
        if len(self._nodes) >= self._max_nodes:
            return False
        self._nodes.add(skill_name)
        if skill_name not in self._adjacency:
            self._adjacency[skill_name] = []
        return True

    def add_catalysis(self, source: str, target: str, weight: float = 0.5, evidence: str = "", edge_type: str = "enhances") -> bool:
        """Register a catalytic relationship: source catalyzes target."""
        if source not in self._nodes:
            self.add_node(source)
        if target not in self._nodes:
            self.add_node(target)

        self._adjacency.setdefault(source, []).append(target)
        self._edges[(source, target)] = CatalysisEdge(
            source=source,
            target=target,
            weight=weight,
            evidence=evidence,
            edge_type=edge_type,
        )
        self._logger.debug("catalysis_added", source=source, target=target, weight=weight)
        return True

    def remove_catalysis(self, source: str, target: str) -> bool:
        """Remove a catalytic relationship."""
        key = (source, target)
        if key in self._edges:
            del self._edges[key]
            if target in self._adjacency.get(source, []):
                self._adjacency[source].remove(target)
            return True
        return False

    def get_catalysts(self, target: str) -> list[str]:
        """Get all skills that catalyze the target."""
        return [s for s in self._nodes if target in self._adjacency.get(s, [])]

    def get_catalyzed(self, source: str) -> list[str]:
        """Get all skills catalyzed by the source."""
        return list(self._adjacency.get(source, []))

    def find_catalytic_cycles(self, min_size: int = 2) -> list[list[str]]:
        """Find all directed cycles (catalytic loops) in the graph."""
        cycles: list[list[str]] = []
        visited: set[str] = set()

        for node in self._nodes:
            if node in visited:
                continue
            path: list[str] = []
            path_set: set[str] = set()
            self._dfs_cycles(node, node, path, path_set, visited, cycles, min_size)

        return cycles

    def _dfs_cycles(
        self,
        start: str,
        current: str,
        path: list[str],
        path_set: set[str],
        visited: set[str],
        cycles: list[list[str]],
        min_size: int,
    ) -> None:
        """DFS to find cycles in the catalysis graph."""
        path.append(current)
        path_set.add(current)

        for neighbor in self._adjacency.get(current, []):
            if neighbor == start and len(path) >= min_size:
                cycles.append(list(path) + [start])
            elif neighbor not in path_set and neighbor not in visited:
                self._dfs_cycles(start, neighbor, path, path_set, visited, cycles, min_size)

        path.pop()
        path_set.discard(current)
        if current == start:
            visited.add(current)

    def find_raf_sets(self, min_size: int = 3) -> list[RAFSet]:
        """Find Reflexively Autocatalytic and Food-generated sets.

        A RAF set is a set of skills where each member is catalyzed by
        at least one other member in the set.
        """
        cycles = self.find_catalytic_cycles(min_size)
        rafs: list[RAFSet] = []

        for cycle in cycles:
            members = list(set(cycle[:-1]))  # Remove duplicate start node
            if len(members) < min_size:
                continue

            # Compute density: edges within set / possible edges
            possible = len(members) * (len(members) - 1)
            if possible == 0:
                continue
            actual = sum(
                1 for s in members
                for t in members
                if s != t and t in self._adjacency.get(s, [])
            )
            density = actual / possible

            # Sustainability: fraction of members that have at least one internal catalyst
            catalyzed = sum(
                1 for m in members
                if any(c in members for c in self.get_catalysts(m))
            )
            sustainability = catalyzed / len(members) if members else 0.0

            rafs.append(RAFSet(
                members=members,
                density=density,
                cycles=[cycle],
                sustainability=sustainability,
            ))

        return rafs

    def compute_sustainability(self, skill_set: list[str]) -> float:
        """How self-sustaining is a skill set? (0-1)

        Sustainability = fraction of skills that have at least one
        internal catalyst within the set.
        """
        if not skill_set:
            return 0.0
        set_members = set(skill_set)
        internal_catalyzed = 0
        for skill in skill_set:
            catalysts = set(self.get_catalysts(skill))
            if catalysts & set_members:
                internal_catalyzed += 1
        return internal_catalyzed / len(skill_set)

    def topological_order(self) -> list[str]:
        """Return skills in topological order (dependencies first)."""
        in_degree: dict[str, int] = {n: 0 for n in self._nodes}
        for source, targets in self._adjacency.items():
            for target in targets:
                if target in in_degree:
                    in_degree[target] += 1

        queue = [n for n, d in in_degree.items() if d == 0]
        order: list[str] = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in self._adjacency.get(node, []):
                if neighbor in in_degree:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

        # Add remaining nodes (in cycles)
        for node in self._nodes:
            if node not in order:
                order.append(node)

        return order

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    @property
    def stats(self) -> dict[str, Any]:
        cycles = self.find_catalytic_cycles()
        rafs = self.find_raf_sets()
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "catalytic_cycles": len(cycles),
            "raf_sets": len(rafs),
            "largest_raf": max((r.size for r in rafs), default=0),
            "avg_sustainability": sum(r.sustainability for r in rafs) / max(len(rafs), 1),
        }
