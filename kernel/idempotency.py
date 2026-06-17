"""Idempotency System — deduplicate requests (Gap: 幂等性).

OpenClaw-equivalent idempotency key deduplication.
SQLite-backed with TTL-based expiry.

Usage:
    store = IdempotencyStore("./data/idempotency.db")
    if store.is_duplicate("req_abc123"):
        return store.get_cached("req_abc123")  # Return cached result
    # ... process request ...
    store.cache("req_abc123", {"status": "ok", "data": ...})
"""

from __future__ import annotations

import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

IDEMPOTENCY_TTL_SECONDS = 3600  # 1 hour default


@dataclass(frozen=True)
class CachedResponse:
    """Cached idempotent response (immutable)."""
    key: str
    payload: dict[str, Any]
    created_at: float
    expires_at: float
    hit_count: int = 0


class IdempotencyStore:
    """SQLite-backed idempotency key store with TTL expiry.

    Usage:
        store = IdempotencyStore()
        key = store.generate_key("agent:run:user123")

        # Check before processing
        cached = store.get(key)
        if cached:
            return cached.payload  # Deduplicate!

        # Process and cache
        result = process_request()
        store.set(key, result, ttl_seconds=3600)
    """

    def __init__(self, db_path: str = "./data/idempotency.db") -> None:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS idempotency (
                key TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                hit_count INTEGER DEFAULT 1
            )
        """)
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_idempotency_expires "
            "ON idempotency(expires_at)"
        )
        # Clean expired entries
        self._conn.execute(
            "DELETE FROM idempotency WHERE expires_at < ?", (time.time(),)
        )
        self._conn.commit()

    @staticmethod
    def generate_key(prefix: str = "") -> str:
        """Generate a unique idempotency key."""
        uid = uuid.uuid4().hex[:16]
        return f"{prefix}:{uid}" if prefix else uid

    def get(self, key: str) -> CachedResponse | None:
        """Check if a key has been seen before. Returns cached response if valid."""
        self._cleanup_expired()

        row = self._conn.execute(
            "SELECT * FROM idempotency WHERE key = ? AND expires_at > ?",
            (key, time.time()),
        ).fetchone()

        if row is None:
            return None

        # Update hit count
        self._conn.execute(
            "UPDATE idempotency SET hit_count = hit_count + 1 WHERE key = ?",
            (key,),
        )
        self._conn.commit()

        import json
        return CachedResponse(
            key=row["key"],
            payload=json.loads(row["payload_json"]),
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            hit_count=row["hit_count"] + 1,
        )

    def is_duplicate(self, key: str) -> bool:
        """Quick check: has this key been seen before?"""
        return self.get(key) is not None

    def set(self, key: str, payload: dict[str, Any], ttl_seconds: float = IDEMPOTENCY_TTL_SECONDS) -> None:
        """Cache a response for idempotency."""
        import json
        now = time.time()
        self._conn.execute(
            "INSERT OR REPLACE INTO idempotency (key, payload_json, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (key, json.dumps(payload, ensure_ascii=False, default=str), now, now + ttl_seconds),
        )
        self._conn.commit()

    def delete(self, key: str) -> bool:
        """Remove a cached entry."""
        cur = self._conn.execute("DELETE FROM idempotency WHERE key = ?", (key,))
        self._conn.commit()
        return cur.rowcount > 0

    def _cleanup_expired(self) -> None:
        """Remove expired entries (called periodically)."""
        self._conn.execute(
            "DELETE FROM idempotency WHERE expires_at < ?", (time.time(),)
        )
        self._conn.commit()

    def get_stats(self) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT COUNT(*) as total, SUM(hit_count) as total_hits "
            "FROM idempotency"
        ).fetchone()
        return {
            "cached_entries": row["total"] or 0,
            "total_hits": row["total_hits"] or 0,
            "dedup_saved": max(0, (row["total_hits"] or 0) - (row["total"] or 0)),
        }

    def close(self) -> None:
        self._cleanup_expired()
        self._conn.close()
