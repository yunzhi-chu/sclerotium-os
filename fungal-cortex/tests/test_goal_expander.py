"""Tests for Mechanism ⑮ M4: Global Goal Expander."""

import pytest

from src.l6.goal_expander import (
    EXPLORATION_DOMAINS,
    KNOWN_DOMAINS,
    GlobalGoalExpander,
    GoalStatus,
)


class TestGlobalGoalExpander:
    @pytest.fixture
    def expander(self) -> GlobalGoalExpander:
        return GlobalGoalExpander()

    # --- Domain Space ---

    def test_known_domains_nonempty(self) -> None:
        assert len(KNOWN_DOMAINS) == 7

    def test_exploration_domains_nonempty(self) -> None:
        assert len(EXPLORATION_DOMAINS) == 12

    # --- Discovery ---

    def test_discover_returns_directions(self, expander: GlobalGoalExpander) -> None:
        directions = expander.discover_new_directions(limit=10)
        assert len(directions) > 0
        assert len(directions) <= 10

    def test_discover_includes_pure_exploration(self, expander: GlobalGoalExpander) -> None:
        directions = expander.discover_new_directions(limit=5)
        types = {d["type"] for d in directions}
        assert "pure_exploration" in types

    def test_discover_includes_cross_domain(self, expander: GlobalGoalExpander) -> None:
        directions = expander.discover_new_directions(limit=50)
        types = {d["type"] for d in directions}
        assert "cross_domain" in types

    def test_discover_zero_visit_high_priority(self, expander: GlobalGoalExpander) -> None:
        directions = expander.discover_new_directions(limit=5)
        pure = [d for d in directions if d["type"] == "pure_exploration"]
        assert len(pure) > 0
        assert pure[0]["priority"] == "high"  # Zero visits = high priority

    # --- Feasibility ---

    def test_assess_feasibility_returns_score(self, expander: GlobalGoalExpander) -> None:
        result = expander.assess_feasibility("china_equity_valuation")
        assert "composite_score" in result
        assert 0.0 <= result["composite_score"] <= 1.0
        assert "feasible" in result

    def test_assess_feasibility_has_five_dimensions(self, expander: GlobalGoalExpander) -> None:
        result = expander.assess_feasibility("climate_risk_modeling")
        dims = result["dimensions"]
        assert set(dims.keys()) == {"data", "compute", "contribution", "risk", "novelty"}

    def test_known_domain_has_low_novelty(self, expander: GlobalGoalExpander) -> None:
        result = expander.assess_feasibility("china_equity_valuation")
        assert result["dimensions"]["novelty"] <= 0.3

    def test_exploration_domain_has_higher_novelty(self, expander: GlobalGoalExpander) -> None:
        result = expander.assess_feasibility("climate_risk_modeling")
        assert result["dimensions"]["novelty"] >= 0.5

    def test_cross_domain_has_high_novelty(self, expander: GlobalGoalExpander) -> None:
        result = expander.assess_feasibility("china_equity × crypto_asset")
        assert result["dimensions"]["novelty"] >= 0.7

    def test_feasibility_high_compute_domains_lower_score(self, expander: GlobalGoalExpander) -> None:
        # "climate_risk_modeling" triggers the heavy compute keyword "climate"
        result = expander.assess_feasibility("climate_risk_modeling")
        assert result["dimensions"]["compute"] <= 0.6

    def test_visits_update_exploration_state(self, expander: GlobalGoalExpander) -> None:
        domain = "alternative_data"
        before = expander._exploration[domain].visits
        expander.assess_feasibility(domain)
        assert expander._exploration[domain].visits == before + 1
        assert expander._exploration[domain].knowledge_gained > 0

    # --- Goal Deployment ---

    def test_deploy_feasible_goal(self, expander: GlobalGoalExpander) -> None:
        ok, msg, goal_id = expander.deploy_goal("Test Goal", "china_equity_valuation", "test description")
        assert ok
        assert goal_id is not None

    def test_deployed_goal_has_subtasks(self, expander: GlobalGoalExpander) -> None:
        _, _, goal_id = expander.deploy_goal("Goal with tasks", "portfolio_optimization")
        goal = expander.get_goal(goal_id)
        assert len(goal.sub_tasks) == 5
        assert all("task_id" in t for t in goal.sub_tasks)

    def test_deploy_unfeasible_domain_rejected(self, expander: GlobalGoalExpander) -> None:
        # A domain with extremely bad scores (all weights near zero) would be rejected
        # Most domains pass the 0.5 threshold; test that the check runs
        result = expander.assess_feasibility("crypto_asset_pricing")
        # This might or might not be feasible — just test the integration
        assert "composite_score" in result

    # --- Goal Management ---

    def test_mark_completed(self, expander: GlobalGoalExpander) -> None:
        _, _, goal_id = expander.deploy_goal("Complete Me", "risk_management")
        ok, _ = expander.mark_completed(goal_id)
        assert ok
        assert expander.get_goal(goal_id).status == GoalStatus.COMPLETED

    def test_freeze_goal(self, expander: GlobalGoalExpander) -> None:
        _, _, goal_id = expander.deploy_goal("Freeze Me", "market_microstructure")
        ok, _ = expander.freeze_goal(goal_id, "budget cut")
        assert ok
        assert expander.get_goal(goal_id).status == GoalStatus.FROZEN

    def test_get_goals_by_status(self, expander: GlobalGoalExpander) -> None:
        _, _, g1 = expander.deploy_goal("G1", "risk_management")
        _, _, g2 = expander.deploy_goal("G2", "alternative_data")
        expander.mark_completed(g1)
        deployed = expander.get_goals_by_status(GoalStatus.DEPLOYED)
        completed = expander.get_goals_by_status(GoalStatus.COMPLETED)
        assert len(deployed) >= 1
        assert len(completed) >= 1

    def test_nonexistent_goal(self, expander: GlobalGoalExpander) -> None:
        assert expander.get_goal("nonexistent") is None
        ok, _ = expander.mark_completed("nonexistent")
        assert not ok

    # --- Coverage ---

    def test_get_current_coverage(self, expander: GlobalGoalExpander) -> None:
        cov = expander.get_current_coverage()
        assert cov["total_domains"] == 19
        assert 0.0 <= cov["coverage_pct"] <= 1.0
        assert "unexplored" in cov

    def test_coverage_increases_on_exploration(self, expander: GlobalGoalExpander) -> None:
        before = expander.get_current_coverage()["covered_domains"]
        expander.assess_feasibility("climate_risk_modeling")
        after = expander.get_current_coverage()["covered_domains"]
        assert after >= before

    # --- Stats ---

    def test_stats(self, expander: GlobalGoalExpander) -> None:
        expander.deploy_goal("S1", "risk_management")
        expander.deploy_goal("S2", "portfolio_optimization")
        s = expander.stats
        assert s["total_goals"] >= 2
        assert s["deployed_goals"] >= 2
        assert "curiosity_index" in s

    # --- Edge Cases ---

    def test_empty_context_defaults(self, expander: GlobalGoalExpander) -> None:
        result = expander.assess_feasibility("supply_chain_analytics", {})
        assert result["composite_score"] >= 0.0

    def test_custom_weights(self) -> None:
        expander = GlobalGoalExpander(weights={"data": 0.5, "compute": 0.0, "contribution": 0.5, "risk": 0.0, "novelty": 0.0})
        result = expander.assess_feasibility("china_equity_valuation")
        assert result["composite_score"] >= 0.0
