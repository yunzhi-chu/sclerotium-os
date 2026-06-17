"""Tests for field_geometry module — grid and continuous field coordinate systems."""

from __future__ import annotations

import numpy as np
import pytest

from src.field.field_geometry import FieldGeometry


class TestFieldGeometry:
    @pytest.fixture
    def geom(self):
        return FieldGeometry(width=256, height=256)

    def test_default_values(self, geom):
        assert geom.width == 256
        assert geom.height == 256
        assert geom.x_range == (0.0, 1.0)
        assert geom.y_range == (0.0, 1.0)
        assert geom.mode == "grid"

    def test_dx_dy(self, geom):
        assert geom.dx == pytest.approx(1.0 / 256)
        assert geom.dy == pytest.approx(1.0 / 256)

    def test_cell_area(self, geom):
        assert geom.cell_area == pytest.approx(geom.dx * geom.dy)

    def test_world_to_grid_origin(self, geom):
        i, j = geom.world_to_grid(0.0, 0.0)
        assert i == 0
        assert j == 0

    def test_world_to_grid_center(self, geom):
        i, j = geom.world_to_grid(0.5, 0.5)
        assert 120 < i < 136  # ~128
        assert 120 < j < 136

    def test_world_to_grid_corner(self, geom):
        i, j = geom.world_to_grid(1.0, 1.0)
        assert i == 255
        assert j == 255

    def test_world_to_grid_clip_outside(self, geom):
        i, j = geom.world_to_grid(2.0, -1.0)
        assert i == 255
        assert j == 0

    def test_grid_to_world(self, geom):
        x, y = geom.grid_to_world(128, 128)
        assert 0.49 < x < 0.52
        assert 0.49 < y < 0.52

    def test_create_field(self, geom):
        field = geom.create_field()
        assert field.shape == (256, 256)
        assert field.dtype == np.float64
        assert np.all(field == 0)

    def test_create_vector_field(self, geom):
        vfield = geom.create_vector_field()
        assert vfield.shape == (2, 256, 256)
        assert vfield.dtype == np.float64
        assert np.all(vfield == 0)

    def test_distance(self, geom):
        d = geom.distance(0, 0, 10, 0)
        assert d > 0.03  # ~10 * dx = 10/256 ≈ 0.039

    def test_distance_same_cell(self, geom):
        d = geom.distance(5, 5, 5, 5)
        assert d == 0.0

    def test_neighbors_radius_one(self, geom):
        nbrs = geom.neighbors(10, 10, radius=1)
        # von Neumann radius 1: 4 neighbors
        assert len(nbrs) == 4

    def test_neighbors_at_corner(self, geom):
        nbrs = geom.neighbors(0, 0, radius=1)
        assert len(nbrs) == 2  # Only right and down

    def test_neighbors_at_edge(self, geom):
        nbrs = geom.neighbors(0, 10, radius=1)
        assert len(nbrs) == 3  # Right, up, down

    def test_neighbors_radius_two(self, geom):
        nbrs = geom.neighbors(50, 50, radius=2)
        # von Neumann radius 2: 12 cells (diamond shape)
        assert len(nbrs) == 12

    def test_neighbors_excludes_self(self, geom):
        nbrs = geom.neighbors(10, 10, radius=2)
        assert (10, 10) not in nbrs

    def test_custom_ranges(self):
        geom = FieldGeometry(width=128, height=64, x_range=(-1.0, 1.0), y_range=(0.0, 2.0))
        assert geom.width == 128
        assert geom.height == 64
        assert geom.dx == pytest.approx(2.0 / 128)
        assert geom.dy == pytest.approx(2.0 / 64)

    def test_continuous_mode(self):
        geom = FieldGeometry(mode="continuous")
        assert geom.mode == "continuous"
