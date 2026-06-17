"""Mechanism ①: Stigmergy Field — reaction-diffusion-convection PDE.

Three coupled fields provide the only communication medium between agents:
- Signal field S(x,t): short-term motion guidance (PISC-inspired)
- Nutrient field N(x,t): long-term memory and resource gradient
- Damage field D(x,t): decaying memory of past errors

Agents never communicate directly — they only read/write local field values.
This is the mathematical foundation of the entire Fungal Cortex.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.fft import fft2, fftfreq, ifft2

from src.config import FieldConfig, get_config
from src.field.field_geometry import FieldGeometry
from src.utils.logging import CortexLogger


@dataclass
class FieldSnapshot:
    """A point-in-time snapshot of all three coupled fields."""

    signal: np.ndarray
    nutrient: np.ndarray
    damage: np.ndarray
    timestamp: float = field(default_factory=time.time)
    iteration: int = 0


class StigmergyField:
    r"""Three-field reaction-diffusion-convection system.

    PDE system (Fungal Cortex v2.0):
    ∂S/∂t = D_s ∇²S + α·N·(1-S) - β·S - γ·A·S          (signal: diffusion + growth - decay - consumption)
    ∂N/∂t = D_n ∇²N + δ·(N_max - N) - ε·A·N + ζ·∇·(N·∇S) (nutrient: diffusion + replenish - consume + convection)
    ∂D/∂t = D_d ∇²D - η·D + θ·E                           (damage: diffusion - decay + error deposition)

    Where A is agent density and E is error density on the grid.
    Uses spectral (FFT) method for the diffusion terms and explicit
    finite-difference for reaction/convection terms.
    """

    def __init__(self, geometry: FieldGeometry | None = None, config: FieldConfig | None = None) -> None:
        self.config = config or get_config().field
        self.geom = geometry or FieldGeometry()
        self._logger = CortexLogger("stigmergy_field")

        # Initialize three fields
        self.S: np.ndarray = self.geom.create_field()  # Signal
        self.N: np.ndarray = np.full((self.geom.width, self.geom.height), 0.5, dtype=np.float64)  # Nutrient (init at 50%)
        self.D: np.ndarray = self.geom.create_field()  # Damage
        self._agent_density: np.ndarray = self.geom.create_field()  # Agent presence map
        self._error_density: np.ndarray = self.geom.create_field()  # Error deposition map

        # Pre-compute spectral solver coefficients
        self._precompute_spectral_coeffs()

        self.iteration: int = 0
        self._total_mass: dict[str, float] = {"signal": 0.0, "nutrient": 0.0, "damage": 0.0}

    def _precompute_spectral_coeffs(self) -> None:
        """Pre-compute FFT domain operators for the diffusion terms.

        In Fourier space: ∇²f → -k²·f̂
        Diffusion step in spectral domain: f̂_{t+dt} = f̂_t / (1 + D·k²·dt)
        using the implicit Euler (Crank-Nicolson style) treatment.
        """
        kx = 2.0 * np.pi * fftfreq(self.geom.width, self.geom.dx)
        ky = 2.0 * np.pi * fftfreq(self.geom.height, self.geom.dy)
        KX, KY = np.meshgrid(kx, ky, indexing="ij")
        self._k2 = KX**2 + KY**2

        cfg = self.config
        dt = cfg.dt
        self._diff_op_signal = 1.0 / (1.0 + cfg.diffusion_rate_signal * self._k2 * dt)
        self._diff_op_nutrient = 1.0 / (1.0 + cfg.diffusion_rate_nutrient * self._k2 * dt)
        self._diff_op_damage = 1.0 / (1.0 + cfg.diffusion_rate_damage * self._k2 * dt)

    def step(self, dt: float | None = None, use_gpu: bool = True) -> None:
        """Advance all three fields by one timestep.

        Args:
            dt: Time step override
            use_gpu: If True, attempts GPU acceleration for reaction terms
        """
        if dt is None:
            dt = self.config.dt

        # ── GPU-accelerated reaction path ──────────────────────────
        if use_gpu:
            try:
                from src.field.gpu_accelerator import get_gpu_ops
                gpu = get_gpu_ops(self.geom.width, self.geom.height)
                if gpu.enabled:
                    # GPU reaction + CPU FFT diffusion
                    self.S = gpu.step_signal_reaction(
                        self.S, self.N, self._agent_density,
                        dt, self.config.reaction_rate, self.config.decay_rate,
                    )
                    self.N = gpu.step_nutrient_reaction(
                        self.N, self._agent_density,
                        dt, self.config.decay_rate,
                    )
                    self.D = gpu.step_damage_reaction(
                        self.D, self._error_density, dt,
                    )
                    # Diffusion still on scipy FFT (fast enough for 128x128)
                    self._step_signal_diffusion_only(dt)
                    self._step_nutrient_diffusion_only(dt)
                    self._step_damage_diffusion_only(dt)
                    self.iteration += 1
                    return
            except (ImportError, Exception):
                pass  # Fall back to CPU path

        # ── CPU path (original) ────────────────────────────────────
        self._step_signal(dt)
        self._step_nutrient(dt)
        self._step_damage(dt)

        # Deposit nutrients from agent activity (slow replenish)
        self.N += self.config.decay_rate * self._agent_density * dt
        np.clip(self.N, 0.0, 1.0, out=self.N)

        self.iteration += 1

    # ── Diffusion-only steps (for GPU hybrid path) ────────────────

    def _step_signal_diffusion_only(self, dt: float) -> None:
        """FFT diffusion only — reaction handled by GPU."""
        S_hat = fft2(self.S)
        S_hat = S_hat * self._diff_op_signal
        self.S = np.real(ifft2(S_hat))
        np.clip(self.S, 0.0, 1.0, out=self.S)

    def _step_nutrient_diffusion_only(self, dt: float) -> None:
        """FFT diffusion only — reaction handled by GPU."""
        N_hat = fft2(self.N)
        N_hat = N_hat * self._diff_op_nutrient
        self.N = np.real(ifft2(N_hat))
        np.clip(self.N, 0.0, 1.0, out=self.N)

    def _step_damage_diffusion_only(self, dt: float) -> None:
        """FFT diffusion only — reaction handled by GPU."""
        D_hat = fft2(self.D)
        D_hat = D_hat * self._diff_op_damage
        self.D = np.real(ifft2(D_hat))
        np.clip(self.D, 0.0, 1.0, out=self.D)

    def _step_signal(self, dt: float) -> None:
        """Advance the signal field S."""
        cfg = self.config

        # 1. Diffusion (spectral method)
        S_hat = fft2(self.S)
        S_hat = S_hat * self._diff_op_signal
        S_diffused = np.real(ifft2(S_hat))

        # 2. Reaction: growth term α·N·(1-S), limited by nutrient
        growth = cfg.reaction_rate * self.N * (1.0 - self.S) * dt

        # 3. Decay: -β·S
        decay = cfg.decay_rate * self.S * dt

        # 4. Agent consumption: -γ·A·S
        consumption = 0.2 * self._agent_density * self.S * dt

        self.S = S_diffused + growth - decay - consumption
        np.clip(self.S, 0.0, 1.0, out=self.S)

    def _step_nutrient(self, dt: float) -> None:
        """Advance the nutrient field N with convection."""
        cfg = self.config

        # 1. Diffusion
        N_hat = fft2(self.N)
        N_hat = N_hat * self._diff_op_nutrient
        N_diffused = np.real(ifft2(N_hat))

        # 2. Convection: ζ·∇·(N·∇S) — nutrient flows toward signal gradients
        grad_Sx, grad_Sy = np.gradient(self.S, self.geom.dx, self.geom.dy)
        flux_x = self.N * grad_Sx
        flux_y = self.N * grad_Sy
        div_flux = np.zeros_like(self.N)
        div_flux[1:-1, 1:-1] = (
            (flux_x[2:, 1:-1] - flux_x[:-2, 1:-1]) / (2 * self.geom.dx)
            + (flux_y[1:-1, 2:] - flux_y[1:-1, :-2]) / (2 * self.geom.dy)
        )
        convection = 0.05 * div_flux * dt

        # 3. Agent consumption
        consumption = 0.1 * self._agent_density * self.N * dt

        self.N = N_diffused + convection - consumption
        np.clip(self.N, 0.0, 1.0, out=self.N)

    def _step_damage(self, dt: float) -> None:
        """Advance the damage field D."""
        cfg = self.config

        # 1. Diffusion
        D_hat = fft2(self.D)
        D_hat = D_hat * self._diff_op_damage
        D_diffused = np.real(ifft2(D_hat))

        # 2. Decay: -η·D (damage slowly heals)
        decay = 0.005 * self.D * dt

        # 3. Error deposition: θ·E
        deposition = 0.5 * self._error_density * dt

        self.D = D_diffused - decay + deposition
        np.clip(self.D, 0.0, 1.0, out=self.D)

    # --- Agent-field interaction API ---

    def sense(self, i: int, j: int, radius: int = 3) -> tuple[float, float, float]:
        """Agent reads local field values (signal, nutrient, damage) at its position."""
        i_min, i_max = max(0, i - radius), min(self.geom.width, i + radius + 1)
        j_min, j_max = max(0, j - radius), min(self.geom.height, j + radius + 1)
        s_local = float(np.mean(self.S[i_min:i_max, j_min:j_max]))
        n_local = float(np.mean(self.N[i_min:i_max, j_min:j_max]))
        d_local = float(np.mean(self.D[i_min:i_max, j_min:j_max]))
        return s_local, n_local, d_local

    def deposit_signal(self, i: int, j: int, amount: float, radius: int = 2) -> None:
        """Agent deposits signal (like ant pheromone) at a location."""
        i_min, i_max = max(0, i - radius), min(self.geom.width, i + radius + 1)
        j_min, j_max = max(0, j - radius), min(self.geom.height, j + radius + 1)
        self.S[i_min:i_max, j_min:j_max] += amount

    def consume_nutrient(self, i: int, j: int, amount: float, radius: int = 1) -> None:
        """Agent consumes nutrient from the field."""
        i_min, i_max = max(0, i - radius), min(self.geom.width, i + radius + 1)
        j_min, j_max = max(0, j - radius), min(self.geom.height, j + radius + 1)
        self.N[i_min:i_max, j_min:j_max] -= amount

    def report_error(self, i: int, j: int, error_magnitude: float) -> None:
        """Agent reports an error, depositing on the damage field."""
        self._error_density[i, j] += error_magnitude

    def set_agent_density(self, density: np.ndarray) -> None:
        """Update the agent density map from current agent positions."""
        np.copyto(self._agent_density, density)
        np.clip(self._agent_density, 0.0, 1.0, out=self._agent_density)

    def gradient_at(self, i: int, j: int) -> tuple[float, float]:
        """Compute the signal gradient at a grid point (guides agent movement)."""
        grad_x = (self.S[min(i + 1, self.geom.width - 1), j] - self.S[max(i - 1, 0), j]) / (2 * self.geom.dx)
        grad_y = (self.S[i, min(j + 1, self.geom.height - 1)] - self.S[i, max(j - 1, 0)]) / (2 * self.geom.dy)
        return float(grad_x), float(grad_y)

    def get_field_state(self) -> dict[str, Any]:
        """Return field state as a dict for WebSocket streaming."""
        return {
            "signal": self.S.flatten().tolist()[:100],
            "nutrient": self.N.flatten().tolist()[:100],
            "damage": self.D.flatten().tolist()[:100],
            "temperature": [],
            "agents": [],
        }

    def snapshot(self) -> FieldSnapshot:
        """Take a point-in-time copy of all fields."""
        return FieldSnapshot(
            signal=self.S.copy(),
            nutrient=self.N.copy(),
            damage=self.D.copy(),
            iteration=self.iteration,
        )

    def reset(self) -> None:
        """Reset all fields to initial state."""
        self.S.fill(0.0)
        self.N.fill(0.5)
        self.D.fill(0.0)
        self._agent_density.fill(0.0)
        self._error_density.fill(0.0)
        self.iteration = 0

    @property
    def stats(self) -> dict[str, float]:
        """Aggregate field statistics."""
        return {
            "signal_mean": float(np.mean(self.S)),
            "signal_max": float(np.max(self.S)),
            "nutrient_mean": float(np.mean(self.N)),
            "damage_mean": float(np.mean(self.D)),
            "damage_max": float(np.max(self.D)),
            "iteration": self.iteration,
        }
