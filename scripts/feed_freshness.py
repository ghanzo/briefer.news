#!/usr/bin/env python3
"""
feed_freshness.py — catch silently-stale sources before they hollow out the brief.

The failure this exists for: a source's feed stops delivering new items while
its website keeps publishing — either it emits nothing (discovered=0) or it
freezes on the same old items (discovered>0 but nothing new is ever stored).
Both look identical to "quiet news day" and are invisible until a human
notices the brief got thin. There was no detector for it. This is that
detector.

Signal: we key off articles.scraped_at — *when we last ingested a NEW item*
from each active source — NOT publish_date. scraped_at is the honest "is this
source still feeding us" axis: a frozen feed that only re-serves old items
inserts no new rows (dedup by url_hash), so its newest scraped_at stops
advancing, while a backdated article we just pulled still counts as fresh
(publish_date would wrongly call it stale).

Buckets (per active source, after a creation grace window):
  NEVER  — 0 articles ever            → config almost certainly broken
  DEAD   — silent >= DEAD_DAYS (30)   → long gone; high confidence something broke
  STALE  — silent >= STALE_DAYS (10)  → recently went quiet; worth a look
  OK     — produced within STALE_DAYS

Why thresholds and not a cadence model: with ~14-day retention the per-source
history is too short to fit a reliable cadence (most sources show 1-3 distinct
scrape-days), so a median-gap model would be noise. Instead we use plain day
thresholds plus two noise controls:
  1. STATE DIFF — only NEW entrants to the flagged set trigger an off-box
     alert, so a known backlog is reported once, not re-nagged every day.
  2. IGNORE LIST — BRIEFER_FRESHNESS_IGNORE (comma-separated source names) for
     genuinely low-cadence sources (e.g. Treaties/TIAS) you've confirmed are
     fine. They still appear in the dated report, just never alert.

Delivery mirrors healthcheck.py: a dated full report to logs/, and an off-box
alert via the shared notifier (scripts/alert.sh -> SES email) ONLY when new
sources go stale. If the watchdog itself can't read the DB it alerts crit —
a blind watchdog must never fail silently.

Usage:
  python3 scripts/feed_freshness.py                 # report + alert on new staleness
  python3 scripts/feed_freshness.py --report-only    # print report, no alert, no state write
  python3 scripts/feed_freshness.py --dry-run        # detect + build alert but never send / write state

Env overrides (all optional):
  STALE_DAYS=10  DEAD_DAYS=30  GRACE_DAYS=4
  BRIEFER_FRESHNESS_IGNORE="State Dept — Treaties (TIAS),Some Other Source"
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOG_DIR = REPO / "logs"
STATE_FILE = LOG_DIR / "feed-freshness-state.json"

# PATH is not set under launchd, so hardcode absolutes (same reason alert.sh
# hardcodes the aws path). docker exec into the running postgres is how the
# rest of the system reaches the DB from the host without a DB driver.
DOCKER = os.environ.get("DOCKER_BIN", "/usr/local/bin/docker")
PG_CONTAINER = os.environ.get("PG_CONTAINER", "briefer_postgres")
PG_USER = os.environ.get("PG_USER", "briefer")
PG_DB = os.environ.get("PG_DB", "briefer")

STALE_DAYS = int(os.environ.get("STALE_DAYS", "10"))
DEAD_DAYS = int(os.environ.get("DEAD_DAYS", "30"))
GRACE_DAYS = int(os.environ.get("GRACE_DAYS", "4"))
IGNORE = {
    n.strip()
    for n in os.environ.get("BRIEFER_FRESHNESS_IGNORE", "").split(",")
    if n.strip()
}

# Import the shared off-box notifier (SES email + logs/alerts.log). Mirrors
# healthcheck.py: the notifier must never break detection, so degrade to a
# stderr stub if it can't be imported.
sys.path.insert(0, str(REPO / "scripts"))
try:
    from notify import notify  # type: ignore
except Exception:  # pragma: no cover
    def notify(severity: str, message: str, dry_run: bool = False) -> bool:
        sys.stderr.write(f"notify import failed; would send [{severity}] {message}\n")
        return False


# One aggregate query — per active source, everything we need to classify it.
# days_since_newest is NULL for sources with zero articles (LEFT JOIN), which
# parse_rows() maps to None.
QUERY = """
SELECT
  s.name,
  s.category,
  EXTRACT(DAY FROM (now() - s.created_at))::int                           AS created_days_ago,
  COUNT(a.id)                                                             AS total,
  COUNT(a.id) FILTER (WHERE a.scraped_at >= now() - interval '7 days')    AS last7,
  COUNT(DISTINCT a.scraped_at::date)                                      AS distinct_days,
  (CURRENT_DATE - MAX(a.scraped_at)::date)                                AS days_since_newest
FROM sources s
LEFT JOIN articles a ON a.source_id = s.id
WHERE s.active = true
GROUP BY s.name, s.category, s.created_at
ORDER BY days_since_newest DESC NULLS FIRST, s.name;
"""


class WatchdogError(RuntimeError):
    """The watchdog could not read the DB — alert crit, do not fail silently."""


def query_db() -> list[dict]:
    """Run the aggregate query via docker exec psql; return parsed rows."""
    cmd = [
        DOCKER, "exec", PG_CONTAINER,
        "psql", "-U", PG_USER, "-d", PG_DB, "-tA", "-F", "|", "-c", QUERY,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except Exception as e:
        raise WatchdogError(f"could not exec docker/psql: {e}") from e
    if r.returncode != 0:
        raise WatchdogError(f"psql exited {r.returncode}: {(r.stderr or r.stdout).strip()[:300]}")
    return parse_rows(r.stdout)


def parse_rows(out: str) -> list[dict]:
    rows = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) != 7:
            continue  # skip anything that isn't a clean data row
        name, category, created, total, last7, distinct, days = parts
        rows.append({
            "name": name,
            "category": category,
            "created_days_ago": _int(created),
            "total": _int(total) or 0,
            "last7": _int(last7) or 0,
            "distinct_days": _int(distinct) or 0,
            "days_since_newest": _int(days),  # None when total == 0
        })
    return rows


def _int(s: str):
    s = (s or "").strip()
    if s == "":
        return None
    try:
        return int(s)
    except ValueError:
        return None


def classify(row: dict) -> str:
    """Return one of: NEVER, DEAD, STALE, OK, GRACE, IGNORED."""
    if row["name"] in IGNORE:
        return "IGNORED"
    created = row["created_days_ago"]
    if created is not None and created < GRACE_DAYS:
        return "GRACE"  # too new to judge; verify-after-first-scrape owns it
    if row["total"] == 0:
        return "NEVER"
    days = row["days_since_newest"]
    if days is None:
        return "NEVER"
    if days >= DEAD_DAYS:
        return "DEAD"
    if days >= STALE_DAYS:
        return "STALE"
    return "OK"


# Buckets that represent a problem a human should see.
FLAGGED = ("NEVER", "DEAD", "STALE")


def build_report(rows: list[dict], buckets: dict[str, list[dict]]) -> str:
    today = dt.date.today().isoformat()
    n_active = len(rows)
    n_flagged = sum(len(buckets[b]) for b in FLAGGED)
    lines = [
        f"feed-freshness report — {today}",
        f"active sources: {n_active}   flagged: {n_flagged}   "
        f"(NEVER={len(buckets['NEVER'])} DEAD={len(buckets['DEAD'])} "
        f"STALE={len(buckets['STALE'])} OK={len(buckets['OK'])} "
        f"GRACE={len(buckets['GRACE'])} IGNORED={len(buckets['IGNORED'])})",
        f"thresholds: STALE>={STALE_DAYS}d  DEAD>={DEAD_DAYS}d  grace<{GRACE_DAYS}d",
        "",
    ]
    for b in ("NEVER", "DEAD", "STALE"):
        if not buckets[b]:
            continue
        lines.append(f"── {b} ──")
        for r in buckets[b]:
            d = r["days_since_newest"]
            dtxt = "never" if d is None else f"{d}d silent"
            lines.append(
                f"  [{r['category']}] {r['name']}  —  {dtxt}, "
                f"{r['total']} arts, last7={r['last7']}, created {r['created_days_ago']}d ago"
            )
        lines.append("")
    if buckets["IGNORED"]:
        lines.append("── IGNORED (low-cadence allowlist) ──")
        for r in buckets["IGNORED"]:
            lines.append(f"  {r['name']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"flagged": {}}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {"flagged": {}}


def main() -> int:
    ap = argparse.ArgumentParser(description="briefer.news feed-freshness watchdog")
    ap.add_argument("--dry-run", action="store_true",
                    help="detect + build alert but never send or persist state")
    ap.add_argument("--report-only", action="store_true",
                    help="print the report only; no alert, no state write")
    args = ap.parse_args()

    LOG_DIR.mkdir(exist_ok=True)
    today = dt.date.today().isoformat()

    try:
        rows = query_db()
    except WatchdogError as e:
        msg = f"feed-freshness watchdog could NOT read the DB: {e}"
        sys.stderr.write(msg + "\n")
        if not args.report_only:
            notify("crit", msg, dry_run=args.dry_run)
        return 2

    buckets = {b: [] for b in ("NEVER", "DEAD", "STALE", "OK", "GRACE", "IGNORED")}
    for r in rows:
        buckets[classify(r)].append(r)

    report = build_report(rows, buckets)
    print(report)

    report_path = LOG_DIR / f"feed-freshness-{today.replace('-', '')}.log"
    report_path.write_text(report)

    if args.report_only:
        return 0

    # State diff: only NEW entrants to the flagged set warrant an off-box alert.
    flagged_now = {}
    for b in FLAGGED:
        for r in buckets[b]:
            flagged_now[r["name"]] = {
                "bucket": b,
                "days": r["days_since_newest"],
                "category": r["category"],
            }

    prior = load_state().get("flagged", {})
    new_names = [n for n in flagged_now if n not in prior]
    recovered = [n for n in prior if n not in flagged_now]

    if new_names:
        lines = [f"{len(new_names)} source(s) newly stale (active feeds not delivering):", ""]
        for n in new_names:
            info = flagged_now[n]
            d = info["days"]
            dtxt = "never produced" if d is None else f"{d}d since last new item"
            lines.append(f"  [{info['bucket']}] {n} — {dtxt}")
        if recovered:
            lines.append("")
            lines.append(f"recovered since last run: {', '.join(recovered)}")
        lines += [
            "",
            f"full report: {report_path}",
            "investigate: docker exec briefer_postgres psql -U briefer -d briefer "
            "(see scripts/feed_freshness.py for the freshness query)",
        ]
        notify("warn", "\n".join(lines), dry_run=args.dry_run)
    else:
        print(f"[feed_freshness] no newly-stale sources (flagged={len(flagged_now)}, "
              f"recovered={len(recovered)}) — no alert sent")

    # Persist the current flagged set (carry first_seen forward) unless dry-run.
    if not args.dry_run:
        carried = {}
        for n, info in flagged_now.items():
            first_seen = prior.get(n, {}).get("first_seen", today)
            carried[n] = {**info, "first_seen": first_seen}
        STATE_FILE.write_text(json.dumps(
            {"updated": today, "flagged": carried}, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
