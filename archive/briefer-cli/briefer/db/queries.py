"""Reusable DuckDB analytical queries."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import duckdb


def get_series_meta(conn: duckdb.DuckDBPyConnection, series_id: str) -> dict | None:
    """Fetch metadata for a single series."""
    row = conn.execute(
        "SELECT * FROM series WHERE series_id = ?", [series_id]
    ).fetchone()
    if not row:
        return None
    cols = [d[0] for d in conn.description]
    return dict(zip(cols, row))


def get_observations(
    conn: duckdb.DuckDBPyConnection,
    series_id: str,
    limit: int = 50,
) -> list[dict]:
    """Fetch recent observations for a series, newest first."""
    rows = conn.execute(
        "SELECT date, value FROM observations "
        "WHERE series_id = ? ORDER BY date DESC LIMIT ?",
        [series_id, limit],
    ).fetchall()
    return [{"date": r[0], "value": r[1]} for r in rows]


def get_all_series(conn: duckdb.DuckDBPyConnection, source: str | None = None) -> list[dict]:
    """Fetch all tracked series, optionally filtered by source."""
    if source:
        rows = conn.execute(
            "SELECT series_id, source, name, category, frequency, units, "
            "latest_date, latest_value, last_updated "
            "FROM series WHERE source = ? ORDER BY category, name",
            [source],
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT series_id, source, name, category, frequency, units, "
            "latest_date, latest_value, last_updated "
            "FROM series ORDER BY source, category, name"
        ).fetchall()
    cols = ["series_id", "source", "name", "category", "frequency", "units",
            "latest_date", "latest_value", "last_updated"]
    return [dict(zip(cols, r)) for r in rows]


def upsert_series(conn: duckdb.DuckDBPyConnection, meta: dict) -> None:
    """Insert or update series metadata."""
    conn.execute("""
        INSERT OR REPLACE INTO series
            (series_id, source, source_key, name, frequency, units,
             seasonal_adj, category, last_updated, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, current_timestamp, ?)
    """, [
        meta["series_id"], meta["source"], meta["source_key"],
        meta["name"], meta.get("frequency"), meta.get("units"),
        meta.get("seasonal_adj"), meta.get("category"),
        meta.get("metadata"),
    ])


def upsert_observations(
    conn: duckdb.DuckDBPyConnection,
    series_id: str,
    observations: list[dict],
) -> int:
    """Bulk upsert observations. Returns count of rows inserted."""
    if not observations:
        return 0
    new_count = 0
    for obs in observations:
        if obs["value"] is None:
            continue
        conn.execute(
            "INSERT OR REPLACE INTO observations (series_id, date, value) VALUES (?, ?, ?)",
            [series_id, obs["date"], obs["value"]],
        )
        new_count += 1

    # Update cached latest in series table
    latest = conn.execute(
        "SELECT date, value FROM observations WHERE series_id = ? ORDER BY date DESC LIMIT 1",
        [series_id],
    ).fetchone()
    if latest:
        first = conn.execute(
            "SELECT date FROM observations WHERE series_id = ? ORDER BY date ASC LIMIT 1",
            [series_id],
        ).fetchone()
        conn.execute(
            "UPDATE series SET latest_date = ?, latest_value = ?, first_date = ?, "
            "last_updated = current_timestamp WHERE series_id = ?",
            [latest[0], latest[1], first[0] if first else None, series_id],
        )
    return new_count


def log_pull_start(conn: duckdb.DuckDBPyConnection, source: str) -> int:
    """Start a pull log entry, return its id."""
    result = conn.execute(
        "INSERT INTO pull_log (source) VALUES (?) RETURNING id", [source]
    ).fetchone()
    return result[0]


def log_pull_end(
    conn: duckdb.DuckDBPyConnection,
    pull_id: int,
    series_count: int,
    obs_count: int,
    status: str = "completed",
    error: str | None = None,
) -> None:
    """Finalize a pull log entry."""
    conn.execute(
        "UPDATE pull_log SET series_count = ?, obs_count = ?, "
        "completed_at = current_timestamp, status = ?, error_message = ? WHERE id = ?",
        [series_count, obs_count, status, error, pull_id],
    )
