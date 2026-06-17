"""Tests for Mechanism ①: Stigmergy Field PDE system."""

import numpy as np
import pytest

from src.field.field_geometry import FieldGeometry
from src.field.stigmergy_field import StigmergyField


@pytest.fixture
def field() -> StigmergyField:
    geom = FieldGeometry(width=64, height=64)
    return StigmergyField(geometry=geom)


class TestStigmergyField:
    def test_initial_state(self, field: StigmergyField) -> None:
        """Field should start with zero signal and damage, half nutrient."""
        assert np.all(field.S == 0.0)
        assert np.allclose(field.N, 0.5)
        assert np.all(field.D == 0.0)

    def test_step_conserves_bounds(self, field: StigmergyField) -> None:
        """After stepping, field values should stay in [0, 1]."""
        for _ in range(10):
            field.step()
        assert np.all(field.S >= 0.0) and np.all(field.S <= 1.0)
        assert np.all(field.N >= 0.0) and np.all(field.N <= 1.0)
        assert np.all(field.D >= 0.0) and np.all(field.D <= 1.0)

    def test_deposit_signal_increases_local(self, field: StigmergyField) -> None:
        """Depositing signal should increase local signal level."""
        initial = float(np.mean(field.S[30:35, 30:35]))
        field.deposit_signal(32, 32, amount=0.5, radius=2)
        after = float(np.mean(field.S[30:35, 30:35]))
        assert after > initial

    def test_consume_nutrient_decreases_local(self, field: StigmergyField) -> None:
        """Consuming nutrient should decrease local nutrient level."""
        initial = float(np.mean(field.N[30:35, 30:35]))
        field.consume_nutrient(32, 32, amount=0.3, radius=2)
        after = float(np.mean(field.N[30:35, 30:35]))
        assert after < initial

    def test_report_error_increases_damage(self, field: StigmergyField) -> None:
        """Reporting an error should increase local damage."""
        field.report_error(32, 32, error_magnitude=0.8)
        field.step()
        assert float(np.mean(field.D[31:34, 31:34])) > 0.0

    def test_gradient_computation(self, field: StigmergyField) -> None:
        """Gradient should be computable at any valid grid point."""
        field.deposit_signal(32, 32, amount=0.8, radius=3)
        gx, gy = field.gradient_at(32, 32)
        assert isinstance(gx, float)
        assert isinstance(gy, float)

    def test_sense_returns_triple(self, field: StigmergyField) -> None:
        """Agent sensing should return (signal, nutrient, damage) tuple."""
        s, n, d = field.sense(32, 32)
        assert isinstance(s, float)
        assert isinstance(n, float)
        assert isinstance(d, float)
        assert 0.0 <= s <= 1.0
        assert 0.0 <= n <= 1.0
        assert 0.0 <= d <= 1.0

    def test_snapshot_is_deep_copy(self, field: StigmergyField) -> None:
        """Snapshot should not mutate the original field."""
        snap = field.snapshot()
        snap.signal[0, 0] = 999.0
        assert field.S[0, 0] != 999.0

    def test_reset_clears_fields(self, field: StigmergyField) -> None:
        """Reset should return all fields to initial state."""
        field.deposit_signal(32, 32, 0.5)
        field.report_error(32, 32, 0.5)
        field.step()
        field.reset()
        assert np.all(field.S == 0.0)
        assert np.allclose(field.N, 0.5)
        assert np.all(field.D == 0.0)
        assert field.iteration == 0

    def test_mass_conservation_approximate(self, field: StigmergyField) -> None:
        """Total signal mass should not explode after many steps."""
        for _ in range(20):
            field.step()
        assert np.mean(field.S) < 1.0
        assert 0.0 <= np.mean(field.N) <= 1.0
