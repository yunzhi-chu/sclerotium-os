"""Token Tracker — usage tracking + budget control (Gap 17).

SQLite-persisted token usage with daily/monthly cost tracking.
Budget alerts when approaching configured limits.
"""

from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TokenUsage:
    """A single token usage record."""
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float = 0.0
    timestamp: float = field(default_factory=time.time)


class TokenTracker:
    """Tracks token usage and cost across LLM calls.

    Usage:
        tracker = TokenTracker("./data/tokens.db")
        tracker.record("deepseek-v4-flash", "deepseek", 500, 300)
        stats = tracker.get_daily_stats()
        if tracker.is_over_budget():
            print("Budget alert!")
    """

    # Approximate cost per 1M tokens (USD, 2026 pricing)
    _COST_PER_1M: dict[str, dict[str, float]] = {
        "deepseek": {
            "deepseek-v4-flash": 0.28,
            "deepseek-v4-pro": 1.10,
            "default": 0.50,
        },
        "openai": {
            "gpt-4o": 5.00,
            "gpt-4o-mini": 0.60,
            "default": 3.00,
        },
        "openrouter": {"default": 2.00},
        "groq": {"default": 0.30},
        "ollama": {"default": 0.0},  # Local = free
    }

    def __init__(
        self,
        db_path: str = "./data/tokens.db",
        daily_budget_usd: float = 5.0,
        monthly_budget_usd: float = 50.0,
    ) -> None:
        self._db_path = db_path
        self.daily_budget = daily_budget_usd
        self.monthly_budget = monthly_budget_usd

        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                provider TEXT NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                timestamp REAL NOT NULL
            )
        """)
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_token_ts ON token_usage(timestamp)"
        )
        self._conn.commit()

    def _estimate_cost(self, provider: str, model: str, total_tokens: int) -> float:
        """Estimate cost in USD for a token count."""
        provider_rates = self._COST_PER_1M.get(provider, {})
        model_rate = provider_rates.get(model, provider_rates.get("default", 1.0))
        return (total_tokens / 1_000_000) * model_rate

    def record(
        self, model: str, provider: str,
        prompt_tokens: int, completion_tokens: int,
    ) -> None:
        """Record a token usage event."""
        total = prompt_tokens + completion_tokens
        cost = self._estimate_cost(provider, model, total)

        self._conn.execute(
            "INSERT INTO token_usage (model, provider, prompt_tokens, "
            "completion_tokens, total_tokens, cost_usd, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (model, provider, prompt_tokens, completion_tokens, total, cost, time.time()),
        )
        self._conn.commit()

    def get_daily_stats(self) -> dict[str, Any]:
        """Get today's token usage stats."""
        today_start = time.time() - (time.time() % 86400)
        row = self._conn.execute(
            "SELECT COUNT(*) as calls, COALESCE(SUM(total_tokens), 0) as tokens, "
            "COALESCE(SUM(cost_usd), 0) as cost "
            "FROM token_usage WHERE timestamp >= ?",
            (today_start,),
        ).fetchone()
        return {
            "calls": row["calls"] or 0,
            "tokens_today": row["tokens"] or 0,
            "cost_today_usd": round(row["cost"] or 0, 4),
            "budget_usd": self.daily_budget,
            "budget_remaining": round(self.daily_budget - (row["cost"] or 0), 4),
        }

    def get_monthly_stats(self) -> dict[str, Any]:
        """Get this month's token usage stats."""
        import datetime
        now = datetime.datetime.now()
        month_start = datetime.datetime(now.year, now.month, 1).timestamp()
        row = self._conn.execute(
            "SELECT COALESCE(SUM(total_tokens), 0) as tokens, "
            "COALESCE(SUM(cost_usd), 0) as cost "
            "FROM token_usage WHERE timestamp >= ?",
            (month_start,),
        ).fetchone()
        return {
            "tokens_month": row["tokens"] or 0,
            "cost_month_usd": round(row["cost"] or 0, 4),
            "budget_usd": self.monthly_budget,
            "budget_remaining": round(self.monthly_budget - (row["cost"] or 0), 4),
        }

    def is_over_budget(self) -> bool:
        """Check if daily or monthly budget is exceeded."""
        daily = self.get_daily_stats()
        if daily["cost_today_usd"] > self.daily_budget:
            return True
        monthly = self.get_monthly_stats()
        if monthly["cost_month_usd"] > self.monthly_budget:
            return True
        return False

    def get_total_stats(self) -> dict[str, Any]:
        """Get all-time token usage stats."""
        row = self._conn.execute(
            "SELECT COUNT(*) as calls, COALESCE(SUM(total_tokens), 0) as tokens, "
            "COALESCE(SUM(cost_usd), 0) as cost "
            "FROM token_usage"
        ).fetchone()
        return {
            "total_calls": row["calls"] or 0,
            "total_tokens": row["tokens"] or 0,
            "total_cost_usd": round(row["cost"] or 0, 4),
        }

    def close(self) -> None:
        self._conn.close()
