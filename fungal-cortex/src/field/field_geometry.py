"""Field geometry — continuous and discrete grid representations for Stigmergy fields."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np


@dataclass(slots=True)
class FieldGeometry:
    """Defines the spatial domain for Stigmergy fields.

    Supports both 2D discrete grids (for FFT spectral solver) and
    continuous coordinate queries (for agent position mapping).
    """

    width: int = 256
    height: int = 256
    x_range: tuple[float, float] = (0.0, 1.0)
    y_range: tuple[float, float] = (0.0, 1.0)
    mode: Literal["grid", "continuous"] = "grid"

    @property
    def dx(self) -> float:
        """Grid spacing in x direction."""
        return (self.x_range[1] - self.x_range[0]) / self.width

    @property
    def dy(self) -> float:
        """Grid spacing in y direction."""
        return (self.y_range[1] - self.y_range[0]) / self.height

    @property
    def cell_area(self) -> float:
        """Area of a single grid cell."""
        return self.dx * self.dy

    def world_to_grid(self, x: float, y: float) -> tuple[int, int]:
        """Map continuous world coordinates to grid indices."""
        i = int(np.clip((x - self.x_range[0]) / self.dx, 0, self.width - 1))
        j = int(np.clip((y - self.y_range[0]) / self.dy, 0, self.height - 1))
        return i, j

    def grid_to_world(self, i: int, j: int) -> tuple[float, float]:
        """Map grid indices to world coordinates (cell center)."""
        x = self.x_range[0] + (i + 0.5) * self.dx
        y = self.y_range[0] + (j + 0.5) * self.dy
        return x, y

    def create_field(self) -> np.ndarray:
        """Create a zero-initialized field array."""
        return np.zeros((self.width, self.height), dtype=np.float64)

    def create_vector_field(self) -> np.ndarray:
        """Create a zero-initialized 2-component vector field array."""
        return np.zeros((2, self.width, self.height), dtype=np.float64)

    def distance(self, i1: int, j1: int, i2: int, j2: int) -> float:
        """Euclidean distance between two grid cells in world units."""
        x1, y1 = self.grid_to_world(i1, j1)
        x2, y2 = self.grid_to_world(i2, j2)
        return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def neighbors(self, i: int, j: int, radius: int = 1) -> list[tuple[int, int]]:
        """Return grid indices of neighboring cells within radius (von Neumann)."""
        result: list[tuple[int, int]] = []
        for ni in range(max(0, i - radius), min(self.width, i + radius + 1)):
            for nj in range(max(0, j - radius), min(self.height, j + radius + 1)):
                if (ni, nj) != (i, j) and abs(ni - i) + abs(nj - j) <= radius:
                    result.append((ni, nj))
        return result
