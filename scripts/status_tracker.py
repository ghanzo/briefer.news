#!/usr/bin/env python3
"""
status_tracker.py — daily project STATE + GOALS snapshot -> Memex rolling notes.

Part of the context-graph loop (Phase 1b). No `claude` calls (writes via
memex_client). Writes two rolling notes:
  - Projects/Briefer/Status.md : editions fresh? today's pipeline ran? subs, articles
  - Projects/Briefer/Goals.md  : progress toward the active goals

Usage:
  python3 scripts/status_tracker.py            # gather + write to Memex
  python3 scripts/status_tracker.py --dry-run  # gather + print, no write
"""
from __future__ import annotations
import datetime
import json
import os
import re
import subprocess
import sys

from memex_client import Memex

MEMEX_URL = "http://10.0.0.5:8765/mcp"
STATUS_NOTE = "Projects/Briefer/Status.md"
GOALS_NOTE = "Projects/Briefer/Goals.md"
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
GOALS_STATE = os.path.join(REPO, ".run", "goals_state.json")
PG = "briefer_postgres"
DRY = "--dry-run" in sys.argv


def sh(args, timeout=30):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:  # noqa: BLE001
        return 1, "", str(e)


def curl(url):
    rc, out, _ = sh(["/usr/bin/curl", "-s", "--max-time", "15", url])
    return out if rc == 0 else ""


def live(edition):
    html = curl(f"https://briefer.news/{edition}/")
    m = re.search(r'class="stamp">([^<]+)<', html)
    return (m.group(1).strip() if m else None), bool(html)


def file_has(path, needle):
    try:
        with open(path) as f:
            return needle.lower() in f.read().lower()
    except Exception:  # noqa: BLE001
        return False


def pg(query):
    rc, out, _ = sh(["docker", "exec", PG, "psql", "-U", "briefer", "-d", "briefer", "-tAc", query])
    return out.strip() if rc == 0 and out.strip() != "" else None


def pgint(query, default=0):
    try:
        return int(pg(query))
    except (TypeError, ValueError):
        return default


def yn(ok):
    return "✅" if ok else "❌"


def main():
    today = datetime.date.today()
    iso = today.isoformat()
    ymd = today.strftime("%Y%m%d")
    stamp_expect = f"{today.strftime('%B').upper()} {today.day}"  # e.g. "JUNE 8"

    us_stamp, _ = live("usa")
    cn_stamp, _ = live("china")
    us_fresh = bool(us_stamp and stamp_expect in us_stamp.upper())
    cn_fresh = bool(cn_stamp and stamp_expect in cn_stamp.upper())

    us_synth = file_has(os.path.join(REPO, "logs", f"synthesize-{ymd}.log"), "Synthesis complete")
    cn_synth = file_has(os.path.join(REPO, "logs", f"synthesize-china-{ymd}.log"), "complete")
    catchup = os.path.exists(os.path.join(REPO, ".run", f"catchup-{iso}.done"))
    critique = os.path.exists(os.path.join(REPO, ".run", f"critique-{ymd}.done"))

    subs = pgint("select count(*) from email_subscribers where status='confirmed' and unsubscribed_at is null")
    subs_total = pgint("select count(*) from email_subscribers")
    arts_today = pgint("select count(*) from articles where scraped_at::date = current_date")

    status_body = "\n".join([
        "# Briefer — Status\n",
        f"_Auto-updated {iso} by `scripts/status_tracker.py` (no Claude calls)._\n",
        "## Editions",
        f"- **US** {yn(us_fresh)} — live stamp `{us_stamp or 'unreachable'}`",
        f"- **China** {yn(cn_fresh)} — live stamp `{cn_stamp or 'unreachable'}`\n",
        "## Today's pipeline",
        f"- US synth {yn(us_synth)} · China synth {yn(cn_synth)} · midday catch-up {yn(catchup)} · critique {yn(critique)}\n",
        "## Data",
        f"- Confirmed subscribers: **{subs}** (of {subs_total} total signups)",
        f"- Articles scraped today: **{arts_today}**",
    ])

    try:
        gstate = json.load(open(GOALS_STATE))
    except Exception:  # noqa: BLE001
        gstate = {}
    hn_posted = bool(gstate.get("hn_posted"))
    hn_date = gstate.get("hn_date", "")
    pct = min(100, round(100 * subs / 30))
    bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
    goals_body = "\n".join([
        "# Briefer — Goals\n",
        f"_Auto-updated {iso}. Flip milestones by editing `.run/goals_state.json`._\n",
        "| Goal | Target | Now | Progress |",
        "|---|---|---|---|",
        f"| Email subscribers | 30 | {subs} | `{bar}` {pct}% {'✅ reached' if subs >= 30 else ''} |",
        f"| Post to Hacker News | launch | {('done ' + hn_date).strip() if hn_posted else 'not yet'} | {'✅' if hn_posted else '🟡 pending'} |",
    ])

    if DRY:
        print(status_body)
        print("\n" + "=" * 52 + "\n")
        print(goals_body)
        print("\n[dry-run] not writing to Memex")
        return

    if not os.path.exists(GOALS_STATE):
        try:
            os.makedirs(os.path.dirname(GOALS_STATE), exist_ok=True)
            json.dump({"hn_posted": False, "hn_date": ""}, open(GOALS_STATE, "w"), indent=2)
        except Exception:  # noqa: BLE001
            pass

    mx = Memex(MEMEX_URL)
    mx.initialize()
    mx.write_note(STATUS_NOTE, status_body, {"tags": ["briefer", "status", "auto"], "status": "active"})
    mx.write_note(GOALS_NOTE, goals_body, {"tags": ["briefer", "goals", "auto"], "status": "active"})
    print(f"wrote {STATUS_NOTE} + {GOALS_NOTE}; subs={subs}/30, arts_today={arts_today}")


if __name__ == "__main__":
    main()
