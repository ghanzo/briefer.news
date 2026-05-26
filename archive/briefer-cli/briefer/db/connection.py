"""DuckDB connection management."""

import os
from pathlib import Path

import duckdb

from briefer.db.schema import ensure_tables

_DEFAULT_DIR = Path.home() / ".briefer"
_DEFAULT_DB = _DEFAULT_DIR / "briefer.duckdb"


def _resolve_db_path(override: str | None = None) -> Path:
    if override:
        return Path(override)
    env = os.getenv("BRIEFER_DB_PATH")
    if env:
        return Path(env)
    return _DEFAULT_DB


def get_connection(db_path: str | None = None) -> duckdb.DuckDBPyConnection:
    """Open (or create) the DuckDB database and ensure schema exists."""
    path = _resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(path))
    ensure_tables(conn)
    return conn
