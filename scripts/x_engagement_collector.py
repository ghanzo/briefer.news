#!/usr/bin/env python3
"""
x_engagement_collector.py — snapshot engagement on our autonomous X posts.

Runs a few times a day (LaunchAgent news.briefer.engagement). For every X
post we made in the last ~48h (recorded in logs/posts-*.jsonl), it fetches
current public metrics (likes, reposts, replies, quotes, impressions) and
appends a typed "engagement" snapshot line to today's posts log.

The Researcher and Analyzer already read logs/posts-*.jsonl, so these
snapshots feed the growth loop with no other wiring. Multiple snapshots per
post accumulate over its first 48h (a simple growth curve); the Analyzer can
take the most-aged snapshot per tweet as the final number.

CLI:
    python3 scripts/x_engagement_collector.py            # collect + append
    python3 scripts/x_engagement_collector.py --dry-run  # print, don't write
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x_post  # reuse _client() + load_env()

REPO = Path(__file__).resolve().parent.parent
LOGS = REPO / "logs"

MAX_AGE_HOURS = 48   # stop snapshotting once a post is older than this
SCAN_DAYS = 3        # how many days of posts-*.jsonl to scan back


def _parse_ts(s: str):
    try:
        return dt.datetime.fromisoformat(s)
    except Exception:
        return None


def collect_targets(now: dt.datetime) -> dict:
    """Return {tweet_id: (post_record, posted_at, age_hours)} for X posts
    younger than MAX_AGE_HOURS, skipping prior engagement snapshots."""
    targets = {}
    for d in range(SCAN_DAYS + 1):
        day = (now.date() - dt.timedelta(days=d)).isoformat()
        f = LOGS / f"posts-{day}.jsonl"
        if not f.exists():
            continue
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("type") == "engagement":      # don't re-snapshot snapshots
                continue
            if rec.get("channel") != "x":
                continue
            tid = (rec.get("result") or {}).get("tweet_id")
            if not tid:
                continue
            ts = _parse_ts(rec.get("timestamp", ""))
            if ts is None:
                continue
            age_h = (now - ts).total_seconds() / 3600.0
            if age_h > MAX_AGE_HOURS:
                continue
            targets[str(tid)] = (rec, ts, age_h)
    return targets


def fetch_metrics(ids: list[str]) -> dict:
    client = x_post._client()
    out = {}
    for i in range(0, len(ids), 100):  # X allows up to 100 ids per call
        resp = client.get_tweets(
            ids=ids[i:i + 100],
            tweet_fields=["public_metrics"],
            user_auth=True,
        )
        for t in (resp.data or []):
            out[str(t.id)] = dict(t.public_metrics or {})
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="print metrics without appending to the log")
    args = ap.parse_args(argv)

    now = dt.datetime.now()
    targets = collect_targets(now)
    if not targets:
        print(f"No X posts in the last {MAX_AGE_HOURS}h to snapshot.")
        return 0

    metrics = fetch_metrics(list(targets.keys()))
    out_path = LOGS / f"posts-{now.date().isoformat()}.jsonl"
    snaps = []
    for tid, (rec, ts, age_h) in targets.items():
        m = metrics.get(tid)
        if m is None:
            print(f"  {tid}: no metrics (deleted or not visible)")
            continue
        eng = (m.get("like_count", 0) + m.get("retweet_count", 0)
               + m.get("reply_count", 0) + m.get("quote_count", 0))
        snaps.append({
            "channel": "x",
            "type": "engagement",
            "tweet_id": tid,
            "url": (rec.get("result") or {}).get("url") or rec.get("url"),
            "post_text": (rec.get("text") or "")[:80],
            "post_timestamp": rec.get("timestamp"),
            "age_hours": round(age_h, 1),
            "metrics": m,
            "timestamp": now.isoformat(),
        })
        print(f"  {tid} (~{age_h:.0f}h): {m.get('impression_count', '?')} impressions, "
              f"{eng} engagements (likes={m.get('like_count', 0)} "
              f"reposts={m.get('retweet_count', 0)} replies={m.get('reply_count', 0)})")

    if args.dry_run:
        print(f"[dry-run] would append {len(snaps)} snapshot(s) to {out_path}")
        return 0

    with out_path.open("a") as fh:
        for snap in snaps:
            fh.write(json.dumps(snap) + "\n")
    print(f"Appended {len(snaps)} engagement snapshot(s) to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
