"""Generic CRUD repository for SQLite-backed entities."""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any


class Repository:
    """Generic repository for a single SQLite table.

    Usage:
        skills = Repository("skills")
        skills.insert({"id": "s1", "name": "Test", "created_at": time.time()})
        row = skills.find_by_id("s1")
        skills.update("s1", {"name": "Updated"})
        skills.delete("s1")
    """

    def __init__(self, table_name: str, conn_getter=None) -> None:
        self._table = table_name
        self._conn_getter = conn_getter or _default_conn_getter

    def insert(self, data: dict[str, Any]) -> bool:
        conn = self._conn_getter()
        if conn is None:
            return False
        data = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in data.items()}
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        try:
            conn.execute(
                f"INSERT OR REPLACE INTO {self._table} ({columns}) VALUES ({placeholders})",
                list(data.values()),
            )
            conn.commit()
            return True
        except sqlite3.Error:
            return False

    def find_by_id(self, entity_id: str) -> dict[str, Any] | None:
        conn = self._conn_getter()
        if conn is None:
            return None
        row = conn.execute(
            f"SELECT * FROM {self._table} WHERE id = ?", (entity_id,)
        ).fetchone()
        return dict(row) if row else None

    def find_all(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        conn = self._conn_getter()
        if conn is None:
            return []
        rows = conn.execute(
            f"SELECT * FROM {self._table} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]

    def find_by(self, field: str, value: Any, limit: int = 100) -> list[dict[str, Any]]:
        conn = self._conn_getter()
        if conn is None:
            return []
        rows = conn.execute(
            f"SELECT * FROM {self._table} WHERE {field} = ? ORDER BY created_at DESC LIMIT ?",
            (value, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def update(self, entity_id: str, data: dict[str, Any]) -> bool:
        conn = self._conn_getter()
        if conn is None:
            return False
        data = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in data.items()}
        sets = ", ".join(f"{k} = ?" for k in data)
        try:
            conn.execute(
                f"UPDATE {self._table} SET {sets} WHERE id = ?",
                list(data.values()) + [entity_id],
            )
            conn.commit()
            return True
        except sqlite3.Error:
            return False

    def delete(self, entity_id: str) -> bool:
        conn = self._conn_getter()
        if conn is None:
            return False
        conn.execute(f"DELETE FROM {self._table} WHERE id = ?", (entity_id,))
        conn.commit()
        return True

    def count(self, where: str = "", params: list[Any] | None = None) -> int:
        conn = self._conn_getter()
        if conn is None:
            return 0
        sql = f"SELECT COUNT(*) FROM {self._table}"
        if where:
            sql += f" WHERE {where}"
        row = conn.execute(sql, params or []).fetchone()
        return row[0] if row else 0

    def truncate(self) -> None:
        conn = self._conn_getter()
        if conn:
            conn.execute(f"DELETE FROM {self._table}")
            conn.commit()


def _default_conn_getter():
    from src.db.connection import get_connection

    return get_connection()
