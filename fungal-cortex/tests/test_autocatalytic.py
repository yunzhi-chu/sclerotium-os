"""Tests for Phase 3 Autocatalytic layer."""
import pytest
from src.autocatalytic.skill_catalysis_graph import SkillCatalysisGraph, CatalysisEdge, RAFSet
from src.autocatalytic.constraint_closure import ConstraintClosure, Constraint, ClosureReport
from src.autocatalytic.phase_transition import PhaseTransition, TransitionState, PhaseMetrics


class TestSkillCatalysisGraph:
    @pytest.fixture
    def graph(self) -> SkillCatalysisGraph:
        return SkillCatalysisGraph()

    def test_add_node(self, graph: SkillCatalysisGraph) -> None:
        assert graph.add_node("skill-A")
        assert graph.node_count == 1

    def test_add_catalysis_auto_adds_nodes(self, graph: SkillCatalysisGraph) -> None:
        assert graph.add_catalysis("A", "B", weight=0.8, evidence="test")
        assert graph.node_count == 2
        assert graph.edge_count == 1

    def test_get_catalysts(self, graph: SkillCatalysisGraph) -> None:
        graph.add_catalysis("A", "C")
        graph.add_catalysis("B", "C")
        catalysts = graph.get_catalysts("C")
        assert "A" in catalysts
        assert "B" in catalysts

    def test_get_catalyzed(self, graph: SkillCatalysisGraph) -> None:
        graph.add_catalysis("A", "B")
        graph.add_catalysis("A", "C")
        catalyzed = graph.get_catalyzed("A")
        assert len(catalyzed) == 2

    def test_remove_catalysis(self, graph: SkillCatalysisGraph) -> None:
        graph.add_catalysis("A", "B")
        assert graph.remove_catalysis("A", "B")
        assert graph.edge_count == 0

    def test_find_catalytic_cycles_simple(self, graph: SkillCatalysisGraph) -> None:
        graph.add_catalysis("A", "B")
        graph.add_catalysis("B", "C")
        graph.add_catalysis("C", "A")  # Forms a cycle
        cycles = graph.find_catalytic_cycles(min_size=2)
        assert len(cycles) >= 1

    def test_find_catalytic_cycles_none(self, graph: SkillCatalysisGraph) -> None:
        graph.add_catalysis("A", "B")
        graph.add_catalysis("B", "C")
        graph.add_catalysis("C", "D")  # Linear chain, no cycle
        cycles = graph.find_catalytic_cycles(min_size=2)
        assert len(cycles) == 0

    def test_find_raf_sets(self, graph: SkillCatalysisGraph) -> None:
        graph.add_catalysis("A", "B")
        graph.add_catalysis("B", "C")
        graph.add_catalysis("C", "A")
        rafs = graph.find_raf_sets(min_size=3)
        assert len(rafs) >= 1
        assert isinstance(rafs[0], RAFSet)

    def test_compute_sustainability(self, graph: SkillCatalysisGraph) -> None:
        graph.add_catalysis("A", "B")
        graph.add_catalysis("B", "A")
        graph.add_catalysis("C", "A")
        sus = graph.compute_sustainability(["A", "B"])
        assert sus == 1.0  # Both catalyze each other

    def test_compute_sustainability_partial(self, graph: SkillCatalysisGraph) -> None:
        graph.add_catalysis("A", "B")
        graph.add_catalysis("B", "C")
        sus = graph.compute_sustainability(["A", "C"])
        assert 0.0 <= sus <= 1.0

    def test_topological_order(self, graph: SkillCatalysisGraph) -> None:
        graph.add_catalysis("A", "B")
        graph.add_catalysis("B", "C")
        order = graph.topological_order()
        assert order.index("A") < order.index("C")

    def test_max_nodes_capacity(self) -> None:
        graph = SkillCatalysisGraph(max_nodes=2)
        assert graph.add_node("A")
        assert graph.add_node("B")
        assert not graph.add_node("C")

    def test_stats(self, graph: SkillCatalysisGraph) -> None:
        graph.add_catalysis("A", "B")
        graph.add_catalysis("B", "C")
        graph.add_catalysis("C", "A")
        s = graph.stats
        assert "catalytic_cycles" in s
        assert "raf_sets" in s


class TestConstraintClosure:
    @pytest.fixture
    def closure(self) -> ConstraintClosure:
        return ConstraintClosure()

    def test_add_constraint(self, closure: ConstraintClosure) -> None:
        c = closure.add_constraint("max_pos", "risk", "strategy", ["risk"])
        assert c.name == "max_pos"
        assert c.source == "strategy"

    def test_check_closure_no_cycles(self, closure: ConstraintClosure) -> None:
        closure.add_constraint("c1", "risk", "strategy", ["risk"])
        report = closure.check_closure()
        assert not report.closure_achieved

    def test_check_closure_with_cycle(self, closure: ConstraintClosure) -> None:
        # strategy → risk → evolution → strategy (full cycle)
        closure.add_constraint("c1", "risk", "strategy", ["risk"])
        closure.add_constraint("c2", "performance", "risk", ["evolution"])
        closure.add_constraint("c3", "compliance", "evolution", ["strategy"])
        report = closure.check_closure()
        assert report.closure_achieved

    def test_remove_constraint(self, closure: ConstraintClosure) -> None:
        closure.add_constraint("c1", "risk", "strategy", ["risk"])
        assert closure.remove_constraint("c1")
        assert not closure.remove_constraint("nonexistent")

    def test_get_domain_constraints(self, closure: ConstraintClosure) -> None:
        closure.add_constraint("c1", "risk", "strategy", ["risk"])
        closure.add_constraint("c2", "capital", "strategy", ["evolution"])
        domain = closure.get_domain_constraints("strategy")
        assert len(domain) == 2

    def test_closure_report_fields(self, closure: ConstraintClosure) -> None:
        closure.add_constraint("c1", "risk", "strategy", ["risk"])
        report = closure.check_closure()
        assert isinstance(report, ClosureReport)
        assert report.total_constraints == 1
        assert report.constraint_graph_density >= 0.0

    def test_inactive_constraints_not_in_cycles(self, closure: ConstraintClosure) -> None:
        c = closure.add_constraint("c1", "risk", "strategy", ["risk"])
        c.active = False
        report = closure.check_closure()
        assert report.active_constraints == 0

    def test_stats(self, closure: ConstraintClosure) -> None:
        closure.add_constraint("c1", "risk", "strategy", ["risk"])
        s = closure.stats
        assert s["total_constraints"] == 1
        assert "closure_achieved" in s


class TestPhaseTransition:
    @pytest.fixture
    def pt(self) -> PhaseTransition:
        return PhaseTransition(n_crit=10)

    def test_initial_state_pre_critical(self, pt: PhaseTransition) -> None:
        assert pt.state == TransitionState.PRE_CRITICAL

    def test_pre_critical_to_critical(self, pt: PhaseTransition) -> None:
        state = pt.evaluate(catalytic_ring_count=6, constraint_closure_loops=0, emergence_rate=0.0, cross_domain_edge_density=0.1)
        assert state == TransitionState.CRITICAL

    def test_critical_to_supercritical(self, pt: PhaseTransition) -> None:
        pt.evaluate(6, 0, 0.0, 0.1)  # → CRITICAL
        state = pt.evaluate(12, 1, 0.5, 0.4)  # → SUPERCRITICAL
        assert state == TransitionState.SUPERCRITICAL

    def test_stay_pre_critical_below_half(self, pt: PhaseTransition) -> None:
        state = pt.evaluate(catalytic_ring_count=3, constraint_closure_loops=0, emergence_rate=0.0, cross_domain_edge_density=0.05)
        assert state == TransitionState.PRE_CRITICAL

    def test_supercritical_to_degenerate(self, pt: PhaseTransition) -> None:
        pt.evaluate(6, 0, 0.0, 0.1)  # → CRITICAL
        pt.evaluate(12, 1, 0.5, 0.4)  # → SUPERCRITICAL
        state = pt.evaluate(2, 0, 0.0, 0.0)  # → DEGENERATE
        assert state == TransitionState.DEGENERATE

    def test_distance_to_critical(self, pt: PhaseTransition) -> None:
        assert pt.distance_to_critical(0) > 0.5
        assert pt.distance_to_critical(5) == 0.5
        assert pt.distance_to_critical(10) == 0.0

    def test_is_autopoietic(self, pt: PhaseTransition) -> None:
        assert not pt.is_autopoietic()
        pt.evaluate(6, 0, 0.0, 0.1)
        pt.evaluate(12, 1, 0.5, 0.4)
        assert pt.is_autopoietic()

    def test_phase_metrics_is_critical(self) -> None:
        pm = PhaseMetrics(catalytic_ring_count=6, constraint_closure_loops=2, emergence_rate=0.1)
        assert pm.is_critical

    def test_phase_metrics_not_critical(self) -> None:
        pm = PhaseMetrics(catalytic_ring_count=2, constraint_closure_loops=0, emergence_rate=0.0)
        assert not pm.is_critical

    def test_stats(self, pt: PhaseTransition) -> None:
        pt.evaluate(6, 0, 0.0, 0.1)
        s = pt.stats
        assert s["state"] == "critical"
        assert "distance_to_critical" in s
        assert "is_autopoietic" in s
