"""Swarm Self-Organizer — 群体自组织器 (Harvard RAnts 外身智能).

Biological Metaphor:
  Termites build 9-meter mounds with precise temperature regulation — without
  blueprints, foremen, or explicit communication. Each termite follows two
  simple rules: (1) deposit soil where pheromone concentration is high,
  (2) avoid areas with CO₂ buildup. From these local rules, global structure
  emerges — exbodied intelligence stored in the environment, not in any
  individual brain.

  Harvard RAnts (Robotectonics, PRX Life 2026) proved this principle with
  robots: two parameters (cooperation_strength × deposition_rate) control
  the entire swarm from construction to dismantling. Flip one parameter,
  and the entire colony switches behavior.

Key Innovation (v4.0):
  Two-parameter phase portrait: cooperation_strength × deposition_rate.
  Four phases: BUILD, PATROL, AGGREGATE, DISMANTLE.
  Single parameter flip triggers global behavior switch.
  Nucleation sites emerge where photormone concentration exceeds threshold.

References:
  - Harvard RAnts (PRX Life 2026): Exbodied Intelligence photormone control
  - Deneubourg et al. (1990): Stigmergy in ant colonies
  - Mycel Network (Zenodo 2026): Swarm phase transitions
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


class SwarmPhase(Enum):
    """Swarm phase determined by the two-parameter portrait.

    BUILD:     High cooperation + High deposition → constructive behavior
    PATROL:    High cooperation + Low deposition  → exploratory behavior
    AGGREGATE: Low cooperation + High deposition → clustering behavior
    DISMANTLE: Low cooperation + Low deposition → destructive behavior
    """
    BUILD = "build"
    PATROL = "patrol"
    AGGREGATE = "aggregate"
    DISMANTLE = "dismantle"
    TRANSITION = "transition"  # Phase change in progress


@dataclass
class PhasePortrait:
    """The two-parameter phase portrait of the swarm.

    cooperation_strength (x-axis):  -1 (competitive) → +1 (cooperative)
    deposition_rate (y-axis):       -1 (remove material) → +1 (deposit material)

    Four quadrants define the swarm's global behavior.
    """

    cooperation_strength: float = 0.5   # ∈ [-1, 1]
    deposition_rate: float = 0.5         # ∈ [-1, 1]
    current_phase: SwarmPhase = SwarmPhase.BUILD
    phase_confidence: float = 0.8
    hysteresis_margin: float = 0.1       # Prevents rapid phase oscillation
    timestamp: float = field(default_factory=time.time)

    def get_phase(self) -> SwarmPhase:
        """Determine phase from cooperation and deposition parameters.

        Phase diagram:
          deposition ↑
          AGGREGATE  │  BUILD
          (-coop,+dep)│  (+coop,+dep)
          ────────────┼────────────→ cooperation
          DISMANTLE  │  PATROL
          (-coop,-dep)│  (+coop,-dep)
        """
        coop = self.cooperation_strength
        dep = self.deposition_rate
        margin = self.hysteresis_margin

        if abs(coop) < margin and abs(dep) < margin:
            return SwarmPhase.TRANSITION

        if coop > margin and dep > margin:
            return SwarmPhase.BUILD
        elif coop > margin and dep < -margin:
            return SwarmPhase.PATROL
        elif coop < -margin and dep > margin:
            return SwarmPhase.AGGREGATE
        elif coop < -margin and dep < -margin:
            return SwarmPhase.DISMANTLE
        else:
            return SwarmPhase.TRANSITION


@dataclass
class NucleationSite:
    """A nucleation site where structure begins to form.

    Like a termite detecting high pheromone concentration and depositing
    the first soil pellet — this is where global structure nucleates.
    """

    site_id: str
    position: tuple[float, float]
    intensity: float = 0.0              # Photormone concentration
    radius: float = 0.05                # Site radius
    age: float = 0.0                    # Time since nucleation
    is_active: bool = True
    deposited_material: float = 0.0     # Accumulated "material" at this site
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PhotormoneField:
    """Digital photormone field for environmental marking.

    Harvard RAnts use light signals (photormones) instead of chemical
    pheromones. The field stores light intensity at each grid point.
    Agents deposit photormones; other agents sense the gradient.
    """

    grid_size: int = 256
    intensity: np.ndarray | None = None
    decay_rate: float = 0.01
    diffusion_rate: float = 0.05

    def __post_init__(self) -> None:
        if self.intensity is None:
            self.intensity = np.zeros((self.grid_size, self.grid_size), dtype=np.float64)

    def deposit(self, x: float, y: float, amount: float, radius: int = 3) -> None:
        """Deposit photormones at a position."""
        if self.intensity is None:
            return
        gx = int(x * self.grid_size) % self.grid_size
        gy = int(y * self.grid_size) % self.grid_size
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                ix = (gx + dx) % self.grid_size
                iy = (gy + dy) % self.grid_size
                dist = math.sqrt(dx**2 + dy**2)
                falloff = max(0.0, 1.0 - dist / (radius + 1))
                self.intensity[ix, iy] = min(1.0, self.intensity[ix, iy] + amount * falloff)

    def sense(self, x: float, y: float, radius: int = 3) -> float:
        """Sense the average photormone concentration at a position."""
        if self.intensity is None:
            return 0.0
        gx = int(x * self.grid_size) % self.grid_size
        gy = int(y * self.grid_size) % self.grid_size
        values = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                ix = (gx + dx) % self.grid_size
                iy = (gy + dy) % self.grid_size
                values.append(self.intensity[ix, iy])
        return float(np.mean(values))

    def gradient_at(self, x: float, y: float) -> tuple[float, float]:
        """Compute the photormone gradient at a position."""
        if self.intensity is None:
            return (0.0, 0.0)
        gx = int(x * self.grid_size) % self.grid_size
        gy = int(y * self.grid_size) % self.grid_size
        right = self.intensity[(gx + 1) % self.grid_size, gy]
        left = self.intensity[(gx - 1) % self.grid_size, gy]
        up = self.intensity[gx, (gy + 1) % self.grid_size]
        down = self.intensity[gx, (gy - 1) % self.grid_size]
        return (float(right - left), float(up - down))

    def step(self) -> None:
        """Advance the photormone field one timestep (decay + diffusion)."""
        if self.intensity is None:
            return
        # Decay
        self.intensity *= (1.0 - self.decay_rate)
        # Simple diffusion (average with neighbors)
        rolled = (
            np.roll(self.intensity, 1, 0) + np.roll(self.intensity, -1, 0) +
            np.roll(self.intensity, 1, 1) + np.roll(self.intensity, -1, 1)
        ) / 4.0
        self.intensity = (1 - self.diffusion_rate) * self.intensity + self.diffusion_rate * rolled
        self.intensity = np.clip(self.intensity, 0.0, 1.0)


@dataclass
class SwarmOrganizerConfig:
    """Configuration for the Swarm Self-Organizer."""

    cooperation_default: float = 0.5
    deposition_default: float = 0.5
    nucleation_threshold: float = 0.7
    phase_hysteresis: float = 0.1
    photormone_decay_rate: float = 0.01
    photormone_diffusion_rate: float = 0.05
    photormone_grid_size: int = 256
    max_nucleation_sites: int = 50


# ═══════════════════════════════════════════════════════════════════════
# Core Organizer
# ═══════════════════════════════════════════════════════════════════════


class SwarmSelfOrganizer:
    """Self-organizing swarm controller with two-parameter phase portrait.

    Inspired by Harvard RAnts: two parameters control the entire swarm's
    global behavior. Intelligence is exbodied — stored in the environment
    (photormone field), not in individual agent brains.

    Usage::

        organizer = SwarmSelfOrganizer()
        phase = organizer.compute_phase_portrait(coop=0.7, dep=0.8)
        site = organizer.nucleate_structure(photormone_field)
        organizer.switch_phase(SwarmPhase.DISMANTLE)
    """

    def __init__(self, config: SwarmOrganizerConfig | None = None) -> None:
        self._config = config or SwarmOrganizerConfig()
        self._logger = CortexLogger("swarm_organizer")

        # Phase state
        self._phase = PhasePortrait(
            cooperation_strength=self._config.cooperation_default,
            deposition_rate=self._config.deposition_default,
            hysteresis_margin=self._config.phase_hysteresis,
        )

        # Photormone field
        self._field = PhotormoneField(
            grid_size=self._config.photormone_grid_size,
            decay_rate=self._config.photormone_decay_rate,
            diffusion_rate=self._config.photormone_diffusion_rate,
        )

        # Nucleation sites
        self._sites: dict[str, NucleationSite] = {}
        self._site_count: int = 0

        # History
        self._phase_history: deque[PhasePortrait] = deque(maxlen=100)
        self._phase_history.append(self._phase)

        self._logger.info("swarm_organizer_initialized",
                          cooperation=self._phase.cooperation_strength,
                          deposition=self._phase.deposition_rate,
                          phase=self._phase.current_phase.value)

    # ── Phase Portrait ────────────────────────────────────────────────

    def compute_phase_portrait(
        self,
        cooperation_strength: float,
        deposition_rate: float,
    ) -> PhasePortrait:
        """Compute the swarm phase from cooperation and deposition parameters.

        The two-parameter phase space determines the entire swarm's behavior:
          BUILD:     Agents construct structures (deposit + cooperate)
          PATROL:    Agents explore/scout (cooperate, don't deposit)
          AGGREGATE: Agents cluster together (deposit, don't cooperate)
          DISMANTLE: Agents break down structures (neither deposit nor cooperate)

        Args:
            cooperation_strength: -1 (competitive) to +1 (cooperative)
            deposition_rate:      -1 (remove) to +1 (deposit)

        Returns:
            PhasePortrait with the determined phase
        """
        coop = max(-1.0, min(1.0, cooperation_strength))
        dep = max(-1.0, min(1.0, deposition_rate))

        phase = PhasePortrait(
            cooperation_strength=coop,
            deposition_rate=dep,
            hysteresis_margin=self._config.phase_hysteresis,
        )
        new_phase = phase.get_phase()

        # Hysteresis: require consecutive consistent readings to switch
        # But always switch if this is the FIRST reading at this target
        if new_phase != self._phase.current_phase:
            recent = list(self._phase_history)[-3:]
            # If we have 2+ recent readings ALSO pointing to the new phase → switch
            recent_new = [r for r in recent if r.current_phase == new_phase]
            if len(recent) < 3 or len(recent_new) >= 2:
                phase.current_phase = new_phase
                phase.phase_confidence = 0.6
                self._logger.info("phase_switched",
                                  old=self._phase.current_phase.value,
                                  new=new_phase.value)
            else:
                # Not enough evidence yet, stick with current
                phase.current_phase = self._phase.current_phase
                phase.phase_confidence = self._phase.phase_confidence
        else:
            phase.current_phase = self._phase.current_phase
            phase.phase_confidence = min(1.0, self._phase.phase_confidence + 0.1)

        self._phase = phase
        self._phase_history.append(phase)

        return phase

    def switch_phase(self, target: SwarmPhase) -> PhasePortrait:
        """Flip parameters to switch the entire swarm to a new phase.

        Single parameter flip triggers global behavior change — just like
        Harvard RAnts flipping one parameter to change from construction
        to dismantling.

        Args:
            target: Desired swarm phase

        Returns:
            New PhasePortrait after the switch
        """
        # Map target phase to (cooperation, deposition) quadrant center
        phase_params = {
            SwarmPhase.BUILD: (0.7, 0.7),
            SwarmPhase.PATROL: (0.7, -0.7),
            SwarmPhase.AGGREGATE: (-0.7, 0.7),
            SwarmPhase.DISMANTLE: (-0.7, -0.7),
        }

        coop, dep = phase_params.get(target, (0.0, 0.0))

        self._logger.info("phase_switch_initiated",
                          target=target.value,
                          cooperation=coop,
                          deposition=dep)

        # Direct switch: bypass hysteresis for explicit phase commands
        phase = PhasePortrait(
            cooperation_strength=coop,
            deposition_rate=dep,
            current_phase=target,
            phase_confidence=1.0,
            hysteresis_margin=self._config.phase_hysteresis,
        )
        self._phase = phase
        self._phase_history.append(phase)

        return phase

    # ── Nucleation ────────────────────────────────────────────────────

    def nucleate_structure(
        self,
        photormone_field: PhotormoneField | None = None,
    ) -> list[NucleationSite]:
        """Detect nucleation sites where structures should form.

        Nucleation occurs where photormone concentration exceeds the
        threshold — analogous to termites beginning to deposit soil at
        high-pheromone locations. These sites become the seeds around
        which larger structures crystallize.

        Args:
            photormone_field: Optional external field (uses internal if None)

        Returns:
            List of newly created nucleation sites
        """
        if photormone_field is None:
            photormone_field = self._field

        threshold = self._config.nucleation_threshold
        new_sites: list[NucleationSite] = []

        if photormone_field.intensity is None:
            return new_sites

        grid = photormone_field.intensity
        gs = photormone_field.grid_size

        # Scan for concentration peaks
        # Use a local maximum detector with minimum separation
        candidates = []
        for i in range(1, gs - 1):
            for j in range(1, gs - 1):
                val = grid[i, j]
                if val < threshold:
                    continue
                # Check if local maximum
                neighbors = [grid[i-1,j], grid[i+1,j], grid[i,j-1], grid[i,j+1]]
                if val > max(neighbors):
                    candidates.append((i, j, float(val)))

        # Sort by intensity, take top candidates
        candidates.sort(key=lambda x: -x[2])
        max_sites = self._config.max_nucleation_sites

        for ci, cj, intensity in candidates[:max_sites]:
            # Check minimum separation from existing sites
            too_close = False
            for existing in self._sites.values():
                ex, ey = existing.position
                dist = math.sqrt(((ci/gs) - ex)**2 + ((cj/gs) - ey)**2)
                if dist < 0.05:  # Minimum 5% grid separation
                    too_close = True
                    break

            if not too_close:
                site_id = f"nucleus-{self._site_count + 1:04d}"
                site = NucleationSite(
                    site_id=site_id,
                    position=(ci / gs, cj / gs),
                    intensity=intensity,
                )
                self._sites[site_id] = site
                new_sites.append(site)
                self._site_count += 1

        if new_sites:
            self._logger.debug("nucleation_detected",
                               new_sites=len(new_sites),
                               total_sites=len(self._sites))

        return new_sites

    def update_sites(self, dt: float = 0.01) -> None:
        """Update nucleation sites: accumulate material or decay."""
        for site in list(self._sites.values()):
            if not site.is_active:
                continue

            # Material accumulation rate depends on local photormone
            local_intensity = self._field.sense(site.position[0], site.position[1])
            if local_intensity > self._config.nucleation_threshold:
                site.deposited_material += local_intensity * dt
            else:
                # Below threshold: decay
                site.deposited_material = max(0.0, site.deposited_material - 0.01 * dt)

            site.age += dt

            # Deactivate if fully decayed
            if site.deposited_material <= 0.0 and site.age > 10.0:
                site.is_active = False

        # Clean up inactive sites
        self._sites = {sid: s for sid, s in self._sites.items() if s.is_active}

    # ── Gradient Navigation ───────────────────────────────────────────

    def gradient_descent(
        self,
        start_position: tuple[float, float],
        photormone_field: PhotormoneField | None = None,
        steps: int = 50,
        learning_rate: float = 0.1,
    ) -> list[tuple[float, float]]:
        """Follow the photormone gradient to find high-concentration areas.

        Like ants following a pheromone trail uphill to the food source.
        In the digital domain, agents follow the photormone gradient to
        find productive work areas.

        Args:
            start_position: Starting (x, y) position
            photormone_field: Field to navigate (uses internal if None)
            steps: Number of gradient descent steps
            learning_rate: Step size

        Returns:
            List of positions along the gradient path
        """
        if photormone_field is None:
            photormone_field = self._field

        path = [start_position]
        x, y = start_position

        for _ in range(steps):
            gx, gy = photormone_field.gradient_at(x, y)
            # Move uphill (gradient ASCENT for photormone concentration)
            x = max(0.0, min(1.0, x + learning_rate * gx))
            y = max(0.0, min(1.0, y + learning_rate * gy))

            if abs(gx) < 1e-6 and abs(gy) < 1e-6:
                break  # Reached stationary point

            path.append((x, y))

        return path

    # ── Photormone Field Access ───────────────────────────────────────

    def mark(self, position: tuple[float, float], intensity: float, radius: int = 3) -> None:
        """Deposit a photormone mark in the environment.

        Like an ant leaving a pheromone trail — other agents will be
        drawn to areas of high concentration.
        """
        self._field.deposit(position[0], position[1], intensity, radius)

    def sense(self, position: tuple[float, float], radius: int = 3) -> float:
        """Sense photormone concentration at a position."""
        return self._field.sense(position[0], position[1], radius)

    def step_field(self) -> None:
        """Advance the photormone field (decay + diffusion)."""
        self._field.step()

    # ── Properties ────────────────────────────────────────────────────

    @property
    def current_phase(self) -> SwarmPhase:
        return self._phase.current_phase

    @property
    def phase_portrait(self) -> PhasePortrait:
        return self._phase

    @property
    def nucleation_sites(self) -> dict[str, NucleationSite]:
        return dict(self._sites)

    @property
    def field(self) -> PhotormoneField:
        return self._field

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "phase": self._phase.current_phase.value,
            "cooperation": round(self._phase.cooperation_strength, 3),
            "deposition": round(self._phase.deposition_rate, 3),
            "phase_confidence": round(self._phase.phase_confidence, 3),
            "nucleation_sites": len(self._sites),
            "active_sites": sum(1 for s in self._sites.values() if s.is_active),
            "field_max_intensity": round(float(np.max(self._field.intensity)), 4)
            if self._field.intensity is not None else 0.0,
            "field_mean_intensity": round(float(np.mean(self._field.intensity)), 4)
            if self._field.intensity is not None else 0.0,
            "phase_history_len": len(self._phase_history),
        }

    def reset(self) -> None:
        """Reset the swarm organizer to initial state."""
        self._phase = PhasePortrait(
            cooperation_strength=self._config.cooperation_default,
            deposition_rate=self._config.deposition_default,
            hysteresis_margin=self._config.phase_hysteresis,
        )
        self._field = PhotormoneField(
            grid_size=self._config.photormone_grid_size,
            decay_rate=self._config.photormone_decay_rate,
            diffusion_rate=self._config.photormone_diffusion_rate,
        )
        self._sites.clear()
        self._site_count = 0
        self._phase_history.clear()
        self._phase_history.append(self._phase)
        self._logger.debug("swarm_organizer_reset")
