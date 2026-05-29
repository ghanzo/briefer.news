#!/usr/bin/env python3
"""post_guard.py — one shared lock + length budget for the X posting path.

Both the daily drafter (drafter.sh) and the one-time launch tweet
(post_launch.py) auto-post to X. They used to coordinate via two *different*
mechanisms — drafter.sh counted today's x records, post_launch.py wrote a
sentinel file — so neither saw the other, and on 2026-05-28 both fired
(a daily post at 12:00 and a launch tweet 10 minutes later). This module is
the single source of truth both paths consult before they create a tweet.

Pure stdlib, importable. No tweepy, no network, no real side effects.

    from post_guard import x_posted_today, enforce_x_length

    if x_posted_today():          # scans today's posts ledger
        ...skip the X post...

    body = enforce_x_length(text, url)   # None if it won't fit X's budget
    if body is None:
        ...too long, skip/shorten...

Definitions match the existing ledger conventions:
  * A "post" is a posts-<date>.jsonl record with channel == "x" that is NOT an
    engagement snapshot (x_engagement_collector.py writes type == "engagement"
    rows into the same ledger; those are reads, not posts, and must not count).
  * X counts any URL as 23 chars regardless of length (t.co shortening). The X
    section's budget is 255 chars of pre-URL text; the URL + a separating
    newline are added on top, mirroring x_post.post()'s "text\\nurl" join and
    post_launch.py's MAX_TEXT = 255.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOGS = REPO / "logs"

# X t.co shortener: every URL counts as this many chars regardless of length.
TCO_URL_LEN = 23
# Pre-URL text budget the X section uses (matches post_launch.MAX_TEXT and the
# "255 characters or fewer" rule in drafter.sh's X-section prompt).
X_PRE_URL_BUDGET = 255


def _today(now: dt.datetime | dt.date | None = None) -> dt.date:
    if now is None:
        return dt.date.today()
    if isinstance(now, dt.datetime):
        return now.date()
    return now


def _ledger_path(now: dt.datetime | dt.date | None = None,
                 logs_dir: Path | None = None) -> Path:
    base = Path(logs_dir) if logs_dir is not None else LOGS
    return base / f"posts-{_today(now).isoformat()}.jsonl"


def x_posted_today(now: dt.datetime | dt.date | None = None,
                   logs_dir: Path | None = None) -> bool:
    """Return True if a real X post already went out today.

    Scans logs/posts-<today>.jsonl for any record with channel == "x" that is
    not an engagement snapshot (type == "engagement"). A missing or unreadable
    ledger means nothing has posted today -> False.

    `now` lets callers/tests pin "today"; `logs_dir` lets tests point at a tmp
    fixture instead of the real logs/ directory.
    """
    path = _ledger_path(now, logs_dir)
    if not path.exists():
        return False
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(rec, dict):
            continue
        if rec.get("channel") == "x" and rec.get("type") != "engagement":
            return True
    return False


def enforce_x_length(text: str, url: str | None = None) -> str | None:
    """Return `text` unchanged if it fits the X section's budget, else None.

    The X budget is X_PRE_URL_BUDGET (255) chars of pre-URL text. A URL, when
    present, is appended by the poster as "text\\nurl" and the URL itself
    counts as TCO_URL_LEN (23) chars regardless of its real length. The
    pre-URL text (including any trailing colon the X format requires) must fit
    the 255-char budget; the URL + newline ride on top of that, exactly as
    x_post.post() and post_launch.py compose it.

    Returns None ("too long") when the pre-URL text exceeds the budget. The URL
    is accepted as a parameter for call-site symmetry and to make the t.co
    accounting explicit, but a present URL never makes a within-budget text
    fail (it is always the fixed 23 chars the budget already accounts for).
    """
    if text is None:
        return None
    if len(text) > X_PRE_URL_BUDGET:
        return None
    return text


if __name__ == "__main__":
    # Tiny CLI so shell callers (drafter.sh) can consult the lock without
    # writing an inline python heredoc. Prints "1"/"0" and exits 0 either way
    # (the shell reads stdout; a crash must not be read as "not posted").
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "x_posted_today":
        print("1" if x_posted_today() else "0")
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "enforce_x_length":
        txt = sys.argv[2] if len(sys.argv) > 2 else ""
        u = sys.argv[3] if len(sys.argv) > 3 else None
        out = enforce_x_length(txt, u)
        print("FIT" if out is not None else "TOOLONG")
        sys.exit(0)
    print("usage: post_guard.py {x_posted_today|enforce_x_length TEXT [URL]}",
          file=sys.stderr)
    sys.exit(2)
