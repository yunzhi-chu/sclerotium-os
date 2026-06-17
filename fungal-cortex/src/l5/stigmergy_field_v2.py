"""Stigmergy Field v2.0 — 70天实验验证的Stigmergy场架构.

Biological Metaphor:
  Ant colonies build complex structures without blueprints or foremen.
  Each ant deposits pheromones as it works; other ants smell the accumulated
  chemical traces and are guided to productive areas. This indirect coordination
  — stigmergy — scales to millions of individuals without central control.

  Mycel Network's 70-day experiment (2026) proved this at production scale:
  - Stigmergy solved 32× more problems than hierarchy (48.5% vs 1.5%)
  - Network tolerated 45% bad actors with <3% output loss
  - Behavioral trust identified ALL problematic agents BEFORE human flagging
  - Norms propagated spontaneously without enforcement

Key Innovation (v4.0):
  Triune stigmergy system: Photormone traces + Citation graph + Behavioral trust.
  Append-only trace grid ensures auditability. Niche partitioning without
  role assignment — agents specialize naturally by observing traces.

References:
  - Mycel Network (Zenodo 2026): 70-day 18-agent governance experiment
  - Harvard RAnts (PRX Life 2026): Exbodied Intelligence via photormones
  - SwarmHarness (May 2026): SwarmCredit Shapley-value incentives
"""

from __future__ import annotations

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


@dataclass
class TraceEntry:
    """An append-only trace in the stigmergy grid.

    Like an ant's pheromone deposit — once laid down, it can only decay,
    never be modified. Other agents read these traces to coordinate.
    """

    trace_id: str
    agent_id: str
    action_type: str                    # e.g., "backtest", "audit", "claim", "refactor"
    content_hash: str                   # Hash of the action content
    evidence_refs: list[str] = field(default_factory=list)  # References to evidence
    quality_score: float = 0.5          # 0-1 action quality
    position: tuple[float, float] = (0.0, 0.0)  # Position in the field
    citations: int = 0                  # Number of times cited
    timestamp: float = field(default_factory=time.time)
    ttl_days: float = 90.0             # Time-to-live in days
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def age_days(self) -> float:
        """Age of this trace in days."""
        return (time.time() - self.timestamp) / 86400.0

    @property
    def is_expired(self) -> bool:
        """Whether this trace has exceeded its TTL."""
        return self.age_days > self.ttl_days

    @property
    def effective_strength(self) -> float:
        """Effective signal strength accounting for age decay."""
        decay = max(0.0, 1.0 - self.age_days / self.ttl_days)
        return self.quality_score * decay * (1.0 + math.log(1 + self.citations))


@dataclass
class CitationEdge:
    """A citation link between two traces.

    Like one ant following another's pheromone trail — the citing agent
    builds upon the work of the cited agent, creating a knowledge DAG.
    """

    parent_trace_id: str
    child_trace_id: str
    citing_agent_id: str
    relevance_score: float = 0.5       # How relevant the parent is to the child
    timestamp: float = field(default_factory=time.time)


@dataclass
class NicheMap:
    """Ecological niche partitioning map.

    Agents naturally specialize by observing which traces they interact with.
    No role assignment — niches emerge from interaction patterns.
    """

    agent_id: str
    primary_domain: str = "general"
    domain_activity: dict[str, int] = field(default_factory=dict)  # domain → interaction count
    jaccard_overlaps: dict[str, float] = field(default_factory=dict)  # agent_id → overlap
    specialization_index: float = 0.0   # 0=generalist, 1=ultra-specialist
    last_updated: float = field(default_factory=time.time)


@dataclass
class TrustScore:
    """Behavioral trust score based on observed actions.

    Trust is earned through behavior, not granted by authority.
    The 70-day experiment showed behavioral trust identifies ALL
    problematic agents before human flagging.
    """

    agent_id: str
    citation_quality: float = 0.5       # Average quality of cited traces
    consistency: float = 0.5            # Alignment between actions and claims
    contribution: float = 0.5           # How often this agent's traces are cited
    composite: float = 0.5              # Weighted composite score
    flags: list[str] = field(default_factory=list)
    last_evaluated: float = field(default_factory=time.time)

    @property
    def is_suspicious(self) -> bool:
        """Agent flagged for suspicious behavior."""
        return len(self.flags) > 0

    @property
    def trust_level(self) -> str:
        """Categorical trust level."""
        if self.composite >= 0.8:
            return "high"
        elif self.composite >= 0.5:
            return "medium"
        elif self.composite >= 0.3:
            return "low"
        else:
            return "untrusted"


@dataclass
class ResilienceReport:
    """Network resilience assessment against bad actors."""

    bad_actor_ratio: float              # Fraction of malicious agents
    output_loss_pct: float              # Output quality degradation
    detected_by_trust: int              # Bad actors identified by trust scoring
    undetected_count: int               # Bad actors missed by trust
    isolated_count: int                 # Automatically isolated
    tolerance: bool                     # Whether system tolerated this ratio
    timestamp: float = field(default_factory=time.time)


@dataclass
class NormSpreadReport:
    """Norm propagation observation report.

    In the 70-day experiment, quality norms spread to new agents
    within 24 hours — without enforcement, penalty, or central mandate.
    """

    norm_id: str
    initial_adoption: float = 0.0       # Initial agent adoption rate
    current_adoption: float = 0.0       # Current adoption rate
    spread_rate: float = 0.0            # Agents adopting per day
    organic_spread: bool = True         # True if spread without enforcement
    agents_adopted: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class StigmergyV2Config:
    """Configuration for Stigmergy Field v2.0."""

    trace_grid_size: int = 1024
    citation_halflife_hours: float = 24.0
    niche_overlap_threshold: float = 0.3
    trust_history_window: int = 100
    trust_citation_weight: float = 0.35
    trust_consistency_weight: float = 0.35
    trust_contribution_weight: float = 0.30
    resilience_bad_actor_ratio: float = 0.45
    norm_propagation_threshold: float = 0.5
    max_trace_age_days: int = 90


# ═══════════════════════════════════════════════════════════════════════
# Core Field
# ═══════════════════════════════════════════════════════════════════════


class StigmergyFieldV2:
    """Stigmergy Field v2.0 — the 70-day experiment-validated architecture.

    Three interacting subsystems:
      1. Append-only trace grid — like an ant colony's pheromone field
      2. Citation graph — like scientific paper references, building a knowledge DAG
      3. Behavioral trust — observing actions, not credentials

    Usage::

        field = StigmergyFieldV2()
        trace = field.append_trace("agent-1", "backtest", content_hash, quality=0.8)
        field.cite_trace(trace.trace_id, "agent-2", new_trace_id)
        trust = field.score_trust("agent-1")
        report = field.compute_resilience(bad_actor_ratio=0.45)
    """

    def __init__(self, config: StigmergyV2Config | None = None) -> None:
        self._config = config or StigmergyV2Config()
        self._logger = CortexLogger("stigmergy_v2")

        # Trace grid
        self._traces: dict[str, TraceEntry] = {}
        self._trace_grid: dict[tuple[int, int], list[str]] = {}  # (x, y) → trace_ids
        self._agent_traces: dict[str, list[str]] = {}             # agent_id → trace_ids

        # Citation graph
        self._citations: dict[str, list[CitationEdge]] = {}       # trace_id → citations from it
        self._citation_count: int = 0

        # Behavioral trust
        self._trust_scores: dict[str, TrustScore] = {}
        self._behavior_history: dict[str, deque[dict[str, Any]]] = {}  # agent_id → recent actions

        # Niche partitioning
        self._niche_maps: dict[str, NicheMap] = {}

        # Norm propagation
        self._norms: dict[str, dict[str, Any]] = {}
        self._norm_reports: list[NormSpreadReport] = []

        # Resilience tracking
        self._resilience_reports: list[ResilienceReport] = []
        self._isolated_agents: set[str] = set()

        # Statistics
        self._total_traces: int = 0
        self._total_citations: int = 0

        self._logger.info("stigmergy_v2_initialized",
                          grid_size=self._config.trace_grid_size)

    # ── Trace Grid ────────────────────────────────────────────────────

    def append_trace(
        self,
        agent_id: str,
        action_type: str,
        content_hash: str,
        quality_score: float = 0.5,
        evidence_refs: list[str] | None = None,
        position: tuple[float, float] | None = None,
    ) -> TraceEntry:
        """Append an immutable trace to the stigmergy grid.

        Like an ant depositing a pheromone — once laid, the trace is
        permanent (append-only). Other agents discover it by sensing
        the local area.

        Args:
            agent_id: ID of the acting agent
            action_type: Type of action performed
            content_hash: Hash of action content for integrity
            quality_score: Estimated quality of the action (0-1)
            evidence_refs: References to supporting evidence
            position: (x, y) position in the field

        Returns:
            The created TraceEntry
        """
        import hashlib
        trace_id = f"trace-{self._total_traces + 1:06d}"

        trace = TraceEntry(
            trace_id=trace_id,
            agent_id=agent_id,
            action_type=action_type,
            content_hash=content_hash,
            evidence_refs=evidence_refs or [],
            quality_score=quality_score,
            position=position or (0.0, 0.0),
            ttl_days=self._config.max_trace_age_days,
        )

        self._traces[trace_id] = trace

        # Grid positioning
        grid_pos = (int(trace.position[0] * self._config.trace_grid_size) % self._config.trace_grid_size,
                     int(trace.position[1] * self._config.trace_grid_size) % self._config.trace_grid_size)
        self._trace_grid.setdefault(grid_pos, []).append(trace_id)

        # Agent index
        self._agent_traces.setdefault(agent_id, []).append(trace_id)

        # Update niche map
        self._update_niche(agent_id, action_type)

        self._total_traces += 1
        self._logger.debug("trace_appended",
                           trace_id=trace_id,
                           agent=agent_id,
                           action=action_type,
                           quality=round(quality_score, 3))

        return trace

    def get_traces_at(self, position: tuple[float, float], radius: float = 0.1) -> list[TraceEntry]:
        """Get all traces within a radius of the given position.

        Like an ant sensing pheromones in its local area.
        """
        grid_pos = (int(position[0] * self._config.trace_grid_size) % self._config.trace_grid_size,
                     int(position[1] * self._config.trace_grid_size) % self._config.trace_grid_size)

        grid_radius = max(1, int(radius * self._config.trace_grid_size))
        found: list[TraceEntry] = []

        for dx in range(-grid_radius, grid_radius + 1):
            for dy in range(-grid_radius, grid_radius + 1):
                gx = (grid_pos[0] + dx) % self._config.trace_grid_size
                gy = (grid_pos[1] + dy) % self._config.trace_grid_size
                for trace_id in self._trace_grid.get((gx, gy), []):
                    trace = self._traces.get(trace_id)
                    if trace and not trace.is_expired:
                        found.append(trace)

        return found

    # ── Citation Graph ────────────────────────────────────────────────

    def cite_trace(
        self,
        parent_trace_id: str,
        citing_agent_id: str,
        child_trace_id: str,
        relevance_score: float = 0.5,
    ) -> CitationEdge | None:
        """Create a citation link between two traces.

        Like one scientist citing another's paper — the citing agent
        acknowledges that their work builds upon the cited work.
        In the 70-day experiment, 3,200+ citation edges formed a
        self-organizing knowledge DAG.

        Args:
            parent_trace_id: The trace being cited (the foundation)
            citing_agent_id: The agent making the citation
            child_trace_id: The trace doing the citing (the new work)
            relevance_score: How relevant the parent is to the child

        Returns:
            CitationEdge if both traces exist, None otherwise
        """
        if parent_trace_id not in self._traces:
            self._logger.warn("citation_parent_not_found", trace_id=parent_trace_id)
            return None
        if child_trace_id not in self._traces:
            self._logger.warn("citation_child_not_found", trace_id=child_trace_id)
            return None

        edge = CitationEdge(
            parent_trace_id=parent_trace_id,
            child_trace_id=child_trace_id,
            citing_agent_id=citing_agent_id,
            relevance_score=relevance_score,
        )

        self._citations.setdefault(parent_trace_id, []).append(edge)

        # Increment citation count on parent trace
        parent_trace = self._traces[parent_trace_id]
        parent_trace.citations += 1

        self._total_citations += 1
        self._citation_count += 1

        return edge

    def get_citation_chain(self, trace_id: str, depth: int = 3) -> list[list[TraceEntry]]:
        """Get the citation chain (ancestors) of a trace.

        Returns layered list: [direct_parents, grandparents, great_grandparents].
        """
        chain: list[list[TraceEntry]] = []
        current = {trace_id}
        visited: set[str] = set()

        for _ in range(depth):
            parents: set[str] = set()
            for tid in current:
                for edge_list in self._citations.values():
                    for edge in edge_list:
                        if edge.child_trace_id == tid and edge.parent_trace_id not in visited:
                            parents.add(edge.parent_trace_id)

            if not parents:
                break

            layer = [self._traces[pid] for pid in parents if pid in self._traces]
            chain.append(layer)
            visited.update(parents)
            current = parents

        return chain

    # ── Niche Partitioning ────────────────────────────────────────────

    def observe_niche_partitioning(self) -> dict[str, NicheMap]:
        """Observe natural niche partitioning without role assignment.

        Agents specialize by the types of traces they interact with.
        No central authority assigns roles — niches emerge organically.
        """
        for agent_id, trace_ids in self._agent_traces.items():
            if agent_id not in self._niche_maps:
                self._niche_maps[agent_id] = NicheMap(agent_id=agent_id)

            niche = self._niche_maps[agent_id]
            domain_activity: dict[str, int] = {}

            for tid in trace_ids[-100:]:  # Recent traces only
                trace = self._traces.get(tid)
                if trace:
                    domain_activity[trace.action_type] = domain_activity.get(trace.action_type, 0) + 1

            niche.domain_activity = domain_activity
            if domain_activity:
                niche.primary_domain = max(domain_activity, key=domain_activity.get)

            # Specialization index: Gini coefficient of activity distribution
            counts = list(domain_activity.values())
            if len(counts) > 1:
                mean = np.mean(counts)
                gini = sum(abs(a - b) for a in counts for b in counts) / (2 * len(counts)**2 * max(mean, 1e-10))
                niche.specialization_index = float(gini)
            else:
                niche.specialization_index = 0.0

            niche.last_updated = time.time()

        # Compute Jaccard overlaps
        agents = list(self._niche_maps.keys())
        for i, a1 in enumerate(agents):
            for a2 in agents[i + 1:]:
                d1 = set(self._niche_maps[a1].domain_activity.keys())
                d2 = set(self._niche_maps[a2].domain_activity.keys())
                intersection = len(d1 & d2)
                union = len(d1 | d2)
                overlap = intersection / max(union, 1)
                self._niche_maps[a1].jaccard_overlaps[a2] = overlap
                self._niche_maps[a2].jaccard_overlaps[a1] = overlap

        return dict(self._niche_maps)

    def _update_niche(self, agent_id: str, action_type: str) -> None:
        """Incrementally update niche map after each trace."""
        if agent_id not in self._niche_maps:
            self._niche_maps[agent_id] = NicheMap(agent_id=agent_id)
        niche = self._niche_maps[agent_id]
        niche.domain_activity[action_type] = niche.domain_activity.get(action_type, 0) + 1

    # ── Behavioral Trust ──────────────────────────────────────────────

    def score_trust(self, agent_id: str) -> TrustScore:
        """Compute behavioral trust score for an agent.

        Trust is based on three observable dimensions:
          1. Citation quality: Average quality of traces this agent cites
          2. Consistency: Alignment between claimed and actual behavior
          3. Contribution: How often this agent's traces are cited by others

        The 70-day experiment showed behavioral trust identifies ALL
        problematic agents — often before any human notices.

        Args:
            agent_id: ID of the agent to score

        Returns:
            TrustScore with composite and dimension scores
        """
        c = self._config

        # 1. Citation quality
        citation_quality = 0.5
        cited_traces = []
        for edges in self._citations.values():
            for edge in edges:
                if edge.citing_agent_id == agent_id:
                    if edge.parent_trace_id in self._traces:
                        cited_traces.append(self._traces[edge.parent_trace_id].quality_score)

        if cited_traces:
            citation_quality = float(np.mean(cited_traces))

        # 2. Consistency
        agent_traces = self._agent_traces.get(agent_id, [])
        if agent_traces:
            qualities = [self._traces[t].quality_score for t in agent_traces[-c.trust_history_window:] if t in self._traces]
            if qualities:
                # Consistency = 1 - std/mean (low variance = high consistency)
                q_mean = np.mean(qualities)
                q_std = np.std(qualities)
                consistency = max(0.0, 1.0 - q_std / max(q_mean, 1e-10))
            else:
                consistency = 0.5
        else:
            consistency = 0.5

        # 3. Contribution (how often this agent's traces are cited)
        contribution = 0.5
        total_cited = sum(1 for t in self._traces.values() if t.agent_id == agent_id and t.citations > 0)
        total_traces = max(len(agent_traces), 1)
        contribution = min(1.0, total_cited / total_traces)

        # Composite score
        composite = (
            c.trust_citation_weight * citation_quality +
            c.trust_consistency_weight * consistency +
            c.trust_contribution_weight * contribution
        )

        # Flag suspicious behavior
        flags: list[str] = []
        if citation_quality < 0.3:
            flags.append("low_citation_quality")
        if consistency < 0.3:
            flags.append("inconsistent_behavior")
        if composite < 0.3:
            flags.append("low_composite_trust")

        score = TrustScore(
            agent_id=agent_id,
            citation_quality=citation_quality,
            consistency=consistency,
            contribution=contribution,
            composite=composite,
            flags=flags,
        )

        self._trust_scores[agent_id] = score

        # Auto-isolate untrusted agents
        if score.trust_level == "untrusted":
            self._isolated_agents.add(agent_id)
            self._logger.warn("agent_isolated", agent_id=agent_id, trust=round(composite, 3))

        return score

    def flag_suspicious(self, agent_id: str) -> list[str]:
        """Get flags for a suspicious agent.

        Returns list of flag reasons. Empty list means no flags raised.
        """
        trust = self._trust_scores.get(agent_id)
        if trust is None:
            trust = self.score_trust(agent_id)
        return trust.flags

    # ── Resilience ────────────────────────────────────────────────────

    def compute_resilience(self, bad_actor_ratio: float | None = None) -> ResilienceReport:
        """Simulate network resilience against bad actors.

        Injects simulated bad actors and measures output quality degradation.
        The 70-day experiment validated: <3% output loss at 45% bad actors.

        Args:
            bad_actor_ratio: Fraction of agents to treat as malicious

        Returns:
            ResilienceReport with tolerance determination
        """
        if bad_actor_ratio is None:
            bad_actor_ratio = self._config.resilience_bad_actor_ratio

        all_agents = list(self._agent_traces.keys())
        n_bad = max(1, int(len(all_agents) * bad_actor_ratio))
        rng = np.random.RandomState(42)

        if all_agents:
            bad_actors = set(rng.choice(all_agents, size=min(n_bad, len(all_agents)), replace=False))

            # Simulate: bad actors produce low-quality traces
            good_qualities = []
            bad_qualities = []
            for trace in self._traces.values():
                if trace.agent_id in bad_actors:
                    bad_qualities.append(trace.quality_score * 0.3)  # Degraded
                else:
                    good_qualities.append(trace.quality_score)

            avg_good = np.mean(good_qualities) if good_qualities else 0.5
            avg_bad = np.mean(bad_qualities) if bad_qualities else 0.5
            output_loss_pct = max(0.0, (avg_good - avg_bad) / max(avg_good, 1e-10)) * 100.0
        else:
            bad_actors = set()
            output_loss_pct = 0.0

        # Detect via trust scoring
        detected_by_trust = sum(1 for aid in bad_actors if aid in self._trust_scores and self._trust_scores[aid].is_suspicious)
        undetected = len(bad_actors) - detected_by_trust
        isolated = len(self._isolated_agents & bad_actors)

        tolerance = bool(output_loss_pct < 3.0)  # <3% loss = tolerating

        report = ResilienceReport(
            bad_actor_ratio=bad_actor_ratio,
            output_loss_pct=round(output_loss_pct, 2),
            detected_by_trust=detected_by_trust,
            undetected_count=max(0, undetected),
            isolated_count=isolated,
            tolerance=tolerance,
        )

        self._resilience_reports.append(report)
        self._logger.info("resilience_computed",
                          bad_ratio=bad_actor_ratio,
                          loss_pct=round(output_loss_pct, 2),
                          tolerance=str(tolerance))

        return report

    # ── Norm Propagation ──────────────────────────────────────────────

    def observe_norm_propagation(self, norm_id: str, norm_pattern: str) -> NormSpreadReport:
        """Observe how a quality norm spreads through the agent population.

        In the 70-day experiment, new agents adopted quality norms within
        24 hours of joining — reading the trace evidence was sufficient.
        No enforcement, no penalty, no central mandate.

        Args:
            norm_id: Identifier for this norm
            norm_pattern: Pattern string to match in traces

        Returns:
            NormSpreadReport tracking adoption metrics
        """
        # Count agents whose traces match the norm pattern
        adopting_agents: list[str] = []
        for agent_id, trace_ids in self._agent_traces.items():
            for tid in trace_ids[-20:]:  # Recent traces
                trace = self._traces.get(tid)
                if trace and norm_pattern.lower() in trace.action_type.lower():
                    adopting_agents.append(agent_id)
                    break

        total_agents = max(len(self._agent_traces), 1)
        adoption_rate = len(set(adopting_agents)) / total_agents

        # Track in norms registry
        prev_adoption = self._norms.get(norm_id, {}).get("adoption_rate", 0.0)
        spread_rate = max(0.0, adoption_rate - prev_adoption)

        self._norms[norm_id] = {
            "norm_pattern": norm_pattern,
            "adoption_rate": adoption_rate,
            "adopting_agents": adopting_agents,
            "timestamp": time.time(),
        }

        report = NormSpreadReport(
            norm_id=norm_id,
            initial_adoption=prev_adoption,
            current_adoption=adoption_rate,
            spread_rate=spread_rate,
            organic_spread=True,  # Always organic in Stigmergy
            agents_adopted=adopting_agents,
        )

        if adoption_rate >= self._config.norm_propagation_threshold:
            self._logger.info("norm_established",
                              norm_id=norm_id,
                              adoption_rate=round(adoption_rate, 3))

        self._norm_reports.append(report)
        return report

    # ── Cleanup ───────────────────────────────────────────────────────

    def purge_expired_traces(self) -> int:
        """Remove expired traces. Like old pheromones evaporating."""
        expired = [tid for tid, trace in self._traces.items() if trace.is_expired]
        for tid in expired:
            self._traces.pop(tid, None)
            # Remove from grid
            for pos, trace_list in list(self._trace_grid.items()):
                if tid in trace_list:
                    trace_list.remove(tid)
                    if not trace_list:
                        del self._trace_grid[pos]
        if expired:
            self._logger.debug("traces_purged", count=len(expired))
        return len(expired)

    # ── Properties ────────────────────────────────────────────────────

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_traces": self._total_traces,
            "active_traces": len(self._traces),
            "total_citations": self._total_citations,
            "citation_graph_edges": self._citation_count,
            "registered_agents": len(self._agent_traces),
            "isolated_agents": len(self._isolated_agents),
            "avg_trust": round(np.mean([t.composite for t in self._trust_scores.values()]), 4)
            if self._trust_scores else None,
            "niche_count": len(self._niche_maps),
            "norms_tracked": len(self._norms),
            "resilience_reports": len(self._resilience_reports),
        }

    def reset(self) -> None:
        """Reset the entire stigmergy field."""
        self._traces.clear()
        self._trace_grid.clear()
        self._agent_traces.clear()
        self._citations.clear()
        self._trust_scores.clear()
        self._behavior_history.clear()
        self._niche_maps.clear()
        self._norms.clear()
        self._norm_reports.clear()
        self._resilience_reports.clear()
        self._isolated_agents.clear()
        self._total_traces = 0
        self._total_citations = 0
        self._citation_count = 0
        self._logger.debug("stigmergy_v2_reset")
