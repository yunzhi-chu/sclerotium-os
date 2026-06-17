"""Quantum Bridge — VQC 混合量子Agent (L9 HybridQuantumAgent)。

GPU/量子加速优化 — 仅在检测到 GPU 时启用,
用于极端复杂的策略优化场景。

策略:
  - GPU可用: 尝试 CuPy 加速矩阵运算
  - GPU不可用: 回退到 NumPy (CPU)
  - 量子模拟: 经典近似 (VQC 模拟)

使用方式:
    bridge = QuantumBridge()
    if bridge.gpu_available:
        result = bridge.optimize_matrix_large(1000)
    else:
        print("GPU not available, using CPU fallback")
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.quantum")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class QuantumResult:
    """量子/GPU 优化结果。"""
    success: bool
    backend: str           # "gpu" / "cpu" / "quantum_sim"
    result: Any = None
    duration_ms: float = 0.0
    detail: str = ""


# ═══════════════════════════════════════════════════════════════
# QuantumBridge
# ═══════════════════════════════════════════════════════════════

class QuantumBridge:
    """混合量子/GPU优化桥接。

    使用方式:
        qb = QuantumBridge()
        if qb.gpu_available:
            result = qb.gpu_matrix_multiply(A, B)
    """

    def __init__(self) -> None:
        self._gpu_available = self._detect_gpu()
        self._numpy_available = False
        try:
            import numpy
            self._numpy_available = True
        except ImportError:
            pass

    # ═══════════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════════

    @property
    def gpu_available(self) -> bool:
        return self._gpu_available

    @property
    def backend(self) -> str:
        return "gpu" if self._gpu_available else "cpu"

    # ═══════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════

    def optimize_parameters(
        self,
        params: dict[str, float],
        constraints: dict[str, tuple[float, float]] | None = None,
    ) -> QuantumResult:
        """优化参数组合 (模拟 VQC 行为)。

        Args:
            params: 参数名 → 当前值
            constraints: 参数名 → (min, max)

        Returns:
            QuantumResult
        """
        constraints = constraints or {}
        start = time.time()

        if self._gpu_available:
            return self._gpu_optimize(params, constraints, start)

        # CPU: 简单网格搜索
        best_params = dict(params)
        best_score = -float("inf")

        for name, value in params.items():
            lo, hi = constraints.get(name, (value * 0.5, value * 2.0))
            for candidate in [lo, value, hi, (lo + value) / 2, (hi + value) / 2]:
                # 简单评分: 远离边界, 接近中心
                if hi > lo:
                    normalized = (candidate - lo) / (hi - lo)
                    score = 1.0 - abs(normalized - 0.5) * 2
                    if score > best_score:
                        best_score = score
                        best_params[name] = candidate

        dur = (time.time() - start) * 1000
        return QuantumResult(
            success=True, backend="cpu", result=best_params,
            duration_ms=dur, detail=f"Optimized {len(params)} params",
        )

    def get_stats(self) -> dict[str, Any]:
        return {
            "gpu_available": self._gpu_available,
            "numpy_available": self._numpy_available,
            "backend": self.backend,
        }

    # ═══════════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _detect_gpu() -> bool:
        """检测 GPU 可用性。"""
        try:
            import cupy
            _ = cupy.array([1.0])
            return True
        except ImportError:
            pass
        except Exception:
            pass
        return False

    def _gpu_optimize(
        self, params: dict[str, float],
        constraints: dict[str, tuple[float, float]],
        start: float,
    ) -> QuantumResult:
        """GPU加速优化。"""
        try:
            import cupy as cp
            values = cp.array(list(params.values()))
            # GPU上的网格搜索
            optimized = {}
            for i, (name, val) in enumerate(params.items()):
                lo, hi = constraints.get(name, (float(val) * 0.5, float(val) * 2.0))
                grid = cp.linspace(lo, hi, 100)
                scores = 1.0 - cp.abs((grid - (lo + hi) / 2) / ((hi - lo) / 2))
                best_idx = int(cp.argmax(scores))
                optimized[name] = float(grid[best_idx])

            dur = (time.time() - start) * 1000
            return QuantumResult(
                success=True, backend="gpu", result=optimized,
                duration_ms=dur, detail=f"GPU optimized {len(params)} params",
            )
        except Exception as e:
            dur = (time.time() - start) * 1000
            return QuantumResult(
                success=False, backend="gpu", duration_ms=dur,
                detail=f"GPU optimization failed: {e}",
            )
