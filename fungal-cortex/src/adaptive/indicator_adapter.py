"""L0/L2c: IndicatorAdapter — "肾上腺髓质" (Adrenal Medulla).

Biological Metaphor:
  肾上腺髓质——快速分泌肾上腺素/去甲肾上腺素, 微调心率/血压/血糖

  6体制×(MACD×3+RSI×2+KDJ×3+BOLL×1+MA×3+ATR×1+CCI×1)=14参数
  动态缩放: base*(0.7+0.6*hypernet_output)
  如同肾上腺素在平静时分泌少(参数接近基线), 应激时分泌多(参数大幅偏离)

Reference:
  Yadav & Singh (2025), "HPA axis modeling", Computers in Biology and Medicine
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class IndicatorParameters:
    """Full set of adapted technical indicator parameters."""

    regime_label: str
    # MACD parameters (3)
    macd_fast: int  # fast EMA period (default 12)
    macd_slow: int  # slow EMA period (default 26)
    macd_signal: int  # signal line period (default 9)
    # RSI parameters (2)
    rsi_period: int  # RSI lookback (default 14)
    rsi_oversold: float  # oversold threshold (default 30)
    # KDJ parameters (3)
    kdj_k_period: int  # K period (default 9)
    kdj_d_period: int  # D period (default 3)
    kdj_smooth: int  # J smoothing (default 3)
    # Bollinger parameters (1)
    boll_period: int  # Bollinger lookback (default 20)
    # Moving Average parameters (3)
    ma_5_weight: float  # weight of MA5 signal
    ma_10_weight: float  # weight of MA10 signal
    ma_20_weight: float  # weight of MA20 signal
    # ATR parameters (1)
    atr_period: int  # ATR lookback (default 14)
    # CCI parameters (1)
    cci_period: int  # CCI lookback (default 20)
    # Meta
    adaptation_strength: float  # how much HyperNetwork influenced this
    timestamp: float = field(default_factory=time.time)


class IndicatorAdapter:
    """Regime-aware technical indicator parameter adapter — the "adrenal medulla".

    Adjusts 14 technical indicator parameters based on market regime,
    like adrenaline/epinephrine fine-tuning heart rate, blood pressure,
    and blood glucose in real-time.

    Architecture:
      - 6 regimes × 14 parameter base matrix
      - Dynamic scaling: param = base * (0.7 + 0.6 × hypernetwork_output)
      - Parameter clamping to biologically-plausible ranges
    """

    N_REGIMES = 6
    N_PARAMS = 14

    REGIME_NAMES = [
        "trending_up", "trending_down", "high_volatility",
        "low_volatility", "sideways", "transition",
    ]

    # Parameter indices
    P_MACD_FAST = 0
    P_MACD_SLOW = 1
    P_MACD_SIGNAL = 2
    P_RSI_PERIOD = 3
    P_RSI_OVERSOLD = 4
    P_KDJ_K = 5
    P_KDJ_D = 6
    P_KDJ_SMOOTH = 7
    P_BOLL_PERIOD = 8
    P_MA5_W = 9
    P_MA10_W = 10
    P_MA20_W = 11
    P_ATR_PERIOD = 12
    P_CCI_PERIOD = 13

    PARAM_NAMES = [
        "macd_fast", "macd_slow", "macd_signal",
        "rsi_period", "rsi_oversold",
        "kdj_k_period", "kdj_d_period", "kdj_smooth",
        "boll_period",
        "ma_5_weight", "ma_10_weight", "ma_20_weight",
        "atr_period", "cci_period",
    ]

    def __init__(self) -> None:
        self._logger = CortexLogger("indicator_adapter")

        # Base parameter matrix: 6 regimes × 14 params
        # These are the "resting" parameter values per regime
        self._base_params: list[list[float]] = [
            # trending_up: fast MACD, sensitive RSI, short MA weights
            [8,  21,  7,  10, 25,  7, 3, 2,  15, 0.4, 0.35, 0.25,  10, 14],
            # trending_down: similar to up, more emphasis on momentum
            [8,  21,  7,  10, 35,  7, 3, 2,  15, 0.35, 0.35, 0.3,  10, 14],
            # high_volatility: slower params, wider thresholds
            [16, 32, 12,  18, 22, 12, 4, 3,  25, 0.25, 0.35, 0.4,  18, 24],
            # low_volatility: faster params, tighter thresholds
            [6,  18,  5,   8, 38,  6, 2, 2,  14, 0.45, 0.35, 0.2,  8, 12],
            # sideways: balanced, mean-reversion focused
            [10, 24,  8,  14, 30,  9, 3, 3,  20, 0.3, 0.35, 0.35,  14, 20],
            # transition: adaptive, mid-range
            [12, 26,  9,  14, 28,  9, 3, 2,  20, 0.33, 0.33, 0.34,  14, 18],
        ]

        # Parameter bounds [min, max] for clamping
        self._param_bounds: list[tuple[float, float]] = [
            (4, 24), (12, 40), (3, 15),       # MACD: fast, slow, signal
            (5, 25), (15, 45),                  # RSI: period, oversold
            (5, 15), (2, 6), (1, 5),           # KDJ: k_period, d_period, smooth
            (10, 30),                           # Bollinger: period
            (0.1, 0.6), (0.1, 0.5), (0.1, 0.5),  # MA: 5w, 10w, 20w
            (5, 25), (10, 30),                 # ATR period, CCI period
        ]

        self._last_params: IndicatorParameters | None = None
        self._call_count: int = 0

    # ── Parameter Adaptation ───────────────────────────────────────────

    def adapt(
        self,
        regime_distribution: list[float],
        hypernetwork_scales: list[float] | None = None,
    ) -> IndicatorParameters:
        """Adapt indicator parameters to current regime.

        Args:
            regime_distribution: 6-dim regime probabilities
            hypernetwork_scales: 24-dim sigmoid scales from HyperNetwork (ACTH-like)

        Returns:
            IndicatorParameters with adapted values
        """
        self._call_count += 1

        r = list(regime_distribution[:self.N_REGIMES])
        while len(r) < self.N_REGIMES:
            r.append(0.0)

        # 1. Base parameters: weighted average across regimes
        base = [0.0] * self.N_PARAMS
        for i in range(self.N_PARAMS):
            for j in range(self.N_REGIMES):
                base[i] += r[j] * self._base_params[j][i]

        # 2. HyperNetwork modulation (ACTH → epinephrine release)
        if hypernetwork_scales and len(hypernetwork_scales) >= self.N_PARAMS:
            hn = hypernetwork_scales[:self.N_PARAMS]
        else:
            hn = [0.5] * self.N_PARAMS  # neutral activation

        # Dynamic scaling: param = base * (0.7 + 0.6 × HN_output)
        # HN output ranges 0-1 (sigmoid), so scale factor ranges 0.7-1.3
        adapted = [0.0] * self.N_PARAMS
        for i in range(self.N_PARAMS):
            scale = 0.7 + 0.6 * hn[i]
            adapted[i] = base[i] * scale

        # 3. Clamp to biologically-plausible ranges
        for i in range(self.N_PARAMS):
            lo, hi = self._param_bounds[i]
            adapted[i] = max(lo, min(hi, adapted[i]))

        # 4. Round integer parameters
        int_params = {self.P_MACD_FAST, self.P_MACD_SLOW, self.P_MACD_SIGNAL,
                      self.P_RSI_PERIOD, self.P_KDJ_K, self.P_KDJ_D, self.P_KDJ_SMOOTH,
                      self.P_BOLL_PERIOD, self.P_ATR_PERIOD, self.P_CCI_PERIOD}
        for i in int_params:
            adapted[i] = round(adapted[i])

        # 5. Adaptation strength
        if hypernetwork_scales:
            adapt_strength = sum(abs(s - 0.5) for s in hypernetwork_scales[:self.N_PARAMS]) / self.N_PARAMS * 2
        else:
            adapt_strength = 0.0

        params = IndicatorParameters(
            regime_label=self._dominant_regime(r),
            macd_fast=int(adapted[self.P_MACD_FAST]),
            macd_slow=int(adapted[self.P_MACD_SLOW]),
            macd_signal=int(adapted[self.P_MACD_SIGNAL]),
            rsi_period=int(adapted[self.P_RSI_PERIOD]),
            rsi_oversold=round(adapted[self.P_RSI_OVERSOLD], 1),
            kdj_k_period=int(adapted[self.P_KDJ_K]),
            kdj_d_period=int(adapted[self.P_KDJ_D]),
            kdj_smooth=int(adapted[self.P_KDJ_SMOOTH]),
            boll_period=int(adapted[self.P_BOLL_PERIOD]),
            ma_5_weight=round(adapted[self.P_MA5_W], 3),
            ma_10_weight=round(adapted[self.P_MA10_W], 3),
            ma_20_weight=round(adapted[self.P_MA20_W], 3),
            atr_period=int(adapted[self.P_ATR_PERIOD]),
            cci_period=int(adapted[self.P_CCI_PERIOD]),
            adaptation_strength=round(adapt_strength, 3),
        )
        self._last_params = params

        self._logger.debug("indicator_adapted",
                          regime=params.regime_label,
                          adapt_strength=round(adapt_strength, 3),
                          macd_fast=params.macd_fast,
                          rsi_period=params.rsi_period)

        return params

    def get_params_dict(self) -> dict[str, Any]:
        """Get last adapted parameters as a dict for downstream use."""
        if self._last_params is None:
            return {}
        return {
            "macd": {
                "fast": self._last_params.macd_fast,
                "slow": self._last_params.macd_slow,
                "signal": self._last_params.macd_signal,
            },
            "rsi": {
                "period": self._last_params.rsi_period,
                "oversold": self._last_params.rsi_oversold,
            },
            "kdj": {
                "k_period": self._last_params.kdj_k_period,
                "d_period": self._last_params.kdj_d_period,
                "smooth": self._last_params.kdj_smooth,
            },
            "bollinger": {"period": self._last_params.boll_period},
            "ma_weights": {
                "ma5": self._last_params.ma_5_weight,
                "ma10": self._last_params.ma_10_weight,
                "ma20": self._last_params.ma_20_weight,
            },
            "atr": {"period": self._last_params.atr_period},
            "cci": {"period": self._last_params.cci_period},
            "adaptation_strength": self._last_params.adaptation_strength,
        }

    @staticmethod
    def _dominant_regime(regime_dist: list[float]) -> str:
        idx = max(range(len(regime_dist)), key=lambda i: regime_dist[i])
        return IndicatorAdapter.REGIME_NAMES[idx] if idx < len(IndicatorAdapter.REGIME_NAMES) else "unknown"

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "call_count": self._call_count,
            "n_regimes": self.N_REGIMES,
            "n_params": self.N_PARAMS,
            "param_names": self.PARAM_NAMES,
            "last_params": self.get_params_dict() if self._last_params else None,
        }
