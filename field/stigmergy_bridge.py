"""Stigmergy Bridge — 信息素场 (PDE反应-扩散-对流, L5)。

黏菌的"集体记忆" — 所有 EventBus 事件映射到空间信息素场。
高频区域=热点, 扩散=时间衰减, 对流=注意力流向。

使用方式:
    field = StigmergyBridge(grid_size=64)
    field.deposit("perception", x=10, y=20, intensity=0.8)
    hotspots = field.get_hotspots(threshold=0.5)

    # 每个 pyloric tick:
    field.diffuse()  # 模拟信息素扩散和蒸发
"""

from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.field")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class FieldPoint:
    """信息素场中的一个点。"""
    x: int
    y: int
    intensity: float              # 0.0–1.0
    category: str = ""            # perception/memory/action/evolution
    age: float = 0.0              # 秒


@dataclass(frozen=True)
class FieldState:
    """信息素场状态快照。"""
    total_intensity: float
    hotspot_count: int
    max_intensity: float
    grid_size: int
    active_cells: int
    dominant_category: str = ""


# ═══════════════════════════════════════════════════════════════
# StigmergyBridge
# ═══════════════════════════════════════════════════════════════

class StigmergyBridge:
    """信息素场 — PDE 反应-扩散-对流模型。

    每个 EventBus 事件 = 信息素沉积
    时间流逝 = 扩散 + 蒸发
    热点 = 需要关注的区域

    使用方式:
        field = StigmergyBridge()
        field.deposit("perception", x=30, y=40, intensity=0.7)
        field.diffuse()
        hotspots = field.get_hotspots()
    """

    def __init__(self, grid_size: int = 64) -> None:
        self._grid_size = grid_size
        self._field: list[list[float]] = [
            [0.0] * grid_size for _ in range(grid_size)
        ]
        self._categories: dict[tuple[int, int], str] = {}
        self._lock = threading.RLock()
        self._total_deposits: int = 0
        self._evaporation_rate: float = 0.05
        self._diffusion_rate: float = 0.1

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def deposit(
        self,
        category: str,
        x: int | None = None,
        y: int | None = None,
        intensity: float = 0.5,
    ) -> None:
        """在指定位置沉积信息素。

        Args:
            category: 类别 (perception/memory/action/evolution)
            x, y: 网格坐标 (None=随机)
            intensity: 沉积强度 (0.0–1.0)
        """
        import random
        if x is None:
            x = random.randint(0, self._grid_size - 1)
        if y is None:
            y = random.randint(0, self._grid_size - 1)
        x = max(0, min(self._grid_size - 1, x))
        y = max(0, min(self._grid_size - 1, y))

        with self._lock:
            self._field[y][x] = min(1.0, self._field[y][x] + intensity)
            self._categories[(x, y)] = category
            self._total_deposits += 1

    def diffuse(self) -> None:
        """执行一次扩散+蒸发步。

        扩散: 每个细胞向8邻域扩散信息素
        蒸发: 所有细胞按蒸发率衰减
        """
        with self._lock:
            new_field = [
                [0.0] * self._grid_size for _ in range(self._grid_size)
            ]
            for y in range(self._grid_size):
                for x in range(self._grid_size):
                    current = self._field[y][x]
                    if current < 0.001:
                        continue
                    # 保留一部分在原地
                    keep = current * (1.0 - self._diffusion_rate)
                    new_field[y][x] += keep
                    # 向8邻域扩散
                    spread = current * self._diffusion_rate / 8.0
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if dx == 0 and dy == 0:
                                continue
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < self._grid_size and 0 <= ny < self._grid_size:
                                new_field[ny][nx] += spread

            # 蒸发
            for y in range(self._grid_size):
                for x in range(self._grid_size):
                    new_field[y][x] *= (1.0 - self._evaporation_rate)
                    self._field[y][x] = min(1.0, new_field[y][x])

    def get_hotspots(self, threshold: float = 0.5, top_n: int = 5) -> list[FieldPoint]:
        """获取信息素热点 (强度超过阈值的区域)。"""
        hotspots: list[FieldPoint] = []
        with self._lock:
            for y in range(self._grid_size):
                for x in range(self._grid_size):
                    if self._field[y][x] >= threshold:
                        hotspots.append(FieldPoint(
                            x=x, y=y,
                            intensity=self._field[y][x],
                            category=self._categories.get((x, y), ""),
                        ))
        hotspots.sort(key=lambda p: p.intensity, reverse=True)
        return hotspots[:top_n]

    def query_point(self, x: int, y: int) -> FieldPoint:
        """查询单个点的信息素强度。"""
        if 0 <= x < self._grid_size and 0 <= y < self._grid_size:
            with self._lock:
                intensity = self._field[y][x]
            return FieldPoint(x=x, y=y, intensity=intensity,
                           category=self._categories.get((x, y), ""))
        return FieldPoint(x=x, y=y, intensity=0.0)

    def get_state(self) -> FieldState:
        """获取当前场状态。"""
        with self._lock:
            total = sum(sum(row) for row in self._field)
            max_val = max(max(row) for row in self._field)
            active = sum(
                1 for row in self._field for v in row if v > 0.01
            )
            # 主导类别
            cat_counts: dict[str, int] = {}
            for (x, y), cat in self._categories.items():
                if self._field[y][x] > 0.1:
                    cat_counts[cat] = cat_counts.get(cat, 0) + 1
            dominant = max(cat_counts, key=cat_counts.get) if cat_counts else ""

        return FieldState(
            total_intensity=round(total, 3),
            hotspot_count=self.get_hotspots().__len__(),
            max_intensity=round(max_val, 3),
            grid_size=self._grid_size,
            active_cells=active,
            dominant_category=dominant,
        )

    def get_stats(self) -> dict[str, Any]:
        state = self.get_state()
        return {
            "grid_size": state.grid_size,
            "total_intensity": state.total_intensity,
            "hotspots": state.hotspot_count,
            "max_intensity": state.max_intensity,
            "active_cells": state.active_cells,
            "dominant": state.dominant_category,
            "total_deposits": self._total_deposits,
        }

    def clear(self) -> None:
        with self._lock:
            self._field = [
                [0.0] * self._grid_size for _ in range(self._grid_size)
            ]
            self._categories.clear()
            self._total_deposits = 0
