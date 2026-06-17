"""Tests for ④ Thermodynamic Engine."""

import math
import pytest

from src.engine.thermodynamic import ThermodynamicEngine, ThermoState
from src.engine.hamiltonian import HamiltonianFlow, ConservativeForce
from src.engine.dissipative import DissipativeFlow, LangevinNoise


class TestHamiltonianFlow:
    def test_initial_state(self) -> None:
        hf = HamiltonianFlow(mass=1.0)
        assert hf.state["position"] == 0.0
        assert hf.state["momentum"] == 0.0

    def test_add_force(self) -> None:
        hf = HamiltonianFlow()
        force = ConservativeForce(
            name="spring",
            potential=lambda x: 0.5 * x ** 2,
            gradient=lambda x: -x,
        )
        hf.add_force(force)
        assert len(hf._forces) == 1

    def test_step_with_spring_force(self) -> None:
        hf = HamiltonianFlow(mass=1.0)
        hf.add_force(ConservativeForce(
            name="spring",
            potential=lambda x: 0.5 * x ** 2,
            gradient=lambda x: -x,
        ))
        hf.set_state(position=1.0, momentum=0.0)
        result = hf.step(dt=0.01)
        assert "position" in result
        assert "total_energy" in result
        # Spring should pull toward origin
        assert result["position"] < 1.0

    def test_energy_conservation_near(self) -> None:
        hf = HamiltonianFlow(mass=1.0, damping=0.0)
        hf.add_force(ConservativeForce(
            name="spring",
            potential=lambda x: 0.5 * x ** 2,
            gradient=lambda x: -x,
        ))
        hf.set_state(position=1.0, momentum=0.0)
        initial_energy = hf.state["energy"]
        energies = []
        for _ in range(100):
            hf.step(dt=0.001)
            energies.append(hf.state["energy"])
        # Energy should be nearly conserved (small drift from symplectic integrator)
        assert max(energies) - min(energies) < 0.1 * abs(initial_energy) + 0.01

    def test_set_state(self) -> None:
        hf = HamiltonianFlow()
        hf.set_state(position=2.0, momentum=3.0)
        assert hf.state["position"] == 2.0
        assert hf.state["momentum"] == 3.0


class TestDissipativeFlow:
    def test_langevin_noise_sample(self) -> None:
        noise = LangevinNoise(amplitude=1.0, temperature=1.0, friction=0.1)
        samples = [noise.sample() for _ in range(100)]
        assert len(samples) == 100
        assert all(isinstance(s, float) for s in samples)

    def test_step_accumulates_entropy(self) -> None:
        df = DissipativeFlow(friction=0.1, temperature=1.0, seed=42)
        for _ in range(10):
            df.step(gradient=1.0)
        assert df.stats["entropy"] > 0

    def test_step_with_increased_temperature(self) -> None:
        df = DissipativeFlow(friction=0.1, temperature=5.0, seed=42)
        df.step(gradient=1.0)
        assert df.stats["temperature"] == 5.0

    def test_set_temperature(self) -> None:
        df = DissipativeFlow(temperature=1.0)
        df.set_temperature(5.0)
        assert df.temperature == 5.0


class TestThermodynamicEngine:
    @pytest.fixture
    def engine(self) -> ThermodynamicEngine:
        return ThermodynamicEngine(
            temperature=1.0,
            noise_scale=0.1,
            dissipation_budget=0.1,
            spectrum_bins=64,
        )

    def test_initial_state(self, engine: ThermodynamicEngine) -> None:
        assert engine.temperature == 1.0
        assert engine.stats["energy"] == 1.0

    def test_step_updates_energy(self, engine: ThermodynamicEngine) -> None:
        initial_energy = engine.stats["energy"]
        engine.step(conservative_force=1.0, noise=0.1)
        assert engine.stats["energy"] != initial_energy

    def test_step_returns_thermo_state(self, engine: ThermodynamicEngine) -> None:
        state = engine.step(conservative_force=0.5, noise=0.0)
        assert isinstance(state, ThermoState)
        assert 0.0 <= state.temperature <= 10.0

    def test_step_accumulates_entropy(self, engine: ThermodynamicEngine) -> None:
        for _ in range(50):
            engine.step(conservative_force=0.5, noise=1.0)
        assert engine.stats["entropy"] > 0

    def test_temperature_adapts_to_market_volatility(self, engine: ThermodynamicEngine) -> None:
        engine.step(conservative_force=0.5, noise=0.0, market_volatility=0.5)
        assert engine.temperature > 1.0  # Higher vol → higher temperature

        engine.step(conservative_force=0.5, noise=0.0, market_volatility=0.01)
        assert engine.temperature < 1.0  # Lower vol → lower temperature

    def test_regime_classification(self, engine: ThermodynamicEngine) -> None:
        state = engine.step(conservative_force=0.1, noise=0.0)
        assert state.regime in ("laminar", "transitional", "turbulent")

    def test_set_temperature_bounded(self, engine: ThermodynamicEngine) -> None:
        engine.set_temperature(100.0)
        assert engine.temperature <= 10.0  # Max clamp

        engine.set_temperature(-1.0)
        assert engine.temperature >= 0.01  # Min clamp

    def test_kolmogorov_exponent_evolves(self, engine: ThermodynamicEngine) -> None:
        # Run many steps to accumulate enough history
        for _ in range(300):
            engine.step(conservative_force=0.1 + _ * 0.001, noise=0.05)
        state = engine.step(conservative_force=0.5, noise=0.0)
        assert isinstance(state.kolmogorov_exponent, float)

    def test_q_budget_controls_exploration(self) -> None:
        engine_low = ThermodynamicEngine(dissipation_budget=0.01, noise_scale=1.0, seed=42)
        engine_high = ThermodynamicEngine(dissipation_budget=0.5, noise_scale=1.0, seed=42)

        # Run same number of steps
        for _ in range(100):
            engine_low.step(conservative_force=0.0, noise=1.0)
            engine_high.step(conservative_force=0.0, noise=1.0)

        # High budget → more entropy (more exploration)
        assert engine_high.stats["entropy"] >= engine_low.stats["entropy"]

    def test_stats_comprehensive(self, engine: ThermodynamicEngine) -> None:
        engine.step(conservative_force=0.5, noise=0.1)
        s = engine.stats
        assert "temperature" in s
        assert "energy" in s
        assert "entropy" in s
        assert "kolmogorov_exponent" in s
        assert "regime" in s
