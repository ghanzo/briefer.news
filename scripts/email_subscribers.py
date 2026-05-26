#!/usr/bin/env python3
"""
email_subscribers.py — Helpers for the self-built email subscriber list.

Thin wrapper over `docker exec briefer_postgres psql` (same pattern as
the rest of the project's pg access — keeps the dependency footprint
small). Used by the signup form backend, the daily-send pipeline, the
unsubscribe endpoint, and bounce-handler.

Functions:
  add_subscriber(email)        — create pending row + return confirmation token
  confirm_subscriber(token)    — pending → confirmed
  unsubscribe(token)           — confirmed → unsubscribed
  list_confirmed(edition)      — emails currently subscribed to that edition
  mark_bounced(email)          — confirmed → bounced (called by SNS handler)
  get(email)                   — lookup by email

CLI:
  python3 scripts/email_subscribers.py add foo@bar.com
  python3 scripts/email_subscribers.py list
"""

from __future__ import annotations

import json
import re
import secrets
import subprocess
import sys


DOCKER = "/usr/local/bin/docker"
CONTAINER = "briefer_postgres"
DB = "briefer"
USER = "briefer"


_COMMAND_TAG = re.compile(r"^(INSERT|UPDATE|DELETE|MERGE|COPY)\s+\d+(\s+\d+)?\s*$")

def _psql(sql: str) -> str:
    """Run a SQL statement and return stdout (psql -tA — tuple-only, unaligned).

    Strips trailing command-tag lines (e.g. 'UPDATE 0') that psql emits for
    DML even in -tA mode — they pollute JSON parsing when RETURNING yields
    zero rows."""
    raw = subprocess.check_output(
        [DOCKER, "exec", CONTAINER, "psql", "-U", USER, "-d", DB, "-tA", "-c", sql],
        text=True, timeout=15,
    )
    lines = [ln for ln in raw.splitlines() if not _COMMAND_TAG.match(ln)]
    return "\n".join(lines).strip()


def _psql_json(sql: str) -> list[dict]:
    """Run a SQL that returns JSON; parse to list of dicts."""
    raw = _psql(sql)
    if not raw or raw == "":
        return []
    return json.loads(raw)


def _make_token() -> str:
    """URL-safe random token, ~32 chars."""
    return secrets.token_urlsafe(24)


def _esc(s: str) -> str:
    """Escape single quotes for SQL literal embedding."""
    return s.replace("'", "''")


# ── Public API ──────────────────────────────────────────────────────────────

def add_subscriber(email: str, edition: str = "both", notes: str = "") -> dict:
    """Create a pending subscriber. Returns the confirmation token.
    The caller emails the token-link to the subscriber to complete double opt-in.
    If the email already exists, returns the existing record without changes."""
    email = email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise ValueError(f"invalid email: {email}")

    # Check for existing
    existing = get(email)
    if existing:
        return existing

    confirm_tok = _make_token()
    unsub_tok = _make_token()
    sql = f"""
        INSERT INTO email_subscribers
            (email, status, confirmation_token, unsubscribe_token, edition_preference, notes)
        VALUES
            ('{_esc(email)}', 'pending', '{confirm_tok}', '{unsub_tok}',
             '{_esc(edition)}', NULLIF('{_esc(notes)}', ''))
        RETURNING json_build_object(
            'id', id, 'email', email, 'status', status,
            'confirmation_token', confirmation_token,
            'unsubscribe_token', unsubscribe_token,
            'edition_preference', edition_preference,
            'created_at', created_at::text);
    """
    out = _psql(sql)
    return json.loads(out) if out else {}


def confirm_subscriber(confirmation_token: str) -> dict | None:
    """Promote a pending row to confirmed by token. Returns the row or None."""
    sql = f"""
        UPDATE email_subscribers
        SET status = 'confirmed', confirmed_at = NOW(),
            confirmation_token = NULL
        WHERE confirmation_token = '{_esc(confirmation_token)}'
          AND status = 'pending'
        RETURNING json_build_object(
            'id', id, 'email', email, 'status', status,
            'confirmed_at', confirmed_at::text,
            'edition_preference', edition_preference);
    """
    out = _psql(sql)
    return json.loads(out) if out else None


def unsubscribe(unsubscribe_token: str) -> dict | None:
    """Mark a subscriber unsubscribed by their stable unsubscribe token."""
    sql = f"""
        UPDATE email_subscribers
        SET status = 'unsubscribed', unsubscribed_at = NOW()
        WHERE unsubscribe_token = '{_esc(unsubscribe_token)}'
          AND status IN ('confirmed', 'pending')
        RETURNING json_build_object(
            'id', id, 'email', email, 'status', status,
            'unsubscribed_at', unsubscribed_at::text);
    """
    out = _psql(sql)
    return json.loads(out) if out else None


def mark_bounced(email: str) -> dict | None:
    """Mark a subscriber bounced (called by the SES SNS handler on hard bounce)."""
    sql = f"""
        UPDATE email_subscribers
        SET status = 'bounced'
        WHERE email = '{_esc(email.strip().lower())}'
        RETURNING json_build_object(
            'id', id, 'email', email, 'status', status);
    """
    out = _psql(sql)
    return json.loads(out) if out else None


def get(email: str) -> dict | None:
    """Look up a subscriber by email."""
    sql = f"""
        SELECT row_to_json(s) FROM (
            SELECT id, email, status, edition_preference,
                   confirmation_token, unsubscribe_token,
                   confirmed_at::text, unsubscribed_at::text, created_at::text
            FROM email_subscribers
            WHERE email = '{_esc(email.strip().lower())}'
        ) s;
    """
    out = _psql(sql)
    return json.loads(out) if out else None


def list_confirmed(edition: str | None = None) -> list[dict]:
    """List currently-confirmed subscribers. Filter by edition if given.
    'both' subscribers always included regardless of edition filter."""
    where = "status = 'confirmed'"
    if edition in ("us", "china"):
        where += f" AND edition_preference IN ('{edition}', 'both')"
    sql = f"""
        SELECT COALESCE(json_agg(row_to_json(s)), '[]'::json) FROM (
            SELECT id, email, edition_preference,
                   confirmed_at::text, unsubscribe_token
            FROM email_subscribers
            WHERE {where}
            ORDER BY confirmed_at
        ) s;
    """
    return json.loads(_psql(sql))


def count_by_status() -> dict[str, int]:
    sql = """
        SELECT json_object_agg(status, n) FROM (
            SELECT status, COUNT(*) AS n FROM email_subscribers GROUP BY status
        ) s;
    """
    out = _psql(sql)
    return json.loads(out) if out else {}


# ── CLI ─────────────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__); return 2
    cmd = argv[1]

    if cmd == "add" and len(argv) >= 3:
        edition = argv[3] if len(argv) >= 4 else "both"
        sub = add_subscriber(argv[2], edition=edition)
        print(json.dumps(sub, indent=2))
        return 0

    if cmd == "confirm" and len(argv) >= 3:
        result = confirm_subscriber(argv[2])
        print(json.dumps(result, indent=2) if result else "(no pending subscriber with that token)")
        return 0

    if cmd == "unsubscribe" and len(argv) >= 3:
        result = unsubscribe(argv[2])
        print(json.dumps(result, indent=2) if result else "(no matching subscriber)")
        return 0

    if cmd == "get" and len(argv) >= 3:
        result = get(argv[2])
        print(json.dumps(result, indent=2) if result else "(not found)")
        return 0

    if cmd == "list":
        edition = argv[2] if len(argv) >= 3 else None
        rows = list_confirmed(edition)
        for r in rows:
            print(f"  {r['email']:40s}  edition={r['edition_preference']:6s}  confirmed={r['confirmed_at']}")
        print(f"\n{len(rows)} confirmed subscribers" + (f" (edition={edition})" if edition else ""))
        return 0

    if cmd == "counts":
        print(json.dumps(count_by_status(), indent=2))
        return 0

    print(f"unknown command: {cmd}")
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
