#!/usr/bin/env python3
"""
healthcheck.py — Verify both daily briefs actually published today, and
recover automatically when one is stale.

Runs once a day from a LaunchAgent (~09:30 PDT, after the 08:00
daily_digests run has finished). For each edition:

  - Fetches briefer.news/usa/ and /china/.
  - Checks the response is HTTP 200 and non-trivially-sized.
  - Checks the date stamp on the page (<div class="stamp">) matches
    today's date — the format the synth emits is e.g. "MAY 22, 2026"
    (uppercase full month).

Writes a one-line status to logs/healthcheck-YYYYMMDD.log. On a stale /
failed edition it does TWO things:

  1. Triggers recovery: shells out to scripts/synth_catchup.sh, which
     self-limits to at most one real synth per day via its own sentinel
     (so repeated healthcheck failures cannot burn the Claude quota).
  2. Notifies off-box via the shared notifier (scripts/alert.sh through
     notify.py — emails via SES + logs to logs/alerts.log), instead of
     the old Mac-only osascript banner that never left the box.

The synth scripts already fail gracefully — a broken run leaves
yesterday's brief in place. This check catches exactly that: silent
staleness, which is invisible until a reader notices.

Usage:
  python3 scripts/healthcheck.py
  python3 scripts/healthcheck.py --dry-run   # never run catchup or send a
                                             # real alert; pass --dry-run
                                             # through to both
"""

from __future__ import annotations

import datetime
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOG_DIR = REPO / "logs"
CATCHUP = REPO / "scripts" / "synth_catchup.sh"

# Import the shared off-box notifier (SES email + logs/alerts.log).
sys.path.insert(0, str(REPO / "scripts"))
try:
    from notify import notify  # type: ignore
except Exception:  # pragma: no cover - notifier must never break detection
    def notify(severity: str, message: str, dry_run: bool = False) -> bool:
        sys.stderr.write(f"notify import failed; would have sent [{severity}] {message}\n")
        return False

EDITIONS = [
    ("US",    "https://briefer.news/usa/"),
    ("China", "https://briefer.news/china/"),
]

STAMP_RE = re.compile(r'<div class="stamp">\s*([^<]+?)\s*</div>')


def fetch(url: str, timeout: int = 25) -> tuple[int, str]:
    """Return (status_code, body) or (0, '') on connection failure."""
    try:
        result = subprocess.run(
            ["curl", "-sSL", "-m", str(timeout), "-w", "\n%{http_code}", url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0, ""
    out = result.stdout or ""
    body, _, status = out.rpartition("\n")
    try:
        return int(status), body
    except ValueError:
        return 0, ""


def expected_stamp(today: datetime.date) -> str:
    """Match the synth's date-stamp format, e.g. 'MAY 22, 2026'."""
    return f"{today.strftime('%B').upper()} {today.day}, {today.year}"


def trigger_catchup(dry_run: bool = False) -> tuple[bool, str]:
    """Shell out to synth_catchup.sh to recover a stale brief.

    synth_catchup.sh self-limits to at most one real synth per calendar day
    via its own sentinel file, so calling it on every healthcheck failure is
    safe — a second call the same day is a no-op. Returns (ok, summary).
    Never raises: recovery is best-effort and must not crash the alert path.
    """
    if not CATCHUP.exists():
        return False, f"catchup script missing at {CATCHUP}"
    cmd = ["bash", str(CATCHUP)]
    if dry_run:
        cmd.append("--dry-run")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    except subprocess.TimeoutExpired:
        return False, "catchup timed out after 1800s"
    except Exception as e:  # pragma: no cover - defensive
        return False, f"catchup failed to launch: {e}"
    tail = (r.stdout or r.stderr or "").strip().splitlines()
    last = tail[-1] if tail else "(no output)"
    ok = r.returncode == 0
    return ok, f"catchup rc={r.returncode}: {last}"


def check_edition(name: str, url: str, today: datetime.date) -> tuple[bool, str]:
    code, body = fetch(url)
    if code != 200:
        return False, f"{name}: HTTP {code} (fetch failed)"
    if len(body) < 5000:
        return False, f"{name}: page is {len(body)} bytes (too small — partial fetch?)"
    m = STAMP_RE.search(body)
    if not m:
        return False, f"{name}: no <div class=\"stamp\"> on the page"
    stamp = m.group(1).strip()
    expected = expected_stamp(today)
    if stamp != expected:
        return False, f"{name}: stamp is '{stamp}', expected '{expected}'"
    return True, f"{name}: OK ({stamp})"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    dry_run = "--dry-run" in argv

    LOG_DIR.mkdir(exist_ok=True)
    now = datetime.datetime.now()
    today = now.date()
    log_path = LOG_DIR / f"healthcheck-{today:%Y%m%d}.log"

    results: list[str] = []
    all_ok = True
    for name, url in EDITIONS:
        ok, msg = check_edition(name, url, today)
        if not ok:
            all_ok = False
        results.append(msg)

    status = "OK" if all_ok else "FAIL"
    line = f"[{now:%Y-%m-%d %H:%M:%S}] {status} — " + " · ".join(results)
    print(line)
    with log_path.open("a") as f:
        f.write(line + "\n")

    if not all_ok:
        failures = " | ".join(r for r in results if ": OK" not in r)
        # 1. Trigger recovery. synth_catchup.sh self-limits to one synth/day,
        #    so this is safe to call on every failure.
        recov_ok, recov_msg = trigger_catchup(dry_run=dry_run)
        recov_line = f"[{now:%Y-%m-%d %H:%M:%S}] RECOVERY — {recov_msg}"
        print(recov_line)
        with log_path.open("a") as f:
            f.write(recov_line + "\n")
        # 2. Notify off-box via the shared notifier (SES + logs/alerts.log),
        #    replacing the old Mac-only osascript banner.
        severity = "crit"
        alert_msg = (
            f"briefer.news health check FAILED — {failures or status}\n"
            f"recovery: {recov_msg}"
        )
        notify(severity, alert_msg, dry_run=dry_run)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
