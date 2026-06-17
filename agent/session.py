"""Session Manager — JSONL + SQLite session persistence.

Injecting R4 (Engram双时态): fast write path (lossless JSONL append)
+ SQLite metadata index for fast lookup + resume support.

Features:
  - Session create / list / resume / delete
  - JSONL append for lossless message history
  - SQLite index for fast session search
  - Auto-save checkpoint every N turns
  - Session metadata (title, tags, model, token_count)
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("sclerotium.session")


@dataclass(frozen=True)
class SessionInfo:
    """Session metadata (immutable)."""
    session_id: str
    title: str = ""
    model: str = ""
    message_count: int = 0
    token_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: tuple[str, ...] = ()


class SessionManager:
    """Persistent session storage with JSONL + SQLite.

    Usage:
        mgr = SessionManager("./data/sessions")
        sid = mgr.create(title="Coding session", model="deepseek-v4-flash")
        mgr.append_message(sid, {"role": "user", "content": "Hello"})
        mgr.append_message(sid, {"role": "assistant", "content": "Hi!"})

        # Resume later
        messages = mgr.load_messages(sid)
        sessions = mgr.list_sessions()
    """

    def __init__(self, data_dir: str = "./data/sessions") -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._db_path = self._data_dir / "sessions.db"
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Create SQLite tables with migrations."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT DEFAULT '',
                model TEXT DEFAULT '',
                message_count INTEGER DEFAULT 0,
                token_count INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                tags TEXT DEFAULT '[]'
            )
        """)
        # Migration: add columns that might be missing
        cur = self._conn.execute("PRAGMA table_info(sessions)")
        existing = {row[1] for row in cur.fetchall()}
        for col, col_def in [
            ("tags", "TEXT DEFAULT '[]'"),
            ("token_count", "INTEGER DEFAULT 0"),
        ]:
            if col not in existing:
                self._conn.execute(f"ALTER TABLE sessions ADD COLUMN {col} {col_def}")

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_updated
            ON sessions(updated_at DESC)
        """)
        self._conn.commit()

    # ── CRUD ──────────────────────────────────────────────────────────────

    def create(
        self,
        title: str = "",
        model: str = "",
        tags: list[str] | None = None,
    ) -> str:
        """Create a new session. Returns session_id."""
        sid = uuid.uuid4().hex[:12]
        now = time.time()

        self._conn.execute(
            "INSERT INTO sessions (id, title, model, created_at, updated_at, tags) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (sid, title, model, now, now, json.dumps(tags or [])),
        )
        self._conn.commit()

        # Create JSONL file
        jsonl_path = self._jsonl_path(sid)
        jsonl_path.touch()

        logger.info("Session created: %s (%s)", sid, title or "untitled")
        return sid

    def get(self, session_id: str) -> SessionInfo | None:
        """Get session metadata."""
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return None

        try:
            tags = tuple(json.loads(row["tags"] or "[]"))
        except json.JSONDecodeError:
            tags = ()

        return SessionInfo(
            session_id=row["id"],
            title=row["title"] or "",
            model=row["model"] or "",
            message_count=row["message_count"] or 0,
            token_count=row["token_count"] or 0,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            tags=tags,
        )

    def list_sessions(self, limit: int = 50) -> list[SessionInfo]:
        """List recent sessions, newest first."""
        rows = self._conn.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

        result = []
        for row in rows:
            try:
                tags = tuple(json.loads(row["tags"] or "[]"))
            except json.JSONDecodeError:
                tags = ()
            result.append(SessionInfo(
                session_id=row["id"],
                title=row["title"] or "",
                model=row["model"] or "",
                message_count=row["message_count"] or 0,
                token_count=row["token_count"] or 0,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                tags=tags,
            ))
        return result

    def update_meta(
        self,
        session_id: str,
        title: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Update session metadata."""
        now = time.time()
        if title is not None:
            self._conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, session_id),
            )
        if tags is not None:
            self._conn.execute(
                "UPDATE sessions SET tags = ?, updated_at = ? WHERE id = ?",
                (json.dumps(tags), now, session_id),
            )
        self._conn.commit()

    def delete(self, session_id: str) -> bool:
        """Delete a session and its JSONL file."""
        self._conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self._conn.commit()

        jsonl_path = self._jsonl_path(session_id)
        if jsonl_path.exists():
            jsonl_path.unlink()
            return True
        return False

    # ── Message persistence (JSONL append — fast write path) ─────────────

    def append_message(self, session_id: str, message: dict[str, Any]) -> None:
        """Append a single message to the session JSONL file."""
        jsonl_path = self._jsonl_path(session_id)
        entry = {
            "ts": time.time(),
            "msg": message,
        }
        with open(jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Update counters
        now = time.time()
        self._conn.execute(
            "UPDATE sessions SET message_count = message_count + 1, "
            "updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        self._conn.commit()

    def append_messages(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        """Append multiple messages at once."""
        jsonl_path = self._jsonl_path(session_id)
        now = time.time()
        with open(jsonl_path, "a", encoding="utf-8") as f:
            for msg in messages:
                entry = {"ts": now, "msg": msg}
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        self._conn.execute(
            "UPDATE sessions SET message_count = message_count + ?, "
            "updated_at = ? WHERE id = ?",
            (len(messages), now, session_id),
        )
        self._conn.commit()

    def load_messages(
        self, session_id: str, limit: int = 0,
    ) -> list[dict[str, Any]]:
        """Load messages from JSONL file. limit=0 means all."""
        jsonl_path = self._jsonl_path(session_id)
        if not jsonl_path.exists():
            return []

        messages = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    messages.append(entry["msg"])
                except (json.JSONDecodeError, KeyError):
                    continue

        if limit > 0 and len(messages) > limit:
            messages = messages[-limit:]

        return messages

    def get_history(self, session_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent conversation history (OpenClaw resolveSession pattern)."""
        return self.load_messages(session_id, limit=limit)

    def save_checkpoint(
        self, session_id: str, messages: list[dict[str, Any]], token_count: int = 0,
    ) -> None:
        """Save a full checkpoint snapshot."""
        jsonl_path = self._jsonl_path(session_id)
        now = time.time()

        with open(jsonl_path, "w", encoding="utf-8") as f:
            for msg in messages:
                entry = {"ts": now, "msg": msg}
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        self._conn.execute(
            "UPDATE sessions SET message_count = ?, token_count = ?, "
            "updated_at = ? WHERE id = ?",
            (len(messages), token_count, now, session_id),
        )
        self._conn.commit()

    # ── Helpers ──────────────────────────────────────────────────────────

    def _jsonl_path(self, session_id: str) -> Path:
        return self._data_dir / f"{session_id}.jsonl"

    def close(self) -> None:
        self._conn.close()

    def get_stats(self) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT COUNT(*) as total, SUM(message_count) as total_msgs "
            "FROM sessions"
        ).fetchone()
        return {
            "total_sessions": row["total"] or 0,
            "total_messages": row["total_msgs"] or 0,
        }
