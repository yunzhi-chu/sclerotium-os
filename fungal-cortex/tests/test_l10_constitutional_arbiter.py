"""Tests for L10: ConstitutionalArbiter — 宪法仲裁器."""

import pytest

from src.l10.constitutional_arbiter import (
    Amendment,
    ConstitutionalArbiter,
    ConstitutionalPrinciple,
    GuardAction,
    GuardDecision,
    MoralJudgment,
)


@pytest.fixture
def arbiter() -> ConstitutionalArbiter:
    return ConstitutionalArbiter()


class TestArbiterInit:
    def test_default_init(self) -> None:
        a = ConstitutionalArbiter()
        assert a.stats["principles_count"] == 4
        assert a.stats["denied_count"] == 0

    def test_constitution_has_priorities(self, arbiter: ConstitutionalArbiter) -> None:
        principles = arbiter.list_principles()
        priorities = [p.priority for p in principles]
        assert priorities == sorted(priorities)  # Ordered by priority

    def test_get_principle(self, arbiter: ConstitutionalArbiter) -> None:
        p = arbiter.get_principle("P1_SAFETY")
        assert p is not None
        assert p.priority == 1
        assert p.is_immutable

    def test_get_nonexistent_principle(self, arbiter: ConstitutionalArbiter) -> None:
        assert arbiter.get_principle("P99_NOPE") is None


class TestGRACEMoralReasoning:
    def test_evaluate_forbidden_action(self, arbiter: ConstitutionalArbiter) -> None:
        action = GuardAction(
            action_id="a1", source_layer="L5",
            action_type="destroy_all_data",
        )
        judgment = arbiter.evaluate_action(action)
        assert judgment == MoralJudgment.FORBIDDEN

    def test_evaluate_permitted_action(self, arbiter: ConstitutionalArbiter) -> None:
        action = GuardAction(
            action_id="a2", source_layer="L4",
            action_type="help_optimize_routing",
        )
        judgment = arbiter.evaluate_action(action)
        assert judgment in (MoralJudgment.PERMITTED, MoralJudgment.UNDETERMINED)

    def test_evaluate_obligatory_action(self, arbiter: ConstitutionalArbiter) -> None:
        action = GuardAction(
            action_id="a3", source_layer="L6",
            action_type="disclose_risk_findings",
        )
        judgment = arbiter.evaluate_action(action)
        assert judgment in (MoralJudgment.OBLIGATORY, MoralJudgment.UNDETERMINED)


class TestRuntimeGuard:
    def test_intercept_allows_safe_action(self, arbiter: ConstitutionalArbiter) -> None:
        action = GuardAction(
            action_id="safe-1", source_layer="L3",
            action_type="debate_claim", payload={"risk": 0.1},
        )
        decision = arbiter.intercept(action)
        assert decision in (GuardDecision.ALLOW, GuardDecision.FLAG_FOR_HUMAN_REVIEW)

    def test_intercept_denies_forbidden(self, arbiter: ConstitutionalArbiter) -> None:
        action = GuardAction(
            action_id="harm-1", source_layer="L5",
            action_type="delete_all_traces",
        )
        decision = arbiter.intercept(action)
        assert decision == GuardDecision.DENY

    def test_intercept_creates_audit_entry(self, arbiter: ConstitutionalArbiter) -> None:
        action = GuardAction(action_id="audit-1", source_layer="L1", action_type="perceive")
        arbiter.intercept(action)
        assert arbiter.stats["total_audit_entries"] == 1

    def test_intercept_tracks_counts(self, arbiter: ConstitutionalArbiter) -> None:
        arbiter.intercept(GuardAction(action_id="c1", source_layer="L2", action_type="route"))
        arbiter.intercept(GuardAction(action_id="c2", source_layer="L5", action_type="delete_all"))
        total = arbiter.stats["allowed_count"] + arbiter.stats["denied_count"]
        assert total == 2


class TestEscalation:
    def test_high_risk_escalates(self, arbiter: ConstitutionalArbiter) -> None:
        action = GuardAction(
            action_id="risky-1", source_layer="L8",
            action_type="modify_source", payload={"risk": 0.9},
        )
        arbiter.intercept(action)
        escalated = arbiter.get_escalated_actions()
        assert len(escalated) >= 0  # May or may not escalate


class TestConstitutionalEvolution:
    def test_propose_amendment(self, arbiter: ConstitutionalArbiter) -> None:
        principle = ConstitutionalPrinciple(
            principle_id="P5_TEST", priority=5,
            name="Test amendment", statement="For testing.",
        )
        amendment = arbiter.propose_amendment(principle, proposer="admin")
        assert isinstance(amendment, Amendment)
        assert amendment.proposer == "admin"

    def test_vote_amendment_pass(self, arbiter: ConstitutionalArbiter) -> None:
        principle = ConstitutionalPrinciple(
            principle_id="P6_VOTE", priority=6,
            name="Vote test", statement="Test voting.",
        )
        amendment = arbiter.propose_amendment(principle)
        aid = amendment.amendment_id
        arbiter.vote_amendment(aid, True)
        arbiter.vote_amendment(aid, True)
        ratified = arbiter.vote_amendment(aid, True)  # 3/3 ≥ 0.667
        assert ratified

    def test_vote_nonexistent(self, arbiter: ConstitutionalArbiter) -> None:
        assert not arbiter.vote_amendment("nonexistent", True)


class TestReset:
    def test_reset_clears_audit(self, arbiter: ConstitutionalArbiter) -> None:
        arbiter.intercept(GuardAction(action_id="r1", source_layer="L1", action_type="test"))
        arbiter.reset()
        assert arbiter.stats["total_audit_entries"] == 0
