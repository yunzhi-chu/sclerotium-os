"""SQLite connection manager with optional persistence toggle.

Set CORTEX_DB_PATH to configure the database file location.
Set CORTEX_NO_DB=1 to disable persistence entirely.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import time

from src.utils.logging import CortexLogger

logger = CortexLogger("db")

_DB_PATH: Path | None = None
_CONN: sqlite3.Connection | None = None


def _resolve_path() -> Path | None:
    global _DB_PATH
    if _DB_PATH is not None:
        return _DB_PATH
    if os.environ.get("CORTEX_NO_DB") == "1":
        return None
    raw = os.environ.get("CORTEX_DB_PATH", "")
    if raw:
        _DB_PATH = Path(raw)
    else:
        _DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "cortex.db"
    return _DB_PATH


def get_connection() -> sqlite3.Connection | None:
    """Get or create the SQLite connection."""
    global _CONN
    if _CONN is not None:
        return _CONN
    path = _resolve_path()
    if path is None:
        logger.info("db_disabled", reason="CORTEX_NO_DB=1")
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    _CONN = sqlite3.connect(str(path), check_same_thread=False)
    _CONN.row_factory = sqlite3.Row
    _CONN.execute("PRAGMA journal_mode=WAL")
    _CONN.execute("PRAGMA foreign_keys=ON")
    logger.info("db_connected", path=str(path))
    return _CONN


def close_connection() -> None:
    global _CONN
    if _CONN:
        _CONN.close()
        _CONN = None
        logger.info("db_closed")


def run_migrations() -> int:
    """Run schema migrations. Returns number of tables created."""
    conn = get_connection()
    if conn is None:
        return 0

    schema = """
    CREATE TABLE IF NOT EXISTS skills (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        version TEXT NOT NULL DEFAULT '1.0.0',
        category TEXT NOT NULL DEFAULT '',
        description TEXT DEFAULT '',
        keywords TEXT DEFAULT '[]',
        dependencies TEXT DEFAULT '[]',
        metadata TEXT DEFAULT '{}',
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS strategies (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT '',
        dna_vector TEXT NOT NULL DEFAULT '[0.5,0.5,0.5,0.5,0.5,0.5]',
        sharpe REAL DEFAULT 0,
        max_drawdown REAL DEFAULT 0,
        annual_return REAL DEFAULT 0,
        win_rate REAL DEFAULT 0,
        metadata TEXT DEFAULT '{}',
        created_at REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL,
        severity TEXT DEFAULT 'info',
        module TEXT DEFAULT '',
        data TEXT DEFAULT '{}',
        source TEXT DEFAULT '',
        parent_id TEXT DEFAULT '',
        created_at REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS goals (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        domain TEXT NOT NULL,
        status TEXT DEFAULT 'proposed',
        description TEXT DEFAULT '',
        feasibility_score REAL DEFAULT 0,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS emergence_patterns (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        confidence REAL DEFAULT 0,
        agent_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'detected',
        signature TEXT DEFAULT '',
        created_at REAL NOT NULL,
        crystallized_at REAL
    );

    CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_logs(event_type);
    CREATE INDEX IF NOT EXISTS idx_audit_severity ON audit_logs(severity);
    CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
    CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category);
    CREATE INDEX IF NOT EXISTS idx_strategies_category ON strategies(category);
    CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);
    """

    count = 0
    for stmt in schema.split(";"):
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt)
            count += 1

    conn.commit()
    logger.info("db_migrated", statements=count)
    return count
