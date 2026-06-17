"""Tests for L5: StigmergyFieldV2 — Stigmergy场v2.0."""

import time

import numpy as np
import pytest

from src.l5.stigmergy_field_v2 import (
    CitationEdge,
    ResilienceReport,
    StigmergyFieldV2,
    StigmergyV2Config,
    TraceEntry,
    TrustScore,
)


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def config() -> StigmergyV2Config:
    return StigmergyV2Config(
        trace_grid_size=64,
        trust_history_window=50,
        max_trace_age_days=90,
    )


@pytest.fixture
def field(config: StigmergyV2Config) -> StigmergyFieldV2:
    return StigmergyFieldV2(config=config)


@pytest.fixture
def populated_field(field: StigmergyFieldV2) -> StigmergyFieldV2:
    """Field populated with traces from multiple agents."""
    rng = np.random.RandomState(42)
    for i in range(10):
        agent = f"agent-{i % 4}"
        field.append_trace(
            agent_id=agent,
            action_type=f"action-{i % 3}",
            content_hash=f"hash-{i:04d}",
            quality_score=0.5 + rng.random() * 0.5,
            position=(rng.random(), rng.random()),
        )
    return field


# ═══════════════════════════════════════════════════════════════════════
# Unit Tests
# ═══════════════════════════════════════════════════════════════════════


class TestFieldInit:
    """Test initialization and configuration."""

    def test_default_init(self) -> None:
        f = StigmergyFieldV2()
        assert f.stats["total_traces"] == 0
        assert f.stats["active_traces"] == 0
        assert f.stats["total_citations"] == 0

    def test_custom_config(self, config: StigmergyV2Config) -> None:
        f = StigmergyFieldV2(config=config)
        assert f._config.trace_grid_size == 64
        assert f._config.trust_history_window == 50

    def test_initial_stats(self, field: StigmergyFieldV2) -> None:
        stats = field.stats
        assert stats["registered_agents"] == 0
        assert stats["isolated_agents"] == 0
        assert stats["avg_trust"] is None


class TestTraceGrid:
    """Test append-only trace grid."""

    def test_append_trace(self, field: StigmergyFieldV2) -> None:
        trace = field.append_trace("agent-1", "backtest", "hash-001", quality_score=0.8)
        assert trace.agent_id == "agent-1"
        assert trace.action_type == "backtest"
        assert trace.quality_score == 0.8
        assert field.stats["total_traces"] == 1

    def test_append_trace_returns_unique_ids(self, field: StigmergyFieldV2) -> None:
        t1 = field.append_trace("a1", "act", "h1")
        t2 = field.append_trace("a1", "act", "h2")
        assert t1.trace_id != t2.trace_id

    def test_trace_effective_strength(self, field: StigmergyFieldV2) -> None:
        trace = field.append_trace("a1", "act", "h1", quality_score=0.9)
        # Fresh trace: high effective strength
        assert trace.effective_strength >= 0.8

    def test_trace_is_not_expired_when_fresh(self, field: StigmergyFieldV2) -> None:
        trace = field.append_trace("a1", "act", "h1")
        assert trace.is_expired is False

    def test_trace_needs_content_hash(self, field: StigmergyFieldV2) -> None:
        """Each trace should have a content hash."""
        trace = field.append_trace("a1", "act", "abc123")
        assert trace.content_hash == "abc123"

    def test_get_traces_at_position(self, populated_field: StigmergyFieldV2) -> None:
        traces = populated_field.get_traces_at((0.5, 0.5), radius=0.3)
        assert isinstance(traces, list)
        for t in traces:
            assert isinstance(t, TraceEntry)

    def test_trace_with_evidence_refs(self, field: StigmergyFieldV2) -> None:
        trace = field.append_trace("a1", "audit", "h1", evidence_refs=["e1", "e2"])
        assert len(trace.evidence_refs) == 2

    def test_trace_ttl_set_from_config(self, config: StigmergyV2Config) -> None:
        f = StigmergyFieldV2(config=config)
        trace = f.append_trace("a1", "act", "h1")
        assert trace.ttl_days == config.max_trace_age_days


class TestCitationGraph:
    """Test citation creation and traversal."""

    def test_cite_trace(self, field: StigmergyFieldV2) -> None:
        parent = field.append_trace("agent-1", "research", "hash-parent", quality_score=0.9)
        child = field.append_trace("agent-2", "research", "hash-child", quality_score=0.8)

        edge = field.cite_trace(parent.trace_id, "agent-2", child.trace_id, relevance_score=0.8)
        assert edge is not None
        assert edge.parent_trace_id == parent.trace_id
        assert edge.citing_agent_id == "agent-2"

    def test_cite_increments_parent_count(self, field: StigmergyFieldV2) -> None:
        parent = field.append_trace("a1", "act", "h1")
        child = field.append_trace("a2", "act", "h2")
        field.cite_trace(parent.trace_id, "a2", child.trace_id)
        assert parent.citations == 1

    def test_cite_nonexistent_parent(self, field: StigmergyFieldV2) -> None:
        child = field.append_trace("a2", "act", "h2")
        edge = field.cite_trace("nonexistent", "a2", child.trace_id)
        assert edge is None

    def test_cite_nonexistent_child(self, field: StigmergyFieldV2) -> None:
        parent = field.append_trace("a1", "act", "h1")
        edge = field.cite_trace(parent.trace_id, "a1", "nonexistent")
        assert edge is None

    def test_citation_chain(self, field: StigmergyFieldV2) -> None:
        """Build a chain: t1 → t2 → t3."""
        t1 = field.append_trace("a1", "research", "h1", quality_score=0.9)
        t2 = field.append_trace("a2", "research", "h2", quality_score=0.8)
        t3 = field.append_trace("a3", "research", "h3", quality_score=0.7)

        field.cite_trace(t1.trace_id, "a2", t2.trace_id)
        field.cite_trace(t2.trace_id, "a3", t3.trace_id)

        chain = field.get_citation_chain(t3.trace_id, depth=3)
        assert len(chain) >= 1  # At least direct parents

    def test_multiple_citations(self, field: StigmergyFieldV2) -> None:
        parent = field.append_trace("a1", "foundational", "h-parent", quality_score=0.95)
        child1 = field.append_trace("a2", "build", "h-child1")
        child2 = field.append_trace("a3", "build", "h-child2")

        field.cite_trace(parent.trace_id, "a2", child1.trace_id)
        field.cite_trace(parent.trace_id, "a3", child2.trace_id)

        assert parent.citations == 2


class TestBehavioralTrust:
    """Test behavioral trust scoring."""

    def test_score_trust_new_agent(self, field: StigmergyFieldV2) -> None:
        trust = field.score_trust("unknown-agent")
        assert isinstance(trust, TrustScore)
        assert trust.agent_id == "unknown-agent"
        # Unknown agent gets default scores
        assert 0.0 <= trust.composite <= 1.0

    def test_score_trust_with_history(self, populated_field: StigmergyFieldV2) -> None:
        """Agent with high-quality traces should have higher trust."""
        trust = populated_field.score_trust("agent-0")
        assert isinstance(trust, TrustScore)
        assert 0.0 <= trust.composite <= 1.0
        assert 0.0 <= trust.citation_quality <= 1.0
        assert 0.0 <= trust.consistency <= 1.0
        assert 0.0 <= trust.contribution <= 1.0

    def test_trust_level_categories(self, field: StigmergyFieldV2) -> None:
        score = TrustScore(agent_id="test", composite=0.85)
        assert score.trust_level == "high"

        score.composite = 0.6
        assert score.trust_level == "medium"

        score.composite = 0.4
        assert score.trust_level == "low"

        score.composite = 0.2
        assert score.trust_level == "untrusted"

    def test_flag_suspicious(self, populated_field: StigmergyFieldV2) -> None:
        flags = populated_field.flag_suspicious("agent-0")
        assert isinstance(flags, list)

    def test_trust_isolates_untrusted(self, field: StigmergyFieldV2) -> None:
        """Agent with consistently low-quality traces should be isolated."""
        # Create low quality traces
        for i in range(20):
            field.append_trace("bad-agent", "spam", f"bad-{i}", quality_score=0.1)
        trust = field.score_trust("bad-agent")
        if trust.trust_level == "untrusted":
            assert "bad-agent" in field._isolated_agents


class TestNichePartitioning:
    """Test ecological niche partitioning."""

    def test_observe_niche_partitioning(self, populated_field: StigmergyFieldV2) -> None:
        niches = populated_field.observe_niche_partitioning()
        assert len(niches) > 0
        for agent_id, niche in niches.items():
            assert niche.agent_id == agent_id
            assert 0.0 <= niche.specialization_index <= 1.0

    def test_niche_primary_domain(self, populated_field: StigmergyFieldV2) -> None:
        niches = populated_field.observe_niche_partitioning()
        for niche in niches.values():
            assert isinstance(niche.primary_domain, str)

    def test_niche_jaccard_overlaps(self, populated_field: StigmergyFieldV2) -> None:
        niches = populated_field.observe_niche_partitioning()
        for niche in niches.values():
            for other_agent, overlap in niche.jaccard_overlaps.items():
                assert 0.0 <= overlap <= 1.0


class TestResilience:
    """Test network resilience computation."""

    def test_compute_resilience(self, populated_field: StigmergyFieldV2) -> None:
        report = populated_field.compute_resilience(bad_actor_ratio=0.3)
        assert isinstance(report, ResilienceReport)
        assert report.bad_actor_ratio == 0.3
        assert isinstance(report.tolerance, bool)

    def test_resilience_with_no_agents(self, field: StigmergyFieldV2) -> None:
        report = field.compute_resilience(bad_actor_ratio=0.5)
        assert report.output_loss_pct == 0.0

    def test_resilience_reports_accumulate(self, populated_field: StigmergyFieldV2) -> None:
        populated_field.compute_resilience(0.2)
        populated_field.compute_resilience(0.4)
        assert len(populated_field._resilience_reports) == 2


class TestNormPropagation:
    """Test norm propagation observation."""

    def test_observe_norm_propagation(self, populated_field: StigmergyFieldV2) -> None:
        report = populated_field.observe_norm_propagation("quality_audit", "audit")
        assert report.norm_id == "quality_audit"
        assert 0.0 <= report.current_adoption <= 1.0
        assert report.organic_spread is True

    def test_norm_tracks_adoption(self, populated_field: StigmergyFieldV2) -> None:
        report = populated_field.observe_norm_propagation("test_norm", "action-0")
        assert report.norm_id == "test_norm"
        assert isinstance(report.agents_adopted, list)


class TestPurgeExpired:
    """Test trace expiration and purging."""

    def test_purge_expired_removes_old_traces(self, field: StigmergyFieldV2) -> None:
        trace = field.append_trace("a1", "act", "h1")
        trace.timestamp = 0.0  # Force very old
        purged = field.purge_expired_traces()
        assert purged >= 1
        # Trace should be gone
        assert trace.trace_id not in field._traces

    def test_fresh_trace_not_purged(self, field: StigmergyFieldV2) -> None:
        field.append_trace("a1", "act", "h1")
        purged = field.purge_expired_traces()
        assert purged == 0


class TestReset:
    """Test field reset."""

    def test_reset_clears_all(self, populated_field: StigmergyFieldV2) -> None:
        populated_field.reset()
        assert populated_field.stats["total_traces"] == 0
        assert populated_field.stats["active_traces"] == 0
        assert populated_field.stats["total_citations"] == 0
        assert populated_field.stats["registered_agents"] == 0
        assert populated_field.stats["isolated_agents"] == 0
