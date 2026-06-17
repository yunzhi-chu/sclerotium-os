"""SQLite persistence layer for Fungal Cortex v2.0.

Provides connection management, schema migration, and generic CRUD
repositories. When persistence is disabled (env CORTEX_NO_DB=1), all
operations are no-ops and data lives in memory only.
"""

from __future__ import annotations

import os

from src.db.connection import get_connection, close_connection, run_migrations
from src.db.repository import Repository

__all__ = ["get_connection", "close_connection", "run_migrations", "Repository"]
