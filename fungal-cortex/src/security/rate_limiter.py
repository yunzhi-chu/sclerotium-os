"""Phase 7.2d: RateLimiter — "肾小球滤过率"(GFR: Glomerular Filtration Rate) 速率限制.

Biological Metaphor:
  肾小球滤过率(GFR)——肾脏持续过滤血液, 但有限速:
    正常GFR≈125mL/min(≈180L/天过滤, 但只排出1-2L尿液)
    血肌酐升高→GFR下降→限速触发
    肾小管重吸收→burst allowance(突发容忍)
    透析→手动重置限速(人工干预)
    慢性肾病分期→分级限速(Stage 1-5)

  滑动窗口算法:
    如同肾脏在任意连续时间窗口内只能处理固定量的血液。
    GFR = 肾脏在单位时间内的最大过滤量。

Reference:
  Levey et al. (2009), "CKD-EPI equation", Annals Internal Medicine 150:604-612;
  Redis sliding window rate limiting patterns
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LimitExceeded(Exception):
    """Raised when a rate limit is exceeded — like elevated creatinine."""
    def __init__(self, key: str, limit: int, window: float, current: int):
        self.key = key
        self.limit = limit
        self.window = window
        self.current = current
        super().__init__(
            f"Rate limit exceeded for '{key}': {current}/{limit} in {window:.1f}s"
        )


class GFRStage(str, Enum):
    """Chronic Kidney Disease stages mapped to rate limit severity."""
    STAGE_1 = "stage_1"  # GFR >= 90 — normal, high limit
    STAGE_2 = "stage_2"  # GFR 60-89 — mildly reduced
    STAGE_3 = "stage_3"  # GFR 30-59 — moderately reduced
    STAGE_4 = "stage_4"  # GFR 15-29 — severely reduced
    STAGE_5 = "stage_5"  # GFR < 15 — kidney failure, strict limit


@dataclass
class SlidingWindow:
    """A single rate limit window — like one nephron's filtration capacity."""

    key: str
    limit: int  # Max requests in the window
    window_seconds: float  # Window duration
    requests: deque[float] = field(default_factory=deque)
    total_allowed: int = 0
    total_blocked: int = 0
    created_at: float = field(default_factory=time.time)


class RateLimiter:
    """Sliding window rate limiter — the kidney's filtration system.

    Config:
      - default_limit: default max requests per window
      - default_window: default window duration in seconds
      - burst_multiplier: burst allowance (like tubular reabsorption)
      - cleanup_interval: seconds between window cleanup cycles
    """

    # GFR stages mapped to limit multipliers
    _GFR_MULTIPLIERS: dict[GFRStage, float] = {
        GFRStage.STAGE_1: 1.0,
        GFRStage.STAGE_2: 0.75,
        GFRStage.STAGE_3: 0.5,
        GFRStage.STAGE_4: 0.25,
        GFRStage.STAGE_5: 0.05,
    }

    def __init__(
        self,
        default_limit: int = 100,
        default_window: float = 60.0,
        burst_multiplier: float = 1.5,
        cleanup_interval: float = 300.0,
    ) -> None:
        self._default_limit = default_limit
        self._default_window = default_window
        self._burst_mult = burst_multiplier
        self._cleanup_interval = cleanup_interval

        self._windows: dict[str, SlidingWindow] = {}
        self._gfr_stage: dict[str, GFRStage] = defaultdict(lambda: GFRStage.STAGE_1)
        self._last_cleanup = time.time()

    # ── Core Rate Limiting ──────────────────────────────────────────

    def check(self, key: str, limit: int | None = None,
              window: float | None = None) -> bool:
        """Check if a request is allowed. Returns True if under limit.

        Like the glomerulus checking if more blood can be filtered.
        """
        self._maybe_cleanup()

        win = self._get_window(key, limit, window)
        now = time.time()

        # Remove expired entries (slide the window)
        cutoff = now - win.window_seconds
        while win.requests and win.requests[0] < cutoff:
            win.requests.popleft()

        # Apply GFR stage multiplier
        stage = self._gfr_stage.get(key, GFRStage.STAGE_1)
        effective_limit = int(win.limit * self._GFR_MULTIPLIERS[stage])

        # Apply burst allowance
        burst_limit = int(effective_limit * self._burst_mult)

        if len(win.requests) < burst_limit:
            win.requests.append(now)
            win.total_allowed += 1
            return True

        win.total_blocked += 1
        return False

    def check_or_raise(self, key: str, limit: int | None = None,
                       window: float | None = None) -> None:
        """Check rate limit, raise LimitExceeded if blocked."""
        win = self._get_window(key, limit, window)
        if not self.check(key, limit, window):
            raise LimitExceeded(key, win.limit, win.window_seconds, len(win.requests))

    # ── GFR Stage Management ────────────────────────────────────────

    def set_gfr_stage(self, key: str, stage: GFRStage) -> None:
        """Set the GFR stage for a key — like diagnosing CKD stage.

        As failures accumulate, the 'kidney function' degrades.
        """
        self._gfr_stage[key] = stage

    def degrade_stage(self, key: str) -> GFRStage:
        """Degrade GFR by one stage — like kidney function declining."""
        current = self._gfr_stage[key]
        stages = list(GFRStage)
        idx = stages.index(current)
        new_idx = min(len(stages) - 1, idx + 1)
        self._gfr_stage[key] = stages[new_idx]
        return stages[new_idx]

    def improve_stage(self, key: str) -> GFRStage:
        """Improve GFR by one stage — like kidney function recovering."""
        current = self._gfr_stage[key]
        stages = list(GFRStage)
        idx = stages.index(current)
        new_idx = max(0, idx - 1)
        self._gfr_stage[key] = stages[new_idx]
        return stages[new_idx]

    def get_gfr_stage(self, key: str) -> GFRStage:
        return self._gfr_stage.get(key, GFRStage.STAGE_1)

    # ── Burst Management ────────────────────────────────────────────

    def allow_burst(self, key: str, count: int = 1) -> bool:
        """Allow a burst of requests — like tubular reabsorption reserve."""
        win = self._get_window(key)
        now = time.time()
        for _ in range(count):
            win.requests.append(now)
            win.total_allowed += 1
        return True

    def reset(self, key: str) -> None:
        """Reset the limiter for a key — like dialysis clearing toxins."""
        if key in self._windows:
            self._windows[key].requests.clear()
        self._gfr_stage[key] = GFRStage.STAGE_1

    # ── Query Interface ─────────────────────────────────────────────

    def get_usage(self, key: str) -> dict[str, Any]:
        """Get current usage statistics for a key."""
        win = self._windows.get(key)
        if win is None:
            return {"current": 0, "limit": self._default_limit, "usage_pct": 0.0}
        now = time.time()
        cutoff = now - win.window_seconds
        current = sum(1 for t in win.requests if t >= cutoff)
        stage = self._gfr_stage.get(key, GFRStage.STAGE_1)
        effective_limit = int(win.limit * self._GFR_MULTIPLIERS[stage])
        return {
            "current": current,
            "limit": effective_limit,
            "raw_limit": win.limit,
            "usage_pct": round(current / max(effective_limit, 1) * 100, 1),
            "gfr_stage": stage.value,
            "total_allowed": win.total_allowed,
            "total_blocked": win.total_blocked,
        }

    # ── Internal ────────────────────────────────────────────────────

    def _get_window(self, key: str, limit: int | None = None,
                    window: float | None = None) -> SlidingWindow:
        if key not in self._windows:
            self._windows[key] = SlidingWindow(
                key=key,
                limit=limit or self._default_limit,
                window_seconds=window or self._default_window,
            )
        return self._windows[key]

    def _maybe_cleanup(self) -> None:
        """Periodic cleanup of expired windows — like shedding old nephrons."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        expired = []
        for key, win in self._windows.items():
            cutoff = now - win.window_seconds * 2
            while win.requests and win.requests[0] < cutoff:
                win.requests.popleft()
            # Remove windows that are empty and haven't been used recently
            if not win.requests and (now - max(win.requests) if win.requests else now - win.created_at) > 3600:
                expired.append(key)
        for key in expired:
            del self._windows[key]

    @property
    def stats(self) -> dict[str, Any]:
        total_allowed = sum(w.total_allowed for w in self._windows.values())
        total_blocked = sum(w.total_blocked for w in self._windows.values())
        return {
            "active_windows": len(self._windows),
            "total_allowed": total_allowed,
            "total_blocked": total_blocked,
            "block_rate": round(total_blocked / max(total_allowed + total_blocked, 1) * 100, 1),
            "gfr_distribution": {
                stage.value: sum(1 for s in self._gfr_stage.values() if s == stage)
                for stage in GFRStage
            },
        }
