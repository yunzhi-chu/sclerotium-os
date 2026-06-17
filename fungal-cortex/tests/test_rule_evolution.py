"""Tests for Mechanism ⑰ M6: Dynamic Rule Evolution."""

import pytest

from src.l6.rule_evolution import (
    RULE_TEMPLATES,
    DynamicRuleEvolutionEngine,
    Rule,
    RuleStatus,
)


class TestRule:
    def test_rule_creation(self) -> None:
        r = Rule(name="test-rule", template_type="position_limit", strategy_id="strat-1")
        assert r.name == "test-rule"
        assert r.status == RuleStatus.DRAFT
        assert r.generation == 0

    def test_clone_for_test(self) -> None:
        r = Rule(name="orig", template_type="stop_loss", strategy_id="s1", parameters={"stop_loss_pct": 0.05})
        r.status = RuleStatus.ACTIVE
        clone = r.clone_for_test()
        assert clone.rule_id != r.rule_id
        assert clone.status == RuleStatus.TESTING
        assert clone.generation == r.generation + 1
        assert clone.parent_rule_id == r.rule_id
        assert clone.parameters == r.parameters


class TestRuleTemplates:
    def test_all_five_templates_exist(self) -> None:
        expected = {"position_limit", "stop_loss", "volatility_trigger", "correlation_trigger", "concentration_limit"}
        assert set(RULE_TEMPLATES.keys()) == expected

    def test_each_template_has_parameters(self) -> None:
        for name, tmpl in RULE_TEMPLATES.items():
            assert "parameters" in tmpl
            assert len(tmpl["parameters"]) > 0
            assert "description" in tmpl


class TestDynamicRuleEvolutionEngine:
    @pytest.fixture
    def engine(self) -> DynamicRuleEvolutionEngine:
        return DynamicRuleEvolutionEngine(
            ab_test_duration_hours=48,
            sharpe_high=2.0,
            sharpe_medium=1.0,
        )

    # --- Rule Generation ---

    def test_generate_rules_for_high_sharpe(self, engine: DynamicRuleEvolutionEngine) -> None:
        rules = engine.generate_rules_for_strategy("strat-high", strategy_sharpe=2.5)
        assert len(rules) == 5
        # High sharpe → looser position limit
        pos_rule = [r for r in rules if r.template_type == "position_limit"][0]
        assert pos_rule.parameters["max_position_pct"] == 0.25

    def test_generate_rules_for_medium_sharpe(self, engine: DynamicRuleEvolutionEngine) -> None:
        rules = engine.generate_rules_for_strategy("strat-med", strategy_sharpe=1.5)
        pos_rule = [r for r in rules if r.template_type == "position_limit"][0]
        assert pos_rule.parameters["max_position_pct"] == 0.15

    def test_generate_rules_for_low_sharpe(self, engine: DynamicRuleEvolutionEngine) -> None:
        rules = engine.generate_rules_for_strategy("strat-low", strategy_sharpe=0.5)
        pos_rule = [r for r in rules if r.template_type == "position_limit"][0]
        assert pos_rule.parameters["max_position_pct"] == 0.08

    def test_generated_rules_are_active(self, engine: DynamicRuleEvolutionEngine) -> None:
        rules = engine.generate_rules_for_strategy("s1", 1.0)
        assert all(r.status == RuleStatus.ACTIVE for r in rules)

    def test_all_five_templates_generated(self, engine: DynamicRuleEvolutionEngine) -> None:
        rules = engine.generate_rules_for_strategy("s2", 1.0)
        templates = {r.template_type for r in rules}
        assert templates == set(RULE_TEMPLATES.keys())

    def test_stop_loss_in_reasonable_range(self, engine: DynamicRuleEvolutionEngine) -> None:
        rules = engine.generate_rules_for_strategy("s3", 1.0)
        stop = [r for r in rules if r.template_type == "stop_loss"][0]
        assert 0.03 <= stop.parameters["stop_loss_pct"] <= 0.15

    # --- Custom Rules ---

    def test_create_custom_rule(self, engine: DynamicRuleEvolutionEngine) -> None:
        ok, msg, rule = engine.create_custom_rule(
            "custom-1", "position_limit", "strat-x", {"max_position_pct": 0.12}
        )
        assert ok
        assert rule is not None
        assert rule.template_type == "position_limit"

    def test_create_custom_rule_bad_template(self, engine: DynamicRuleEvolutionEngine) -> None:
        ok, msg, rule = engine.create_custom_rule("bad", "nonexistent", "s1", {})
        assert not ok

    # --- A/B Testing ---

    def test_ab_test_starts(self, engine: DynamicRuleEvolutionEngine) -> None:
        rules = engine.generate_rules_for_strategy("s-ab", 1.5)
        rule = rules[0]
        ok, msg, test_id = engine.ab_test_rules(rule.rule_id, {"max_position_pct": 0.20})
        assert ok
        assert test_id is not None
        # Original rule should be in TESTING status
        assert engine.get_rule(rule.rule_id).status == RuleStatus.TESTING

    def test_ab_test_nonexistent_rule(self, engine: DynamicRuleEvolutionEngine) -> None:
        ok, msg, test_id = engine.ab_test_rules("nonexistent-id", {})
        assert not ok

    def test_ab_test_non_active_rule(self, engine: DynamicRuleEvolutionEngine) -> None:
        r = Rule(name="draft", template_type="position_limit", strategy_id="s1")
        engine._rules[r.rule_id] = r
        ok, msg, test_id = engine.ab_test_rules(r.rule_id, {})
        assert not ok

    # --- Evaluate & Adopt ---

    def test_evaluate_and_adopt(self, engine: DynamicRuleEvolutionEngine) -> None:
        rules = engine.generate_rules_for_strategy("s-eval", 1.0)
        rule = rules[0]
        _, _, test_id = engine.ab_test_rules(rule.rule_id, {"max_position_pct": 0.18})
        engine.set_test_results(test_id, sharpe_a=1.5, max_dd_a=0.1, sharpe_b=1.2, max_dd_b=0.15)
        ok, msg, winner_id = engine.evaluate_and_adopt(test_id)
        assert ok
        assert winner_id is not None
        # Winner should be ACTIVE
        winner = engine.get_rule(winner_id)
        assert winner.status == RuleStatus.ACTIVE

    def test_evaluate_adopts_better_sharpe(self, engine: DynamicRuleEvolutionEngine) -> None:
        rules = engine.generate_rules_for_strategy("s-best", 1.0)
        rule = rules[0]
        _, _, test_id = engine.ab_test_rules(rule.rule_id, {"max_position_pct": 0.20})
        # Variant B has better sharpe
        engine.set_test_results(test_id, sharpe_a=0.8, max_dd_a=0.2, sharpe_b=2.0, max_dd_b=0.05)
        ok, msg, winner_id = engine.evaluate_and_adopt(test_id)
        assert ok
        # Winner should be variant B
        winner = engine.get_rule(winner_id)
        assert winner.parameters["max_position_pct"] == 0.20

    # --- Rule Management ---

    def test_deprecate_rule(self, engine: DynamicRuleEvolutionEngine) -> None:
        rules = engine.generate_rules_for_strategy("s-dep", 1.0)
        r = rules[0]
        ok, _ = engine.deprecate_rule(r.rule_id, "no longer needed")
        assert ok
        assert engine.get_rule(r.rule_id).status == RuleStatus.DEPRECATED

    def test_get_rules_for_strategy(self, engine: DynamicRuleEvolutionEngine) -> None:
        engine.generate_rules_for_strategy("s-query", 2.0)
        engine.generate_rules_for_strategy("s-other", 1.0)
        rules = engine.get_rules_for_strategy("s-query")
        assert len(rules) == 5
        assert all(r.strategy_id == "s-query" for r in rules)

    def test_get_active_rules(self, engine: DynamicRuleEvolutionEngine) -> None:
        engine.generate_rules_for_strategy("s-act", 1.0)
        active = engine.get_active_rules()
        assert len(active) >= 5

    def test_get_rules_by_template(self, engine: DynamicRuleEvolutionEngine) -> None:
        engine.generate_rules_for_strategy("s-tmpl", 1.0)
        vol_rules = engine.get_rules_by_template("volatility_trigger")
        assert len(vol_rules) >= 1
        assert all(r.template_type == "volatility_trigger" for r in vol_rules)

    # --- Stats & Reports ---

    def test_stats(self, engine: DynamicRuleEvolutionEngine) -> None:
        engine.generate_rules_for_strategy("s-stat", 1.0)
        s = engine.stats
        assert s["total_rules"] >= 5
        assert s["active_rules"] >= 5
        assert s["active_tests"] == 0

    def test_evolution_report(self, engine: DynamicRuleEvolutionEngine) -> None:
        engine.generate_rules_for_strategy("s-report", 1.0)
        report = engine.get_evolution_report()
        assert "total_rules" in report
        assert "recent_events" in report

    def test_event_log_tracks_lifecycle(self, engine: DynamicRuleEvolutionEngine) -> None:
        engine.generate_rules_for_strategy("s-log", 1.0)
        assert len(engine.event_log) >= 5  # One "created" event per rule
        assert engine.event_log[0].event_type == "created"
