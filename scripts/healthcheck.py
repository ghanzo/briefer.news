#!/usr/bin/env python3
"""
healthcheck.py — Verify both daily briefs actually published today.

Runs once a day from a LaunchAgent (~09:30 PDT, after the 08:00
daily_digests run has finished). For each edition:

  - Fetches briefer.news/usa/ and /china/.
  - Checks the response is HTTP 200 and non-trivially-sized.
  - Checks the date stamp on the page (<div class="stamp">) matches
    today's date — the format the synth emits is e.g. "MAY 22, 2026"
    (uppercase full month).

Writes a one-line status to logs/healthcheck-YYYYMMDD.log. On any
failure, also fires a macOS notification so the failure surfaces even
when you are not reading logs.

The synth scripts already fail gracefully — a broken run leaves
yesterday's brief in place. This check catches exactly that: silent
staleness, which is invisible until a reader notices.

Usage:
  python3 scripts/healthcheck.py
"""

from __future__ import annotations

import datetime
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOG_DIR = REPO / "logs"

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


def notify(title: str, message: str) -> None:
    """Fire a macOS notification. Best-effort; never fatal."""
    # Escape double-quotes for the AppleScript string literal.
    safe_msg = message.replace('"', '\\"')
    safe_title = title.replace('"', '\\"')
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{safe_msg}" with title "{safe_title}"'],
            timeout=10, check=False,
        )
    except Exception:
        pass


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


def main() -> int:
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
        notify("briefer.news health check FAILED", failures or status)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
