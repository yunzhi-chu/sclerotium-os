"""Tests for the SQLite persistence layer (src/db)."""

import time

import pytest

from src.db.connection import close_connection, get_connection, run_migrations
from src.db.repository import Repository


@pytest.fixture(autouse=True)
def _reset_db_state(monkeypatch):
    """Reset global connection state before and after each test."""
    import src.db.connection as db_conn

    # Close any existing connection
    close_connection()

    # Reset module-level globals properly by going through the module reference
    monkeypatch.setattr(db_conn, "_CONN", None)
    monkeypatch.setattr(db_conn, "_DB_PATH", None)

    yield

    close_connection()
    monkeypatch.setattr(db_conn, "_CONN", None)
    monkeypatch.setattr(db_conn, "_DB_PATH", None)


@pytest.fixture
def in_memory_db(monkeypatch):
    """Configure an in-memory SQLite database for testing."""
    import src.db.connection as db_conn

    monkeypatch.setattr(db_conn, "_CONN", None)
    monkeypatch.setattr(db_conn, "_DB_PATH", None)
    monkeypatch.setenv("CORTEX_DB_PATH", ":memory:")
    conn = get_connection()
    assert conn is not None
    run_migrations()
    return conn


class TestConnection:
    def test_get_connection_creates_connection(self, monkeypatch) -> None:
        """get_connection should return a connection when DB is configured."""
        monkeypatch.setenv("CORTEX_DB_PATH", ":memory:")
        conn = get_connection()
        assert conn is not None
        # Should return the same connection on second call
        conn2 = get_connection()
        assert conn2 is conn

    def test_get_connection_with_no_db(self, monkeypatch) -> None:
        """get_connection should return None when CORTEX_NO_DB=1."""
        monkeypatch.setenv("CORTEX_NO_DB", "1")
        conn = get_connection()
        assert conn is None

    def test_close_connection(self, monkeypatch) -> None:
        """close_connection should close and clear the connection."""
        monkeypatch.setenv("CORTEX_DB_PATH", ":memory:")
        conn = get_connection()
        assert conn is not None
        close_connection()
        import src.db.connection as db_conn

        assert db_conn._CONN is None

    def test_close_connection_when_none(self) -> None:
        """close_connection should not error when no connection exists."""
        close_connection()
        close_connection()  # Should be a no-op

    def test_run_migrations_creates_tables(self, monkeypatch) -> None:
        """run_migrations should create all expected tables."""
        monkeypatch.setenv("CORTEX_DB_PATH", ":memory:")
        count = run_migrations()
        assert count > 0
        conn = get_connection()
        assert conn is not None
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [r["name"] for r in tables]
        assert "skills" in table_names
        assert "strategies" in table_names
        assert "audit_logs" in table_names
        assert "goals" in table_names
        assert "emergence_patterns" in table_names

    def test_run_migrations_with_no_db(self, monkeypatch) -> None:
        """run_migrations should return 0 when CORTEX_NO_DB=1."""
        monkeypatch.setenv("CORTEX_NO_DB", "1")
        count = run_migrations()
        assert count == 0

    def test_idempotent_migrations(self, monkeypatch) -> None:
        """Running migrations twice should not error."""
        monkeypatch.setenv("CORTEX_DB_PATH", ":memory:")
        run_migrations()
        run_migrations()  # Second call should be fine


class TestRepository:
    def test_insert_and_find_by_id(self, in_memory_db) -> None:
        """Insert a record and find it by id."""
        repo = Repository("skills")
        now = time.time()
        inserted = repo.insert({
            "id": "skill-1",
            "name": "Test Skill",
            "version": "1.0.0",
            "created_at": now,
            "updated_at": now,
        })
        assert inserted
        row = repo.find_by_id("skill-1")
        assert row is not None
        assert row["name"] == "Test Skill"
        assert row["version"] == "1.0.0"

    def test_find_by_id_not_found(self, in_memory_db) -> None:
        """find_by_id should return None for non-existent id."""
        repo = Repository("skills")
        row = repo.find_by_id("nonexistent")
        assert row is None

    def test_find_all(self, in_memory_db) -> None:
        """find_all should return all records ordered by created_at DESC."""
        repo = Repository("skills")
        now = time.time()
        repo.insert({"id": "s1", "name": "First", "created_at": now - 10, "updated_at": now - 10})
        repo.insert({"id": "s2", "name": "Second", "created_at": now, "updated_at": now})
        rows = repo.find_all()
        assert len(rows) == 2
        # Should be ordered by created_at DESC
        assert rows[0]["id"] == "s2"

    def test_find_all_with_limit_and_offset(self, in_memory_db) -> None:
        """find_all should respect limit and offset."""
        repo = Repository("skills")
        now = time.time()
        repo.insert({"id": "s1", "name": "S1", "created_at": now, "updated_at": now})
        repo.insert({"id": "s2", "name": "S2", "created_at": now, "updated_at": now})
        repo.insert({"id": "s3", "name": "S3", "created_at": now, "updated_at": now})
        rows = repo.find_all(limit=2, offset=1)
        assert len(rows) == 2
        # With limit 1
        rows = repo.find_all(limit=1)
        assert len(rows) == 1

    def test_find_by_field(self, in_memory_db) -> None:
        """find_by should filter by a specific field."""
        repo = Repository("skills")
        now = time.time()
        repo.insert({"id": "s1", "name": "Alpha", "category": "A", "created_at": now, "updated_at": now})
        repo.insert({"id": "s2", "name": "Beta", "category": "B", "created_at": now, "updated_at": now})
        repo.insert({"id": "s3", "name": "Gamma", "category": "A", "created_at": now, "updated_at": now})
        rows = repo.find_by("category", "A")
        assert len(rows) == 2
        assert rows[0]["id"] in ("s1", "s3")

    def test_update(self, in_memory_db) -> None:
        """Update should modify a record and return True."""
        repo = Repository("skills")
        now = time.time()
        repo.insert({"id": "update-1", "name": "Original", "version": "1.0.0", "created_at": now, "updated_at": now})
        updated = repo.update("update-1", {"name": "Updated", "version": "2.0.0"})
        assert updated
        row = repo.find_by_id("update-1")
        assert row is not None
        assert row["name"] == "Updated"
        assert row["version"] == "2.0.0"

    def test_delete(self, in_memory_db) -> None:
        """Delete should remove a record and return True."""
        repo = Repository("skills")
        now = time.time()
        repo.insert({"id": "delete-1", "name": "Delete Me", "created_at": now, "updated_at": now})
        deleted = repo.delete("delete-1")
        assert deleted
        row = repo.find_by_id("delete-1")
        assert row is None

    def test_delete_nonexistent(self, in_memory_db) -> None:
        """Delete of non-existent id should return True (no error)."""
        repo = Repository("skills")
        deleted = repo.delete("nonexistent")
        assert deleted

    def test_count(self, in_memory_db) -> None:
        """Count should return the number of records."""
        repo = Repository("skills")
        now = time.time()
        assert repo.count() == 0
        repo.insert({"id": "c1", "name": "C1", "category": "X", "created_at": now, "updated_at": now})
        repo.insert({"id": "c2", "name": "C2", "category": "X", "created_at": now, "updated_at": now})
        repo.insert({"id": "c3", "name": "C3", "category": "Y", "created_at": now, "updated_at": now})
        assert repo.count() == 3
        assert repo.count(where="category = ?", params=["X"]) == 2

    def test_truncate(self, in_memory_db) -> None:
        """Truncate should remove all records."""
        repo = Repository("skills")
        now = time.time()
        repo.insert({"id": "t1", "name": "T1", "created_at": now, "updated_at": now})
        repo.insert({"id": "t2", "name": "T2", "created_at": now, "updated_at": now})
        repo.truncate()
        assert repo.count() == 0

    def test_insert_with_dict_and_list_fields(self, in_memory_db) -> None:
        """Insert should JSON-serialize dict and list fields."""
        repo = Repository("skills")
        now = time.time()
        repo.insert({
            "id": "json-1",
            "name": "JSON Test",
            "keywords": ["finance", "trading"],
            "metadata": {"source": "test", "version": 2},
            "created_at": now,
            "updated_at": now,
        })
        row = repo.find_by_id("json-1")
        assert row is not None
        import json

        keywords = json.loads(row["keywords"]) if isinstance(row["keywords"], str) else row["keywords"]
        assert "finance" in keywords
        meta = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"]
        assert meta["source"] == "test"

    def test_update_with_dict_field(self, in_memory_db) -> None:
        """Update should JSON-serialize dict fields."""
        repo = Repository("skills")
        now = time.time()
        repo.insert({"id": "update-json", "name": "JSON Update", "created_at": now, "updated_at": now})
        repo.update("update-json", {"metadata": {"key": "value"}})
        row = repo.find_by_id("update-json")
        assert row is not None
        import json

        meta = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"]
        assert meta["key"] == "value"

    def test_repository_no_db(self, monkeypatch) -> None:
        """Repository operations should return sensible defaults when DB is disabled."""
        monkeypatch.setenv("CORTEX_NO_DB", "1")
        from src.db.connection import close_connection
        close_connection()
        repo = Repository("skills")
        assert not repo.insert({"id": "x", "name": "X"})
        assert repo.find_by_id("x") is None
        assert repo.find_all() == []
        assert repo.find_by("name", "X") == []
        assert not repo.update("x", {"name": "Y"})
        # delete returns False when no DB connection (which is falsy)
        assert repo.delete("x") is False
        assert repo.count() == 0
        repo.truncate()

    def test_insert_failure_returns_false(self, monkeypatch) -> None:
        """Insert should return False on database error."""
        monkeypatch.setenv("CORTEX_DB_PATH", ":memory:")
        repo = Repository("skills")
        bad_repo = Repository("nonexistent_table")
        result = bad_repo.insert({"id": "x", "name": "x"})
        assert not result

    def test_update_failure_returns_false(self, monkeypatch) -> None:
        """Update should return False on database error."""
        monkeypatch.setenv("CORTEX_DB_PATH", ":memory:")
        monkeypatch.setattr("src.db.connection.get_connection", lambda: None)
        repo = Repository("skills")
        result = repo.update("x", {"name": "test"})
        assert not result

    def test_insert_with_connection_none(self, monkeypatch) -> None:
        """insert should return False when connection is None."""
        monkeypatch.setenv("CORTEX_NO_DB", "1")
        repo = Repository("skills")
        assert not repo.insert({"id": "x", "name": "x"})

    def test_connection_with_custom_path(self, monkeypatch, tmp_path) -> None:
        """get_connection should use a custom path when CORTEX_DB_PATH is set."""
        db_file = tmp_path / "test_custom.db"
        monkeypatch.setenv("CORTEX_DB_PATH", str(db_file))
        conn = get_connection()
        assert conn is not None
        assert db_file.exists()
        close_connection()

    def test_resolve_path_cached_db_path(self, monkeypatch) -> None:
        """_resolve_path should return cached _DB_PATH without re-checking env vars."""
        import src.db.connection as db_conn

        # First call to set the cache
        monkeypatch.setenv("CORTEX_DB_PATH", ":memory:")
        conn = get_connection()
        assert conn is not None
        close_connection()
        # Now _DB_PATH is cached; set CORTEX_NO_DB to prove cache is used
        monkeypatch.setenv("CORTEX_NO_DB", "1")
        # _DB_PATH is still set from before, so it should return it despite CORTEX_NO_DB
        cached = db_conn._resolve_path()
        assert cached is not None

    def test_resolve_path_empty_env_var_falls_back_to_default(self, monkeypatch) -> None:
        """When CORTEX_DB_PATH is empty string, _resolve_path should use default."""
        import src.db.connection as db_conn
        from pathlib import Path

        monkeypatch.setenv("CORTEX_DB_PATH", "")
        monkeypatch.setattr(db_conn, "_DB_PATH", None)
        result = db_conn._resolve_path()
        # Should use the default path (not None, not empty string)
        assert result is not None
        assert "cortex.db" in str(result)

    def test_update_failure_on_invalid_column(self, monkeypatch) -> None:
        """Update should return False when trying to set a non-existent column."""
        monkeypatch.setenv("CORTEX_DB_PATH", ":memory:")
        run_migrations()
        repo = Repository("skills")
        now = time.time()
        repo.insert({"id": "u1", "name": "Test", "created_at": now, "updated_at": now})
        # Updating a non-existent column should cause an sqlite3.Error
        result = repo.update("u1", {"nonexistent_column": "value"})
        assert not result
