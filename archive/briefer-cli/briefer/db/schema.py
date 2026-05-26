"""DuckDB table definitions."""

import duckdb

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS series (
    series_id    VARCHAR PRIMARY KEY,
    source       VARCHAR NOT NULL,
    source_key   VARCHAR NOT NULL,
    name         VARCHAR NOT NULL,
    frequency    VARCHAR,
    units        VARCHAR,
    seasonal_adj VARCHAR,
    category     VARCHAR,
    last_updated TIMESTAMP,
    first_date   DATE,
    latest_date  DATE,
    latest_value DOUBLE,
    metadata     VARCHAR,
    created_at   TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS observations (
    series_id  VARCHAR NOT NULL,
    date       DATE NOT NULL,
    value      DOUBLE,
    pulled_at  TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (series_id, date)
);

CREATE TABLE IF NOT EXISTS pull_log (
    id              INTEGER PRIMARY KEY DEFAULT nextval('pull_log_seq'),
    source          VARCHAR NOT NULL,
    series_count    INTEGER DEFAULT 0,
    obs_count       INTEGER DEFAULT 0,
    started_at      TIMESTAMP DEFAULT current_timestamp,
    completed_at    TIMESTAMP,
    status          VARCHAR DEFAULT 'running',
    error_message   VARCHAR
);

CREATE TABLE IF NOT EXISTS analyses (
    id           INTEGER PRIMARY KEY DEFAULT nextval('analyses_seq'),
    scope        VARCHAR NOT NULL,
    context_json VARCHAR NOT NULL,
    analysis     VARCHAR NOT NULL,
    model_used   VARCHAR,
    created_at   TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS digests (
    id             INTEGER PRIMARY KEY DEFAULT nextval('digests_seq'),
    digest_date    DATE NOT NULL UNIQUE,
    headline       VARCHAR,
    body           VARCHAR,
    series_covered VARCHAR,
    model_used     VARCHAR,
    created_at     TIMESTAMP DEFAULT current_timestamp
);
"""


def ensure_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """Create all tables and sequences if they don't exist."""
    for seq in ("pull_log_seq", "analyses_seq", "digests_seq"):
        conn.execute(f"CREATE SEQUENCE IF NOT EXISTS {seq} START 1")
    conn.execute(SCHEMA_SQL)
