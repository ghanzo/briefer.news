#!/usr/bin/env python3
"""
reconfirm_pending.py — one re-confirmation nudge to PENDING subscribers whose
original confirmation email likely landed in spam.

Re-sends the SAME double-opt-in confirmation (raw MIME + List-Unsubscribe, via
email_api_server.send_confirmation) to people who submitted the signup form but
never confirmed. It does NOT auto-confirm anyone — they must still click the
link. Every recipient personally entered their address on briefer.news.

Safety rails:
  - only status='pending' (never confirmed / unsubscribed / bounced)
  - only rows created within --days (default 14)
  - skips anyone already nudged (notes marked) so re-runs never double-email
  - batched via --limit (default 25)
  - preflight ABORT if the recent SES bounce rate exceeds --max-bounce-rate
    (protects sender reputation, which is still recovering)
  - --dry-run prints the recipients and sends nothing

Usage:
  python3 scripts/reconfirm_pending.py --dry-run
  python3 scripts/reconfirm_pending.py --limit 25          # send one batch
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import email_subscribers as subs              # _psql / _esc DB helpers
from email_api_server import send_confirmation, AWS

MARK = "reconfirm sent"   # notes marker so a person is nudged at most once


def recent_bounce_rate() -> float:
    """Bounce rate (%) over the most recent slice of SES send data points."""
    try:
        raw = subprocess.check_output(
            [AWS, "ses", "get-send-statistics", "--region", "us-east-1", "--output", "json"],
            text=True, timeout=30)
        pts = sorted(json.loads(raw).get("SendDataPoints", []), key=lambda x: str(x["Timestamp"]))[-12:]
        sent = sum(p.get("DeliveryAttempts", 0) for p in pts)
        bounced = sum(p.get("Bounces", 0) for p in pts)
        return (100.0 * bounced / sent) if sent else 0.0
    except Exception as e:
        print(f"  WARN: could not read SES stats ({e}); proceeding without preflight")
        return 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--since", default="",
                    help="fixed cutoff date YYYY-MM-DD (created_at >=); overrides --days. "
                         "Use this for a multi-day campaign so a rolling window can't age "
                         "out the oldest signups before they're reached (newest are sent first).")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--max-bounce-rate", type=float, default=5.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.since:
        date_clause = f"created_at >= '{args.since}'::date"
        window = f"since={args.since}"
    else:
        date_clause = f"created_at > now() - interval '{args.days} days'"
        window = f"days={args.days}"

    sql = f"""SELECT json_agg(t) FROM (
      SELECT email, confirmation_token, unsubscribe_token
      FROM email_subscribers
      WHERE status='pending'
        AND {date_clause}
        AND COALESCE(notes,'') NOT LIKE '%{MARK}%'
      ORDER BY created_at DESC
      LIMIT {args.limit}
    ) t;"""
    rows = json.loads(subs._psql(sql) or "null") or []

    print(f"=== reconfirm_pending: {len(rows)} recipient(s) "
          f"({window}, limit={args.limit}, dry_run={args.dry_run}) ===")
    if not rows:
        print("  nothing to do (all caught up or none in window).")
        return 0

    if not args.dry_run:
        br = recent_bounce_rate()
        print(f"  recent SES bounce rate: {br:.1f}%  (abort threshold {args.max_bounce_rate}%)")
        if br > args.max_bounce_rate:
            print("  ABORT: bounce rate too high — protecting sender reputation. Retry later.")
            return 1

    sent = failed = 0
    for r in rows:
        if args.dry_run:
            print(f"  DRY-RUN would re-confirm: {r['email']}")
            continue
        ok = send_confirmation(r["email"], r["confirmation_token"], r.get("unsubscribe_token", "") or "")
        if ok:
            sent += 1
            subs._psql(
                "UPDATE email_subscribers SET "
                f"notes = COALESCE(notes,'') || ' | {MARK} {dt.date.today().isoformat()}', "
                f"updated_at=now() WHERE email='{subs._esc(r['email'])}';")
            print(f"  sent:   {r['email']}")
        else:
            failed += 1
            print(f"  FAILED: {r['email']}")
        time.sleep(1.5)   # gentle pacing

    print(f"=== done: sent={sent} failed={failed} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
