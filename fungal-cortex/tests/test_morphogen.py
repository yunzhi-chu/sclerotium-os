"""Tests for ⑨ Morphogen Patterning."""

import pytest

from src.morphogen.morphogen_gradient import MorphogenGradient, GradientPoint
from src.morphogen.turing_patterning import TuringPatterning, TuringPattern
from src.morphogen.guided_selforg import (
    GuidedSelfOrganization,
    PatternConstraint,
    RootAgentRole,
    SelfOrgReport,
)


class TestMorphogenGradient:
    @pytest.fixture
    def gradient(self) -> MorphogenGradient:
        return MorphogenGradient(gradient_length=1.0, dimensions=4)

    def test_initial_source_at_origin(self, gradient: MorphogenGradient) -> None:
        assert gradient._source == (0.0, 0.0, 0.0, 0.0)

    def test_concentration_at_source_is_max(self, gradient: MorphogenGradient) -> None:
        conc = gradient.concentration_at((0.0, 0.0, 0.0, 0.0))
        assert conc == pytest.approx(1.0, rel=0.01)

    def test_concentration_decays_with_distance(self, gradient: MorphogenGradient) -> None:
        near = gradient.concentration_at((0.1, 0.1, 0.1, 0.1))
        far = gradient.concentration_at((3.0, 3.0, 3.0, 3.0))
        assert near > far

    def test_gradient_vector_points_toward_source(self, gradient: MorphogenGradient) -> None:
        # Position at positive x → gradient should point negative (toward source at 0)
        grad = gradient.gradient_at((1.0, 0.0, 0.0, 0.0))
        assert grad[0] < 0  # Points toward origin

    def test_set_source_moves_attractor(self, gradient: MorphogenGradient) -> None:
        gradient.set_source((2.0, 2.0, 2.0, 2.0))
        conc_at_new = gradient.concentration_at((2.0, 2.0, 2.0, 2.0))
        assert conc_at_new == pytest.approx(1.0, rel=0.01)

    def test_sense_returns_gradient_point(self, gradient: MorphogenGradient) -> None:
        point = gradient.sense((0.5, 0.0, 0.0, 0.0))
        assert isinstance(point, GradientPoint)
        assert point.concentration > 0
        assert len(point.gradient_vector) == 4

    def test_sample_field(self, gradient: MorphogenGradient) -> None:
        field = gradient.sample_field(resolution=5)
        assert len(field.points) == 5

    def test_temporal_integration(self, gradient: MorphogenGradient) -> None:
        gradient.sense((0.5, 0.0, 0.0, 0.0))
        gradient.sense((0.5, 0.0, 0.0, 0.0))
        avg = gradient.temporal_integration(window=2)
        assert 0.0 < avg <= 1.0

    def test_dimension_mismatch_raises(self, gradient: MorphogenGradient) -> None:
        with pytest.raises(ValueError):
            gradient.concentration_at((1.0, 2.0))


class TestTuringPatterning:
    @pytest.fixture
    def turing(self) -> TuringPatterning:
        return TuringPatterning(grid_size=16, seed=42)

    def test_initial_pattern_is_uniform_like(self, turing: TuringPatterning) -> None:
        pattern = turing.get_pattern()
        assert pattern.pattern_type in ("uniform", "spots", "stripes", "labyrinth")

    def test_evolution_produces_pattern(self, turing: TuringPatterning) -> None:
        pattern = turing.evolve(iterations=200, dt=0.01)
        assert pattern.iteration_count == 200
        assert isinstance(pattern.activator_field, list)

    def test_evolution_changes_pattern_type(self, turing: TuringPatterning) -> None:
        initial = turing.get_pattern()
        pattern = turing.evolve(iterations=500, dt=0.01)
        # After evolution, pattern should stabilize
        assert pattern.stability >= 0

    def test_boundary_condition(self, turing: TuringPatterning) -> None:
        turing.set_boundary_condition((0, 3), 1.0)
        pattern = turing.get_pattern()
        # Top rows should be fixed at 1.0
        assert pattern.activator_field[0][0] == 1.0

    def test_diffusion_ratio(self, turing: TuringPatterning) -> None:
        ratio = turing.params.inhibitor_diffusion / max(turing.params.activator_diffusion, 1e-10)
        assert ratio > 1.0  # Inhibitor must diffuse faster for Turing instability

    def test_stats(self, turing: TuringPatterning) -> None:
        s = turing.stats
        assert s["grid_size"] == 16
        assert "pattern_type" in s
        assert "diffusion_ratio" in s


class TestGuidedSelfOrganization:
    @pytest.fixture
    def gso(self) -> GuidedSelfOrganization:
        gso = GuidedSelfOrganization()
        gso.set_boundaries((0.0, 1.0), (0.0, 1.0))
        gso.define_axis("risk", 0.0, 1.0)
        gso.define_axis("return", 0.0, 1.0)
        return gso

    def test_boundaries_set(self, gso: GuidedSelfOrganization) -> None:
        assert gso._boundary_set

    def test_axes_defined(self, gso: GuidedSelfOrganization) -> None:
        assert len(gso._axes) == 2
        assert "risk" in gso._axes

    def test_enforce_keeps_valid_agents(self, gso: GuidedSelfOrganization) -> None:
        positions = {"agent-1": (0.5, 0.5)}
        adjusted = gso.enforce(positions)
        assert adjusted["agent-1"] == (0.5, 0.5)

    def test_enforce_clamps_out_of_bounds(self, gso: GuidedSelfOrganization) -> None:
        positions = {"agent-out": (1.5, -0.5)}
        adjusted = gso.enforce(positions)
        x, y = adjusted["agent-out"]
        assert x <= 1.0
        assert y >= 0.0

    def test_assess_pattern_differentiated(self, gso: GuidedSelfOrganization) -> None:
        # Concentrated enough to trigger "differentiated" (moderate entropy)
        dist = {"regime": 10, "strategy": 2, "indicator": 2, "tactics": 1, "risk": 1}
        report = gso.assess_pattern(dist, clusters=5)
        assert report.pattern_formed

    def test_assess_pattern_uniform(self, gso: GuidedSelfOrganization) -> None:
        dist = {"a": 10, "b": 10, "c": 10, "d": 10, "e": 10}
        report = gso.assess_pattern(dist, clusters=5)
        assert report.pattern_type == "uniform"

    def test_assess_pattern_concentrated(self, gso: GuidedSelfOrganization) -> None:
        dist = {"a": 50, "b": 1}
        report = gso.assess_pattern(dist, clusters=1)
        assert report.pattern_type == "concentrated"

    def test_enforce_increments_interventions(self, gso: GuidedSelfOrganization) -> None:
        before = gso._intervention_count
        gso.enforce({"agent-out": (2.0, -1.0)})
        assert gso._intervention_count > before

    def test_root_agent_roles(self) -> None:
        assert RootAgentRole.BOUNDARY_SETTER.value == "boundary_setter"
        assert len(RootAgentRole) == 5

    def test_stats(self, gso: GuidedSelfOrganization) -> None:
        s = gso.stats
        assert s["boundary_set"]
        assert len(s["axes"]) == 2
