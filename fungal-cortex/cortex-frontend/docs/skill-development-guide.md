# Fungal Cortex v2.0 -- Skill Development Guide

> **Creating, testing, and publishing Skills for the L6 framework**

---

## 1. Skill Lifecycle

Every Skill in Fungal Cortex follows a 5-stage lifecycle aligned with the bio-inspired mechanisms:

```
  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │  CREATE   │──►│ VALIDATE │──►│ SANDBOX  │──►│  DEPLOY  │──►│  EVOLVE  │
  │           │    │           │    │  (⑭)    │    │          │    │  (⑩)    │
  │  Author   │    │  Schema  │    │ Isolated │    │  Active  │    │  Rule-   │
  │  draft    │    │  check   │    │  runtime │    │  in reg. │    │  driven  │
  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
        │               │               │               │               │
        │          ┌────▼────┐    ┌────▼────┐          │          ┌────▼────┐
        │          │  Fix    │    │  Fix    │          │          │  Retire │
        └──────────►  errors │    │  errors │          │          │  or     │
                   └─────────┘    └─────────┘          │          │  mutate │
                                                        └──────────┴─────────┘
```

### Stage Details

1. **CREATE** -- Write the Skill code, define its DNA vector, and register metadata.
2. **VALIDATE** -- Schema checks pass: DNA bounds, parameter types, dependency resolution.
3. **SANDBOX (⑭)** -- The Skill runs in an isolated sandbox against historical data. All I/O is mocked. Results are compared against expected outputs.
4. **DEPLOY** -- The Skill is published to the Skill Registry and becomes available to the pipeline.
5. **EVOLVE (⑩)** -- Dynamic Rule Evolution (M6) may mutate the Skill's parameters or DNA over time based on performance.

---

## 2. Skill DNA Vector

Every Skill has a 6-dimensional DNA vector encoding its innate characteristics. Each dimension is a float in `[0.0, 1.0]`.

| Index | Dimension | Meaning | Low (0.0) | High (1.0) |
|-------|-----------|---------|------------|------------|
| 0 | **Speed** | Execution priority | Batch, slow | Realtime, fast |
| 1 | **Risk** | Risk tolerance | Conservative | Aggressive |
| 2 | **Complexity** | Computational cost | Lightweight | Heavy |
| 3 | **Adaptivity** | Parameter sensitivity | Static | Dynamic |
| 4 | **Novelty** | Exploration vs exploitation | Exploit | Explore |
| 5 | **Scope** | Market breadth | Single asset | Multi-asset |

**Example -- MA Crossover Strategy:**

```
dna = [0.85, 0.42, 0.13, 0.67, 0.91, 0.34]
       │     │     │     │     │     │
       │     │     │     │     │     └─ Scope: mostly focused on few assets
       │     │     │     │     └─────── Novelty: strongly exploratory
       │     │     │     └───────────── Adaptivity: moderately adaptive
       │     │     └─────────────────── Complexity: lightweight
       │     └───────────────────────── Risk: moderately conservative
       └─────────────────────────────── Speed: near-realtime
```

**Validation rules:**

- Each dimension must be in `[0.0, 1.0]`.
- The vector must have exactly 6 elements.
- At least 2 dimensions must differ from `0.5` by more than `0.1` (to avoid uniform "gray goo" skills).

---

## 3. Skill File Structure

```
skills/
└── <module>/
    └── <skill-name>/
        ├── __init__.py        # Skill registration, metadata
        ├── skill.py           # Core implementation
        ├── config.py          # Parameters, defaults, constraints
        ├── schema.py          # I/O schema (input/output types)
        ├── test_skill.py      # Unit tests
        └── spec.yaml          # DNA, dependencies, metadata
```

### Directory Conventions

| Field | Convention |
|-------|-----------|
| Module directory | `strategy/`, `indicator/`, `risk/`, `research/`, `analysis/`, `trading/`, `agent/` |
| Skill directory | Lowercase kebab-case (e.g., `ma-crossover/`) |
| Python files | `skill.py`, `config.py`, `schema.py` |
| Tests | `test_skill.py` with pytest |
| Metadata | `spec.yaml` in YAML format |

---

## 4. Creating a Strategy Skill

Let us walk through creating a simple mean-reversion strategy skill.

### Step 1: Create the directory structure

```
skills/strategy/mean-reversion/
├── __init__.py
├── skill.py
├── config.py
├── schema.py
├── test_skill.py
└── spec.yaml
```

### Step 2: Define `spec.yaml`

```yaml
id: strat-mean-reversion
name: Mean Reversion Strategy
description: >
  Identifies overbought/oversold conditions using z-score
  deviation from a rolling mean. Enters mean-reversion
  positions when price exceeds N standard deviations.
version: 1.0.0
module: strategy
author: "Cortex Dev"
dna: [0.6, 0.3, 0.2, 0.5, 0.4, 0.3]

dependencies:
  - indicator-sma
  - indicator-bollinger

parameters:
  window:
    type: int
    default: 20
    min: 5
    max: 100
    description: Rolling window for mean calculation
  entry_z:
    type: float
    default: 2.0
    min: 1.0
    max: 3.0
    description: Z-score threshold for entry
  exit_z:
    type: float
    default: 0.5
    min: 0.1
    max: 1.5
    description: Z-score threshold for exit

asset_classes: [equity, crypto]
risk_level: medium
```

### Step 3: Implement `skill.py`

```python
"""Mean Reversion Strategy Skill."""
from typing import Optional
import numpy as np
from cortex.sdk import BaseSkill, Signal, MarketData


class MeanReversionSkill(BaseSkill):
    """Mean reversion strategy based on z-score deviation."""

    async def generate_signal(
        self,
        data: MarketData,
        window: int = 20,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
    ) -> Optional[Signal]:
        """Generate a trading signal based on mean reversion.

        Args:
            data: Current market data window.
            window: Rolling window size.
            entry_z: Z-score threshold to enter.
            exit_z: Z-score threshold to exit.

        Returns:
            Signal if conditions met, None otherwise.
        """
        prices = data.close[-window:]
        if len(prices) < window:
            return None

        mean = np.mean(prices)
        std = np.std(prices)

        if std == 0:
            return None

        current_price = data.close[-1]
        z_score = (current_price - mean) / std

        # Check for position entry
        if z_score > entry_z:
            return Signal(
                action="sell",
                confidence=min(1.0, (z_score - entry_z) / 0.5),
                reason=f"Overbought (z={z_score:.2f})",
                metadata={"z_score": float(z_score), "window": window},
            )
        elif z_score < -entry_z:
            return Signal(
                action="buy",
                confidence=min(1.0, (-z_score - entry_z) / 0.5),
                reason=f"Oversold (z={z_score:.2f})",
                metadata={"z_score": float(z_score), "window": window},
            )

        return None

    async def should_exit(
        self,
        position,
        data: MarketData,
        window: int = 20,
        exit_z: float = 0.5,
    ) -> bool:
        """Check if position should be exited."""
        prices = data.close[-window:]
        if len(prices) < window:
            return False

        mean = np.mean(prices)
        std = np.std(prices)

        if std == 0:
            return False

        current_price = data.close[-1]
        z_score = abs((current_price - mean) / std)

        return z_score < exit_z
```

### Step 4: Define `config.py`

```python
from dataclasses import dataclass, field
from typing import List


@dataclass
class MeanReversionConfig:
    """Configuration for Mean Reversion strategy."""

    window: int = 20
    entry_z: float = 2.0
    exit_z: float = 0.5
    asset_classes: List[str] = field(default_factory=lambda: ["equity", "crypto"])
    max_position_size: float = 0.1
    stop_loss_pct: float = 0.02
```

### Step 5: Define `schema.py`

```python
from pydantic import BaseModel, Field
from typing import Optional


class MeanReversionInput(BaseModel):
    """Input schema for mean reversion strategy."""
    symbol: str
    window: int = Field(default=20, ge=5, le=100)
    entry_z: float = Field(default=2.0, ge=1.0, le=3.0)
    exit_z: float = Field(default=0.5, ge=0.1, le=1.5)


class MeanReversionOutput(BaseModel):
    """Output schema for mean reversion strategy."""
    signal: Optional[str] = None  # "buy", "sell", or None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    reason: Optional[str] = None
    z_score: Optional[float] = None
```

---

## 5. Creating an Indicator Skill (with TDX Formula)

Indicators are simpler than strategies -- they transform data rather than generate signals.

### Example: TDX-Style RSI Indicator

```python
"""RSI Indicator Skill with TDX formula compatibility."""
import numpy as np
from cortex.sdk import BaseIndicator


class RSIIndicator(BaseIndicator):
    """Relative Strength Index indicator.

    TDX formula equivalent:
        LC := REF(CLOSE,1);
        RSI:SMA(MAX(CLOSE-LC,0),N,1)/SMA(ABS(CLOSE-LC),N,1)*100;
    """

    name = "RSI"
    version = "1.0.0"
    dna = [0.9, 0.1, 0.05, 0.3, 0.2, 0.1]

    async def compute(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Compute RSI over price series.

        Args:
            prices: Array of closing prices.
            period: RSI period (default 14).

        Returns:
            Array of RSI values (same length as input).
        """
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        avg_gain = np.zeros_like(prices)
        avg_loss = np.zeros_like(prices)

        # Wilder smoothing (equivalent to SMA(..., N, 1) in TDX)
        avg_gain[period] = np.mean(gains[:period])
        avg_loss[period] = np.mean(losses[:period])

        for i in range(period + 1, len(prices)):
            avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
            avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period

        rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss != 0)
        rsi = 100 - (100 / (1 + rs))

        return rsi
```

**spec.yaml for the indicator:**

```yaml
id: indicator-rsi
name: RSI Indicator
description: Relative Strength Index with Wilder smoothing
version: 1.0.0
module: indicator
dna: [0.9, 0.1, 0.05, 0.3, 0.2, 0.1]
dependencies: []
parameters:
  period:
    type: int
    default: 14
    min: 2
    max: 100
tdx_formula: "RSI:SMA(MAX(CLOSE-LC,0),N,1)/SMA(ABS(CLOSE-LC),N,1)*100;"
```

---

## 6. Sandbox Verification Pipeline (Mechanism ⑭)

Every Skill must pass the sandbox pipeline before deployment. The sandbox runs the Skill in an isolated container with mocked dependencies.

```
  spec.yaml ──► validate_schema()
                    │
  skill.py ────► lint_check() ──► type_check()
                    │
  test_skill.py ──► run_tests()
                    │
               ┌───▼───┐
               │ MOCK   │
               │ ENGINE │──► historical_data_feed()
               └───┬───┘    ├── execute_skill()
                    │        └── record_outputs()
                    │
               ┌───▼────┐
               │ VERIFY  │──► output_schema_check()
               │         │──► performance_check()
               └───┬────┘    ├── dna_congruence_check()
                    │         └── safety_check()
                    │
               ┌───▼────┐
               │ REPORT  │──► pass / fail / warn
               └────────┘
```

### Sandbox CLI

```bash
# Validate a skill
cortex skill validate skills/strategy/mean-reversion/

# Run sandbox tests
cortex skill sandbox skills/strategy/mean-reversion/ \
    --data historical/btc_usd_1h_2025.parquet \
    --timeout 60

# Full pipeline (validate + sandbox + deploy)
cortex skill deploy skills/strategy/mean-reversion/ \
    --env sandbox \
    --approve
```

### What the sandbox checks:

| Check | What It Tests | Fail Condition |
|-------|--------------|----------------|
| Schema validation | spec.yaml structure and bounds | Missing field, out-of-range DNA |
| Lint | PEP 8 compliance | PyLint score < 8.0 |
| Type check | mypy strict mode | Any type violation |
| Unit tests | pytest run | Any test failure |
| Historical run | Skill execution on 6 months data | Runtime error |
| Output schema | Result matches schema.py | Type mismatch |
| Performance | Latency and memory | > 500ms or > 256MB |
| DNA congruence | Behavior matches DNA profile | Divergence > 0.3 |
| Safety | No side effects, no I/O | File write, network call |

---

## 7. Testing Skills

### Unit Tests (`test_skill.py`)

```python
import pytest
import numpy as np
from skills.strategy.mean_reversion.skill import MeanReversionSkill
from cortex.sdk import MarketData, Signal


@pytest.fixture
def skill():
    return MeanReversionSkill()


@pytest.fixture
def normal_market():
    """Normal market data -- no signal expected."""
    prices = np.linspace(100, 105, 30) + np.random.normal(0, 1, 30)
    return MarketData(
        symbol="BTC/USD",
        close=prices,
        timestamp="2026-06-12T00:00:00Z",
    )


@pytest.fixture
def overbought_market():
    """Overbought market -- sell signal expected."""
    prices = np.array([100, 102, 105, 110, 120, 130, 135, 132, 128,
                       125, 122, 118, 115, 112, 110, 108, 107, 106,
                       105, 104, 103, 102, 101, 100, 99, 98, 97, 96, 95, 94])
    return MarketData(
        symbol="BTC/USD",
        close=prices,
        timestamp="2026-06-12T00:00:00Z",
    )


class TestMeanReversionSkill:
    """Test suite for Mean Reversion Strategy."""

    async def test_no_signal_in_normal_market(self, skill, normal_market):
        signal = await skill.generate_signal(normal_market)
        assert signal is None

    async def test_sell_signal_in_overbought(self, skill, overbought_market):
        signal = await skill.generate_signal(overbought_market)
        assert signal is not None
        assert signal.action == "sell"
        assert 0.0 <= signal.confidence <= 1.0

    async def test_insufficient_data_returns_none(self, skill, normal_market):
        short_data = MarketData(
            symbol="BTC/USD",
            close=normal_market.close[:3],
            timestamp="2026-06-12T00:00:00Z",
        )
        signal = await skill.generate_signal(short_data, window=20)
        assert signal is None

    async def test_parameter_bounds(self, skill, overbought_market):
        with pytest.raises(ValueError):
            await skill.generate_signal(overbought_market, entry_z=0.5)

    async def test_dna_congruence(self, skill):
        """DNA profile indicates moderate risk -- verify behavior."""
        dna = skill.dna
        assert dna[1] == 0.3  # Risk dimension
        assert dna[0] > 0.5   # Speed dimension

    @pytest.mark.parametrize("window", [5, 10, 20, 50])
    async def test_various_windows(self, skill, overbought_market, window):
        signal = await skill.generate_signal(overbought_market, window=window)
        # All parameterizations should produce valid signals or None
        assert signal is None or signal.action in ("buy", "sell")
```

### Running Tests

```bash
# Run specific skill tests
pytest skills/strategy/mean-reversion/test_skill.py -v

# Run all skill tests with coverage
pytest skills/ --cov=skills/ --cov-report=term-missing

# Sandbox test (includes historical run)
cortex skill sandbox skills/strategy/mean-reversion/
```

---

## 8. Publishing to the Skill Registry

Once the Skill passes all sandbox checks, publish it:

```bash
cortex skill publish skills/strategy/mean-reversion/

# The registry returns:
#   Skill 'strat-mean-reversion' v1.0.0 published
#   Registry ID: 4f8a-b3c2
#   Status: sandbox (will auto-promote after 24h observation)
```

**Post-publication:**
- Skills remain in `sandbox` status for 24 hours (observation period).
- During this period, the Skill runs on live data but its signals are **not** acted upon.
- After 24h, if no anomalies are detected, the Skill auto-promotes to `active`.
- An operator can manually promote earlier via the API.

---

## 9. Skill Registry API

See [API Reference](./api-reference.md) for full endpoint details.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/skills` | GET | List/search skills |
| `/api/skills/:id` | GET | Get skill detail |
| `/api/skills` | POST | Register new skill |
| `/api/skills/:id/deploy` | POST | Deploy skill |
| `/api/skills/:id/retire` | POST | Retire skill |

---

## 10. Best Practices

- **DNA accuracy**: Ensure the DNA vector genuinely reflects the Skill's behavior. The sandbox verifies this automatically.
- **Dependency management**: Declare all dependencies in `spec.yaml`. The registry resolves the dependency graph at deploy time.
- **Stateless design**: Skills should be stateless between invocations. Use the provided `SkillContext` for any required state.
- **Error handling**: Return `None` for no-signal conditions rather than raising exceptions. The framework logs all raised errors.
- **Performance profiling**: Use the `@profile` decorator to track skill latency automatically.
- **Version pinning**: When depending on other skills, pin to major versions (e.g., `indicator-sma@^2.0`).

---

## 11. Related Documents

- [Architecture Overview](./architecture.md) -- system design, L6 modules, mechanisms
- [API Reference](./api-reference.md) -- REST and WebSocket endpoint documentation
- [Operator Manual](./operator-manual.md) -- deployment, monitoring, troubleshooting
