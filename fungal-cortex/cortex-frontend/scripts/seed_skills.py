#!/usr/bin/env python3
"""Batch import skills into the Fungal Cortex Skill Registry.

Reads a JSON file of skill definitions (or generates 22 built-in demo skills)
and POSTs each to the backend API at ``/api/skills``.

Usage::

    # Use built-in demo skills
    python scripts/seed_skills.py

    # Load from a JSON file
    python scripts/seed_skills.py --file my_skills.json

    # Point at a non-default backend
    python scripts/seed_skills.py --api-url http://localhost:8000

    # Dry-run: print what would happen without sending requests
    python scripts/seed_skills.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_API_URL = "http://localhost:8000"

SKILL_CATEGORY_MAP = {
    "core": "adaptive_engine",
    "data": "data_provider",
    "alphaear": "alphaear",
    "quant": "quant_strategy",
    "agent": "agent_plugin",
    "bridge": "vertical_plugin",
}

SKILL_TEMPLATES: List[Dict[str, Any]] = [
    # ---- core (adaptive_engine) ----
    {
        "name": "adaptive-engine",
        "version": "2.0.0",
        "category": "core",
        "description": "Core adaptive engine for self-organizing agent orchestration and dynamic skill routing.",
        "triggers": ["agent.spawned", "pipeline.activate", "skill.missing"],
        "dependencies": [],
        "dna": [0.95, 0.80, 0.90, 0.85, 0.75, 0.60],
        "module": "cortex.engine.adaptive",
    },
    {
        "name": "l4-autonomous-platform",
        "version": "2.0.0",
        "category": "core",
        "description": "L4 autonomous agent platform for self-directed task execution and goal decomposition.",
        "triggers": ["goal.deployed", "task.complex", "strategy.evolve"],
        "dependencies": ["adaptive-engine"],
        "dna": [0.90, 0.95, 0.85, 0.80, 0.90, 0.70],
        "module": "cortex.engine.l4",
    },
    {
        "name": "l5-cluster-platform",
        "version": "2.0.0",
        "category": "core",
        "description": "L5 cluster coordination platform for multi-agent swarms and collective intelligence.",
        "triggers": ["cluster.form", "workflow.distribute", "load.balance"],
        "dependencies": ["l4-autonomous-platform"],
        "dna": [0.85, 0.70, 0.80, 0.95, 0.85, 0.65],
        "module": "cortex.engine.l5",
    },
    {
        "name": "l6-cognition-platform",
        "version": "2.0.0",
        "category": "core",
        "description": "L6 meta-cognition platform for self-reflection, refactoring, and emergent behavior detection.",
        "triggers": ["emergence.detect", "refactor.needed", "pattern.unusual"],
        "dependencies": ["l5-cluster-platform"],
        "dna": [0.70, 0.60, 0.95, 0.70, 0.95, 0.50],
        "module": "cortex.engine.l6",
    },
    # ---- data (data_provider) ----
    {
        "name": "a-stock-data",
        "version": "2.0.0",
        "category": "data",
        "description": "A-share stock data provider for Chinese equity markets: prices, fundamentals, corporate actions.",
        "triggers": ["market.open.cn", "data.refresh.daily", "symbol.watch.cn"],
        "dependencies": [],
        "dna": [0.60, 0.90, 0.50, 0.95, 0.30, 0.40],
        "module": "cortex.data.astock",
    },
    {
        "name": "global-stock-data",
        "version": "2.0.0",
        "category": "data",
        "description": "Global stock data provider for US, HK, EU, and JP markets with cross-exchange normalization.",
        "triggers": ["market.open.us", "market.open.hk", "data.refresh.intraday"],
        "dependencies": [],
        "dna": [0.65, 0.85, 0.55, 0.90, 0.35, 0.45],
        "module": "cortex.data.global",
    },
    # ---- alphaear ----
    {
        "name": "alphaear-stock",
        "version": "2.0.0",
        "category": "alphaear",
        "description": "AlphaEar stock screening skill: scans universe for alpha-generating candidates using multi-factor filters.",
        "triggers": ["scan.start", "alpha.hunt", "screen.universe"],
        "dependencies": ["a-stock-data", "global-stock-data"],
        "dna": [0.80, 0.75, 0.70, 0.85, 0.60, 0.55],
        "module": "cortex.alphaear.stock",
    },
    {
        "name": "alphaear-news",
        "version": "2.0.0",
        "category": "alphaear",
        "description": "AlphaEar news sentiment analyzer: ingests headlines and extracts market-moving signals in real time.",
        "triggers": ["news.flow", "sentiment.shift", "headline.alert"],
        "dependencies": [],
        "dna": [0.75, 0.95, 0.40, 0.90, 0.45, 0.30],
        "module": "cortex.alphaear.news",
    },
    {
        "name": "alphaear-search",
        "version": "2.0.0",
        "category": "alphaear",
        "description": "AlphaEar semantic search: retrieves relevant filings, transcripts, and reports via vector similarity.",
        "triggers": ["search.query", "document.retrieve", "filing.lookup"],
        "dependencies": [],
        "dna": [0.70, 0.60, 0.45, 0.80, 0.55, 0.35],
        "module": "cortex.alphaear.search",
    },
    {
        "name": "alphaear-sentiment",
        "version": "2.0.0",
        "category": "alphaear",
        "description": "AlphaEar fine-grained sentiment: token-level sentiment scoring for earnings calls, filings, and social media.",
        "triggers": ["sentiment.analyze", "earnings.process", "social.scan"],
        "dependencies": ["alphaear-news"],
        "dna": [0.65, 0.85, 0.35, 0.75, 0.70, 0.25],
        "module": "cortex.alphaear.sentiment",
    },
    {
        "name": "alphaear-predictor",
        "version": "2.0.0",
        "category": "alphaear",
        "description": "AlphaEar time-series predictor: LSTM/Transformer-based price movement forecasting with uncertainty bounds.",
        "triggers": ["predict.shortterm", "forecast.generate", "signal.validate"],
        "dependencies": ["a-stock-data", "global-stock-data"],
        "dna": [0.40, 0.50, 0.85, 0.60, 0.95, 0.80],
        "module": "cortex.alphaear.predictor",
    },
    {
        "name": "alphaear-signal-tracker",
        "version": "2.0.0",
        "category": "alphaear",
        "description": "AlphaEar signal tracker: monitors active signals for decay, confluence, and execution readiness.",
        "triggers": ["signal.update", "track.refresh", "signal.decay"],
        "dependencies": ["alphaear-predictor", "alphaear-sentiment"],
        "dna": [0.55, 0.90, 0.75, 0.70, 0.50, 0.85],
        "module": "cortex.alphaear.signal",
    },
    {
        "name": "alphaear-deepear-lite",
        "version": "2.0.0",
        "category": "alphaear",
        "description": "AlphaEar DeepEar Lite: lightweight on-device pattern recognition for real-time edge inference.",
        "triggers": ["edge.infer", "pattern.quick", "lightweight.scan"],
        "dependencies": ["alphaear-predictor"],
        "dna": [0.85, 0.95, 0.60, 0.95, 0.40, 0.90],
        "module": "cortex.alphaear.deepear",
    },
    {
        "name": "alphaear-reporter",
        "version": "2.0.0",
        "category": "alphaear",
        "description": "AlphaEar reporter: auto-generates research summaries, trade rationales, and performance digests.",
        "triggers": ["report.generate", "summary.create", "digest.daily"],
        "dependencies": ["alphaear-signal-tracker"],
        "dna": [0.50, 0.65, 0.30, 0.60, 0.60, 0.40],
        "module": "cortex.alphaear.reporter",
    },
    {
        "name": "alphaear-logic-visualizer",
        "version": "2.0.0",
        "category": "alphaear",
        "description": "AlphaEar logic visualizer: renders decision trees, causal graphs, and factor exposure charts.",
        "triggers": ["visualize.decision", "graph.render", "factor.exposure"],
        "dependencies": ["alphaear-reporter"],
        "dna": [0.45, 0.40, 0.25, 0.50, 0.65, 0.30],
        "module": "cortex.alphaear.viz",
    },
    # ---- quant (quant_strategy) ----
    {
        "name": "quant-strategies",
        "version": "2.0.0",
        "category": "quant",
        "description": "Quant strategy library: backtesting engine with multi-asset support, risk models, and portfolio optimization.",
        "triggers": ["strategy.backtest", "portfolio.optimize", "risk.assess"],
        "dependencies": ["a-stock-data", "global-stock-data"],
        "dna": [0.60, 0.70, 0.95, 0.65, 0.90, 0.75],
        "module": "cortex.quant.strategies",
    },
    {
        "name": "quant-theory",
        "version": "2.0.0",
        "category": "quant",
        "description": "Quant theory engine: stochastic calculus, factor model construction, and regime detection.",
        "triggers": ["theory.compute", "factor.build", "regime.detect"],
        "dependencies": ["quant-strategies"],
        "dna": [0.35, 0.45, 0.80, 0.40, 0.95, 0.60],
        "module": "cortex.quant.theory",
    },
    {
        "name": "quanthub",
        "version": "2.0.0",
        "category": "quant",
        "description": "QuantHub: centralized marketplace for quant models, data feeds, and strategy sharing.",
        "triggers": ["hub.publish", "model.browse", "feed.subscribe"],
        "dependencies": ["quant-strategies"],
        "dna": [0.75, 0.55, 0.65, 0.75, 0.50, 0.45],
        "module": "cortex.quant.hub",
    },
    # ---- agent (agent_plugin) ----
    {
        "name": "masterminds",
        "version": "2.0.0",
        "category": "agent",
        "description": "Masterminds: orchestrated multi-agent collaboration for complex problem-solving and debate.",
        "triggers": ["debate.start", "consensus.build", "problem.complex"],
        "dependencies": ["adaptive-engine"],
        "dna": [0.90, 0.85, 0.70, 0.80, 0.85, 0.55],
        "module": "cortex.agent.masterminds",
    },
    {
        "name": "stock-analysis-team",
        "version": "2.0.0",
        "category": "agent",
        "description": "Stock analysis team: coordinated agent swarm for deep-dive equity research with role specialization.",
        "triggers": ["research.deepdive", "equity.analyze", "team.assemble"],
        "dependencies": ["masterminds", "a-stock-data", "global-stock-data"],
        "dna": [0.80, 0.75, 0.60, 0.85, 0.70, 0.50],
        "module": "cortex.agent.stockteam",
    },
    {
        "name": "skill-creator",
        "version": "2.0.0",
        "category": "agent",
        "description": "Skill creator agent: autonomously designs, tests, and deploys new skills into the registry.",
        "triggers": ["skill.design", "skill.test", "skill.deploy"],
        "dependencies": ["adaptive-engine"],
        "dna": [0.85, 0.60, 0.50, 0.70, 0.80, 0.40],
        "module": "cortex.agent.skillcreator",
    },
    # ---- bridge (vertical_plugin) ----
    {
        "name": "wind-mcp",
        "version": "2.0.0",
        "category": "bridge",
        "description": "Wind MCP bridge: connects Wind Financial Terminal via MCP protocol for institutional data and analytics.",
        "triggers": ["wind.query", "wind.subscribe", "macro.data"],
        "dependencies": ["adaptive-engine"],
        "dna": [0.55, 0.80, 0.60, 0.65, 0.45, 0.50],
        "module": "cortex.bridge.wind",
    },
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class SkillPayload:
    """Skill payload sent to ``POST /api/skills``."""

    name: str
    version: str
    category: str
    description: str
    triggers: List[str]
    dependencies: List[str]
    catalyzes: List[str] = field(default_factory=list)
    catalyzed_by: List[str] = field(default_factory=list)
    dna: Optional[Dict[str, float]] = None
    is_active: bool = True
    module: str = ""

    @classmethod
    def from_template(cls, t: Dict[str, Any]) -> "SkillPayload":
        """Build a payload from a SKILL_TEMPLATES entry."""
        raw_cat = t.get("category", "agent")
        mapped_cat = SKILL_CATEGORY_MAP.get(raw_cat, raw_cat)

        dna_list: List[float] = t.get("dna", [0.5] * 6)
        dna_dict = {
            "picker": dna_list[0] if len(dna_list) > 0 else 0.5,
            "timer": dna_list[1] if len(dna_list) > 1 else 0.5,
            "risk_control": dna_list[2] if len(dna_list) > 2 else 0.5,
            "frequency": dna_list[3] if len(dna_list) > 3 else 0.5,
            "complexity": dna_list[4] if len(dna_list) > 4 else 0.5,
            "holding_period": dna_list[5] if len(dna_list) > 5 else 0.5,
        }

        return cls(
            name=t["name"],
            version=t.get("version", "1.0.0"),
            category=mapped_cat,
            description=t.get("description", ""),
            triggers=t.get("triggers", []),
            dependencies=t.get("dependencies", []),
            dna=dna_dict,
            module=t.get("module", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-safe dict (excludes empty defaults)."""
        d: Dict[str, Any] = {
            "name": self.name,
            "version": self.version,
            "category": self.category,
            "description": self.description,
            "triggers": self.triggers,
            "dependencies": self.dependencies,
            "is_active": self.is_active,
        }
        if self.catalyzes:
            d["catalyzes"] = self.catalyzes
        if self.catalyzed_by:
            d["catalyzed_by"] = self.catalyzed_by
        if self.dna is not None:
            d["dna"] = self.dna
        if self.module:
            d["module"] = self.module
        return d


@dataclass
class SeedSummary:
    """Accumulator for import results."""

    imported: int = 0
    failed: int = 0
    skipped: int = 0
    errors: List[Tuple[str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.imported + self.failed + self.skipped

    def print_report(self) -> None:
        """Print a human-readable summary."""
        print("=" * 56)
        print(f"  Seed Summary:  {self.total} skills processed")
        print(f"  Imported:      {self.imported}")
        print(f"  Failed:        {self.failed}")
        print(f"  Skipped:       {self.skipped}")
        if self.errors:
            print(f"  Errors:")
            for name, msg in self.errors:
                print(f"    - {name}: {msg}")
        print("=" * 56)


# ---------------------------------------------------------------------------
# Progress-bar helpers (tqdm optional)
# ---------------------------------------------------------------------------

_PROGRESS_ENABLED = True

try:
    from tqdm import tqdm as _tqdm
except ImportError:

    class _FallbackProgress:
        """Stand-in progress display when tqdm is not installed."""

        def __init__(self, iterable=None, desc="", **kwargs):
            self.iterable = iterable
            self.desc = desc
            self._iterator = iter(iterable) if iterable else iter([])
            self._idx = 0
            self._total = len(iterable) if iterable else 0

        def __iter__(self):
            return self

        def __next__(self):
            try:
                val = next(self._iterator)
            except StopIteration:
                print()
                raise
            self._idx += 1
            if _PROGRESS_ENABLED and self._total:
                pct = self._idx / self._total * 100
                print(f"\r  {self.desc}  [{self._idx}/{self._total}] {pct:5.1f}%", end="")
            return val

        def update(self, n: int = 1) -> None:
            self._idx += n

        def close(self) -> None:
            pass

        def set_description(self, desc: str) -> None:
            self.desc = desc

    _tqdm = _FallbackProgress


def progress(items, desc: str = "", **kwargs):
    """Wrap an iterable with a progress bar (tqdm if available, else simple counter)."""
    return _tqdm(items, desc=desc, **kwargs)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

RETRY_MAX = 3
RETRY_BASE_DELAY = 1.0  # seconds


def post_skill(
    api_url: str, payload: SkillPayload, dry_run: bool = False
) -> Optional[int]:
    """POST one skill to the API with retries and exponential backoff.

    Returns the HTTP status code on success, or ``None`` on failure.
    """
    url = f"{api_url.rstrip('/')}/api/skills"
    body = json.dumps(payload.to_dict()).encode("utf-8")

    if dry_run:
        curl_parts = [
            "curl -s -o /dev/null -w '%{http_code}'",
            f"-X POST '{url}'",
            "-H 'Content-Type: application/json'",
            f"-d '{body.decode('utf-8')}'",
        ]
        print(f"  [DRY-RUN] {' '.join(curl_parts)}")
        return 200  # pretend success

    last_error: Optional[str] = None
    for attempt in range(1, RETRY_MAX + 1):
        try:
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            if e.code in (409,):
                return 409  # already exists → skipped
            last_error = f"HTTP {e.code}: {e.reason}"
            if attempt < RETRY_MAX:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                print(f"    retry {attempt}/{RETRY_MAX} after {delay:.1f}s  ({last_error})")
                time.sleep(delay)
        except urllib.error.URLError as e:
            last_error = str(e.reason)
            if attempt < RETRY_MAX:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                print(f"    retry {attempt}/{RETRY_MAX} after {delay:.1f}s  ({last_error})")
                time.sleep(delay)
        except (OSError, ConnectionError) as e:
            last_error = str(e)
            if attempt < RETRY_MAX:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                print(f"    retry {attempt}/{RETRY_MAX} after {delay:.1f}s  ({last_error})")
                time.sleep(delay)
    print(f"  [FAIL]  {payload.name}  (after {RETRY_MAX} retries: {last_error})")
    return None


# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------


def load_skills_from_file(filepath: str) -> List[Dict[str, Any]]:
    """Load skill definitions from a JSON file.

    The file must contain an array of objects with at least a ``name`` field.
    """
    with open(filepath, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        data = data.get("skills", data.get("items", []))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array of skills, got {type(data).__name__}")
    if not data:
        raise ValueError("Skill list is empty")
    for i, entry in enumerate(data):
        if "name" not in entry:
            raise ValueError(f"Item at index {i} is missing required 'name' field")
    return data


def generate_demo_skills() -> List[Dict[str, Any]]:
    """Return the built-in 22 demo skill templates."""
    return list(SKILL_TEMPLATES)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch import skills into the Fungal Cortex Skill Registry.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("BACKEND_URL", DEFAULT_API_URL),
        help=f"Backend API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--file",
        "-f",
        default=None,
        help="Path to a JSON file with skill definitions",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print curl commands instead of sending requests",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bar output",
    )
    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    global _PROGRESS_ENABLED
    if args.no_progress:
        _PROGRESS_ENABLED = False

    # 1. Load skills -------------------------------------------------------
    if args.file:
        try:
            raw_skills = load_skills_from_file(args.file)
            source = f"file '{args.file}'"
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            print(f"Error loading skills from {args.file}: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        raw_skills = generate_demo_skills()
        source = "built-in templates"

    print(f"Loaded {len(raw_skills)} skills from {source}")
    print()

    # 2. Validate API connectivity (unless dry-run) ------------------------
    if not args.dry_run:
        api_url = args.api_url.rstrip("/")
        health_url = f"{api_url}/api/health"
        connected = False
        try:
            with urllib.request.urlopen(health_url, timeout=10) as resp:
                if resp.status == 200:
                    connected = True
        except Exception:
            connected = False

        if not connected:
            print(
                f"Warning: Could not reach API at {api_url}.\n"
                "  Continuing anyway — individual POSTs may fail.",
                file=sys.stderr,
            )
        else:
            print(f"API reachable at {api_url}")
    else:
        api_url = args.api_url.rstrip("/")
        print(f"DRY-RUN mode (no requests will be sent to {api_url})")

    print()

    # 3. Import ------------------------------------------------------------
    summary = SeedSummary()
    items = progress(raw_skills, desc="Importing skills")

    for raw in items:
        payload = SkillPayload.from_template(raw)

        code = post_skill(api_url, payload, dry_run=args.dry_run)

        if code is None:
            summary.failed += 1
            summary.errors.append((payload.name, "Connection failed after retries"))
        elif code == 409:
            summary.skipped += 1
        elif 200 <= code < 300:
            summary.imported += 1
        else:
            summary.failed += 1
            summary.errors.append((payload.name, f"Unexpected status {code}"))

    # 4. Report ------------------------------------------------------------
    print()
    summary.print_report()

    if summary.failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
