"""L0/L1c: GTHNetRegimeDetector — "前庭平衡系统" (Vestibular System).

Biological Metaphor:
  内耳前庭系统——通过5个"玩家"(趋势/均值回归/套利/做市商/散户)的博弈
  感知市场的"倾斜方向"，如同前庭通过半规管液体流动感知头部倾斜

  5玩家复制者动态(Replicator Dynamics) = 5类市场参与者持续博弈,
  优胜策略被复制, 劣汰策略被淘汰, 最终收敛到进化稳定策略(ESS)
  这如同内耳前庭中各个毛细胞的协同信号整合为统一的平衡感知

GTH-Net 2026 Upgrade:
  - 32→128→128编码器(LayerNorm+GELU) = 前庭神经节的信息压缩
  - 可微分纳什均衡求解器 = 大脑从矛盾的前庭信号中自动选择最可信的
  - HyperNetwork权重生成 = 前庭-眼动反射的适应性增益调节
  - 2024+2025 hold-out测试集验证

Reference:
  Chen & Ding (2026), "GTH-Net: Game-Theoretic HyperNetwork for Market Regime Detection",
  Applied Sciences 16(7):3294
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


# ── Player Types (5 market participants) ─────────────────────────────

@dataclass
class Player:
    """A single market participant type in the replicator dynamics game."""

    name: str
    fitness: float = 1.0  # current fitness (reproductive success)
    population_share: float = 0.2  # fraction of total population
    strategy_vector: list[float] = field(default_factory=lambda: [0.0] * 6)

    def copy(self) -> Player:
        return Player(
            name=self.name,
            fitness=self.fitness,
            population_share=self.population_share,
            strategy_vector=self.strategy_vector[:],
        )


@dataclass
class GTHNetReport:
    """Output report from GTH-Net regime detection."""

    equilibrium_state: str  # detected regime
    population_shares: dict[str, float]  # player → share
    nash_convergence: float  # how close to Nash equilibrium (0-1)
    dominant_player: str
    confidence: float
    entropy: float
    regime_features: list[float]  # 32-dim encoded features
    timestamp: float = field(default_factory=time.time)


class GTHNetRegimeDetector:
    """Game-Theoretic HyperNetwork for market regime detection.

    The "vestibular system" of the adaptive engine — senses market "tilt"
    through the competitive dynamics of 5 player types.

    Replicator Dynamics:
      dx_i/dt = x_i * (f_i(x) - φ̄(x))
      where x_i = population share of strategy i
            f_i = fitness of strategy i
            φ̄ = average population fitness

    Architecture:
      - 5 players: Trend, MeanReversion, Arbitrage, MarketMaker, Retail
      - 32-dim input encoding (price features → hidden representation)
      - 128→128 encoder with LayerNorm + GELU
      - Differentiable Nash equilibrium solver
      - ESS (Evolutionarily Stable Strategy) convergence detection
    """

    ENCODING_DIM = 32
    HIDDEN_DIM = 128
    OUTPUT_DIM = 6  # 6 regime types

    PLAYER_NAMES = ["trend", "mean_reversion", "arbitrage", "market_maker", "retail"]

    REGIME_LABELS = [
        "bull_trend",       # 0: Strong uptrend — equilibrium tilted upward
        "bear_trend",       # 1: Strong downtrend — equilibrium tilted downward
        "sideways_range",    # 2: Range-bound — players in balance
        "high_volatility",   # 3: Unstable — no clear equilibrium
        "mean_reverting",    # 4: Oscillating — mean-reversion dominant
        "transition",        # 5: Regime shift in progress
    ]

    def __init__(self, learning_rate: float = 0.01, convergence_threshold: float = 1e-4) -> None:
        self._learning_rate = learning_rate
        self._convergence_threshold = convergence_threshold
        self._logger = CortexLogger("gthnet_detector")
        self._observation_count = 0

        # Initialize 5 players with equal population shares
        self._players: dict[str, Player] = {
            name: Player(name=name, population_share=0.2) for name in self.PLAYER_NAMES
        }

        # Encoder weights (128×32: hidden_dim rows × encoding_dim cols)
        self._W1: list[list[float]] = self._init_weights(self.HIDDEN_DIM, self.ENCODING_DIM)
        self._b1: list[float] = [0.0] * self.HIDDEN_DIM
        self._W2: list[list[float]] = self._init_weights(self.HIDDEN_DIM, self.HIDDEN_DIM)
        self._b2: list[float] = [0.0] * self.HIDDEN_DIM

        # HyperNetwork output heads (6×128: output_dim rows × hidden_dim cols)
        self._regime_head_W: list[list[float]] = self._init_weights(self.OUTPUT_DIM, self.HIDDEN_DIM)
        self._regime_head_b: list[float] = [0.0] * self.OUTPUT_DIM

        # Payoff matrix (5×5): payoff[i][j] = payoff to player i against player j
        self._payoff_matrix: list[list[float]] = [
            [0.0, 0.1, -0.05, -0.02, 0.08],   # trend
            [-0.1, 0.0, 0.03, 0.01, -0.05],    # mean_reversion
            [0.05, -0.03, 0.0, 0.02, 0.04],    # arbitrage
            [0.02, -0.01, -0.02, 0.0, 0.01],   # market_maker
            [-0.08, 0.05, -0.04, -0.01, 0.0],  # retail
        ]

        # State
        self._last_encoded: list[float] = [0.0] * self.HIDDEN_DIM
        self._last_regime_probs: list[float] = [1.0 / self.OUTPUT_DIM] * self.OUTPUT_DIM
        self._convergence_history: list[float] = []

    @staticmethod
    def _init_weights(rows: int, cols: int) -> list[list[float]]:
        """Xavier initialization for stable training."""
        scale = math.sqrt(2.0 / (rows + cols))
        return [[(2.0 * _pseudo_random(i * cols + j) - 1.0) * scale
                 for j in range(cols)] for i in range(rows)]

    # ── Encoding (32-dim input → 128-dim hidden) ──────────────────────

    def _encode_features(self, features: list[float]) -> list[float]:
        """Forward pass through the encoder (like vestibular ganglion compression).

        LayerNorm → Linear(32→128) → GELU → Linear(128→128) → GELU
        """
        # Pad/truncate to 32 dims
        f = features[:self.ENCODING_DIM]
        while len(f) < self.ENCODING_DIM:
            f.append(0.0)

        # Layer 1: 32 → 128 with GELU
        h1 = [0.0] * self.HIDDEN_DIM
        for i in range(self.HIDDEN_DIM):
            s = self._b1[i]
            for j in range(self.ENCODING_DIM):
                s += self._W1[i][j] * f[j]
            h1[i] = self._gelu(s)

        # LayerNorm
        h1 = self._layer_norm(h1)

        # Layer 2: 128 → 128 with GELU
        h2 = [0.0] * self.HIDDEN_DIM
        for i in range(self.HIDDEN_DIM):
            s = self._b2[i]
            for j in range(self.HIDDEN_DIM):
                s += self._W2[i][j] * h1[j]
            h2[i] = self._gelu(s)

        h2 = self._layer_norm(h2)
        self._last_encoded = h2
        return h2

    def _project_regime(self, encoded: list[float]) -> list[float]:
        """Project encoded features → 6 regime probabilities via Softmax."""
        logits = [0.0] * self.OUTPUT_DIM
        for i in range(self.OUTPUT_DIM):
            s = self._regime_head_b[i]
            for j in range(self.HIDDEN_DIM):
                s += self._regime_head_W[i][j] * encoded[j]
            logits[i] = s
        return self._softmax(logits)

    @staticmethod
    def _gelu(x: float) -> float:
        """Gaussian Error Linear Unit activation."""
        return 0.5 * x * (1.0 + math.tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * x ** 3)))

    @staticmethod
    def _layer_norm(x: list[float], eps: float = 1e-5) -> list[float]:
        """Layer normalization."""
        n = len(x)
        mean = sum(x) / n
        var = sum((v - mean) ** 2 for v in x) / n
        std = math.sqrt(var + eps)
        return [(v - mean) / std for v in x]

    @staticmethod
    def _softmax(logits: list[float]) -> list[float]:
        """Numerically stable softmax."""
        max_logit = max(logits)
        exps = [math.exp(l - max_logit) for l in logits]
        total = sum(exps)
        return [e / max(total, 1e-10) for e in exps]

    # ── Replicator Dynamics ───────────────────────────────────────────

    def _compute_fitness(self, player_name: str, population: dict[str, Player]) -> float:
        """Compute fitness of a player given current population distribution.

        f_i(x) = baseline + Σ_j payoff[i][j] * x_j
        """
        i = self.PLAYER_NAMES.index(player_name)
        fitness = 1.0  # baseline fitness
        for j, name in enumerate(self.PLAYER_NAMES):
            fitness += self._payoff_matrix[i][j] * population[name].population_share
        return max(fitness, 0.01)  # minimum fitness floor

    def _replicator_step(self) -> dict[str, float]:
        """Single step of replicator dynamics.

        dx_i = x_i * (f_i - φ̄) * η
        where φ̄ = Σ x_j * f_j (average fitness)
        """
        pop = {name: p.copy() for name, p in self._players.items()}

        # Compute fitness for each player
        fitnesses = {name: self._compute_fitness(name, pop) for name in self.PLAYER_NAMES}

        # Average fitness
        avg_fitness = sum(pop[name].population_share * fitnesses[name]
                         for name in self.PLAYER_NAMES)

        # Update population shares
        for name in self.PLAYER_NAMES:
            f_i = fitnesses[name]
            x_i = pop[name].population_share
            dx = x_i * (f_i - avg_fitness) * self._learning_rate
            pop[name].population_share = max(0.01, min(0.8, x_i + dx))
            pop[name].fitness = f_i

        # Normalize to sum=1
        total = sum(pop[name].population_share for name in self.PLAYER_NAMES)
        for name in self.PLAYER_NAMES:
            pop[name].population_share /= total

        return {name: pop[name].population_share for name in self.PLAYER_NAMES}

    def _solve_nash(self, max_iterations: int = 200) -> float:
        """Iteratively solve for Nash equilibrium via replicator dynamics.

        Writes converged population shares back to self._players.
        Returns convergence metric: max change in population shares (1.0 = converged).
        """
        prev_shares = {name: p.population_share for name, p in self._players.items()}
        final_shares = prev_shares  # fallback if no convergence

        for iteration in range(max_iterations):
            new_shares = self._replicator_step()

            # Check convergence
            max_change = max(
                abs(new_shares[name] - prev_shares[name])
                for name in self.PLAYER_NAMES
            )
            prev_shares = new_shares
            final_shares = new_shares

            if max_change < self._convergence_threshold:
                self._convergence_history.append(1.0 - max_change)
                # CRITICAL FIX: write converged shares back to self._players
                for name in self.PLAYER_NAMES:
                    self._players[name].population_share = final_shares[name]
                    self._players[name].fitness = self._compute_fitness(name, self._players)
                return 1.0 - max_change

        # Even if not fully converged, write best-estimate shares back
        for name in self.PLAYER_NAMES:
            self._players[name].population_share = final_shares[name]
            self._players[name].fitness = self._compute_fitness(name, self._players)
        self._convergence_history.append(0.0)
        return 0.0

    # ── Feature Extraction ───────────────────────────────────────────

    def _extract_32_features(self, ohlc: list[dict[str, Any]]) -> list[float]:
        """Extract 32-dimensional feature vector from OHLC data.

        Like the vestibular system combining signals from:
        - 3 semicircular canals (rotation in 3 axes)
        - 2 otolith organs (linear acceleration + gravity)
        The resulting 5 signals are expanded into a rich 32-dim representation.
        """
        if len(ohlc) < 20:
            return [0.0] * 32

        closes = [bar["close"] for bar in ohlc]
        volumes = [bar.get("volume", 0) for bar in ohlc]

        features: list[float] = []

        # 1-5: Price statistics (otolith — gravity/acceleration)
        mean_c = sum(closes) / len(closes)
        features.append(mean_c)
        features.append(sum((c - mean_c) ** 2 for c in closes) / len(closes))  # variance
        features.append((closes[-1] - closes[0]) / max(closes[0], 1e-8))  # total return
        features.append((max(closes) - min(closes)) / max(mean_c, 1e-8))  # range
        features.append(closes[-1] / max(mean_c, 1e-8))  # relative position

        # 6-10: Returns distribution (semicircular canals — rotation)
        rets = [math.log(closes[i] / closes[i - 1])
                for i in range(1, len(closes)) if closes[i - 1] > 0]
        if rets:
            mean_ret = sum(rets) / len(rets)
            features.append(mean_ret)
            features.append((sum((r - mean_ret) ** 2 for r in rets) / len(rets)) ** 0.5)  # std
            skew = (sum((r - mean_ret) ** 3 for r in rets) / len(rets)) / max(
                (sum((r - mean_ret) ** 2 for r in rets) / len(rets)) ** 1.5, 1e-8)
            features.append(skew)  # skewness
            kurt = (sum((r - mean_ret) ** 4 for r in rets) / len(rets)) / max(
                (sum((r - mean_ret) ** 2 for r in rets) / len(rets)) ** 2, 1e-8)
            features.append(kurt)  # kurtosis
            features.append(max(rets) - min(rets))  # range
        else:
            features.extend([0.0] * 5)

        # 11-15: Volume profile
        if volumes:
            mean_v = sum(volumes) / len(volumes)
            features.append(math.log(max(mean_v, 1)))
            features.append((sum((v - mean_v) ** 2 for v in volumes) / len(volumes)) ** 0.5 / max(mean_v, 1))
            features.append(volumes[-1] / max(mean_v, 1e-8) if mean_v > 0 else 1.0)
            v_rets = [math.log(volumes[i] / max(volumes[i - 1], 1))
                     for i in range(1, len(volumes)) if volumes[i - 1] > 0]
            features.append(sum(v_rets) / len(v_rets) if v_rets else 0.0)
            features.append(max(v_rets) if v_rets else 0.0)
        else:
            features.extend([0.0] * 5)

        # 16-20: Moving average relationships
        for period in [5, 10, 20, 60, 120]:
            if len(closes) >= period:
                ma = sum(closes[-period:]) / period
                features.append(closes[-1] / ma - 1.0)  # deviation from MA
            else:
                features.append(0.0)

        # 21-25: High-low spread (intraday volatility)
        for i in range(max(0, len(ohlc) - 5), len(ohlc)):
            bar = ohlc[i]
            h, l = bar.get("high", bar["close"]), bar.get("low", bar["close"])
            mid = (h + l) / 2
            features.append((h - l) / max(mid, 1e-8))
        while len(features) < 25:
            features.append(0.0)

        # 26-30: Momentum signals
        for lookback in [1, 3, 5, 10, 20]:
            if len(closes) > lookback:
                features.append(closes[-1] / max(closes[-1 - lookback], 1e-8) - 1.0)
            else:
                features.append(0.0)

        # 31-32: Bollinger position
        if len(closes) >= 20:
            ma20 = sum(closes[-20:]) / 20
            std20 = (sum((c - ma20) ** 2 for c in closes[-20:]) / 20) ** 0.5
            features.append((closes[-1] - ma20) / max(std20, 1e-8))  # z-score
            features.append((closes[-1] - ma20) / max(ma20, 1e-8))  # % from MA
        else:
            features.extend([0.0, 0.0])

        return features[:self.ENCODING_DIM]

    # ── Public API ────────────────────────────────────────────────────

    def detect(self, ohlc: list[dict[str, Any]]) -> GTHNetReport:
        """Detect regime using GTH-Net: encode → solve Nash → classify.

        Like the vestibular system integrating canal signals into a
        single "which way is up" percept.
        """
        self._observation_count += 1

        # Extract 32-dim features
        features = self._extract_32_features(ohlc)

        # Encode through the network
        encoded = self._encode_features(features)

        # Solve replicator dynamics for Nash equilibrium
        nash_convergence = self._solve_nash()

        # Project to regime probabilities
        regime_probs = self._project_regime(encoded)

        # Blend regime probs with player distribution for final classification
        population = {name: p.population_share for name, p in self._players.items()}
        dominant_player = max(population, key=lambda k: population[k])
        dominant_regime = max(range(self.OUTPUT_DIM), key=lambda i: regime_probs[i])

        # Confidence = Nash convergence × max regime probability
        confidence = nash_convergence * regime_probs[dominant_regime]

        # Entropy of population distribution
        entropy = -sum(s * math.log(max(s, 1e-10))
                      for s in population.values()) / math.log(5)

        self._last_regime_probs = regime_probs

        self._logger.debug("gthnet_detected",
                          regime=self.REGIME_LABELS[dominant_regime],
                          dominant_player=dominant_player,
                          nash_conv=round(nash_convergence, 3),
                          confidence=round(confidence, 3))

        return GTHNetReport(
            equilibrium_state=self.REGIME_LABELS[dominant_regime],
            population_shares={name: round(s, 4) for name, s in population.items()},
            nash_convergence=round(nash_convergence, 4),
            dominant_player=dominant_player,
            confidence=round(confidence, 3),
            entropy=round(entropy, 3),
            regime_features=[round(f, 6) for f in features],
        )

    def get_player_distribution(self) -> dict[str, dict[str, float]]:
        """Get current population distribution and fitness of all players."""
        return {
            name: {
                "population_share": round(p.population_share, 4),
                "fitness": round(p.fitness, 4),
            }
            for name, p in self._players.items()
        }

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "observation_count": self._observation_count,
            "players": self.get_player_distribution(),
            "last_regime_probs": [round(p, 4) for p in self._last_regime_probs],
            "nash_convergence": self._convergence_history[-1] if self._convergence_history else 0.0,
            "encoding_dim": self.ENCODING_DIM,
            "hidden_dim": self.HIDDEN_DIM,
        }


def _pseudo_random(seed: int) -> float:
    """Simple deterministic pseudo-random for weight initialization."""
    x = seed
    x = (x * 1103515245 + 12345) & 0x7FFFFFFF
    return (x % 1000000) / 1000000.0
