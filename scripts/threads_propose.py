#!/usr/bin/env python3
"""
threads_propose.py — Stage 1 of the auto-thread proposer.

Reads the past 14 days of archived daily briefs (both editions),
extracts the bold lead phrase from each bullet, groups by date +
edition, and writes a structured collection file that Claude reads
in Stage 2 to propose candidate long-arc threads.

Output: .run/threads_collected.md

Stage 2 (the Claude analysis) is driven by scripts/threads_propose.sh,
which calls this script then invokes Claude with a prompt that asks
for candidate threads not already in pipeline/config/threads.yaml.
The Claude output goes to .run/threads_proposed.md for editor review.
NEVER auto-merged into threads.yaml.

Usage:
  python3 scripts/threads_propose.py [YYYY-MM-DD]
"""

from __future__ import annotations

import html as html_lib
import re
import subprocess
import sys
from datetime import datetime, timedelta, date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUN_DIR = REPO / ".run"
NGINX_CONTAINER = "briefer_nginx"
ARCHIVE_BASE = "/usr/share/nginx/html"

BULLET_LEAD_RE = re.compile(
    r'<li>\s*<b>([^<]+)</b>\s*([^<]*)',
    re.DOTALL,
)
HEADLINE_RE = re.compile(r'<h2 class="headline">\s*(.+?)\s*</h2>', re.DOTALL)


def _list_archive(rel_path: str) -> list[str]:
    try:
        out = subprocess.check_output(
            ["docker", "exec", NGINX_CONTAINER, "sh", "-c",
             f"ls {ARCHIVE_BASE}/{rel_path}/ 2>/dev/null"],
            text=True, timeout=15,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []
    return [n.strip() for n in out.splitlines()
            if re.match(r"^\d{4}-\d{2}-\d{2}\.html$", n.strip())]


def _read_archive(rel_path: str, filename: str) -> str:
    try:
        return subprocess.check_output(
            ["docker", "exec", NGINX_CONTAINER, "cat",
             f"{ARCHIVE_BASE}/{rel_path}/{filename}"],
            text=True, timeout=15,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(s)).strip()


def extract_briefs(rel_path: str, today: date, days: int) -> list[dict]:
    cutoff = today - timedelta(days=days - 1)
    out: list[dict] = []
    for fname in _list_archive(rel_path):
        try:
            d = datetime.strptime(fname.removesuffix(".html"), "%Y-%m-%d").date()
        except ValueError:
            continue
        if d < cutoff or d > today:
            continue
        html = _read_archive(rel_path, fname)
        if not html:
            continue
        headline_m = HEADLINE_RE.search(html)
        bullets = []
        # Scope bullet extraction to the items <ul> only
        items_m = re.search(r'<ul class="items">(.+?)</ul>', html, re.DOTALL)
        if items_m:
            for m in BULLET_LEAD_RE.finditer(items_m.group(1)):
                lead = _clean(m.group(1))
                snippet = _clean(m.group(2))[:80]
                bullets.append({"lead": lead, "snippet": snippet})
        out.append({
            "date": d.isoformat(),
            "headline": _clean(headline_m.group(1)) if headline_m else "",
            "bullets": bullets,
        })
    out.sort(key=lambda b: b["date"], reverse=True)
    return out


def main() -> int:
    if len(sys.argv) >= 2:
        today = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    else:
        today = date.today()

    us = extract_briefs("usa/archive", today, days=14)
    cn = extract_briefs("china/archive", today, days=14)

    lines = ["# Collected bullets · past 14 days", ""]
    lines.append(f"Generated: {today.isoformat()}")
    lines.append("")
    lines.append("## U.S. edition")
    if not us:
        lines.append("_no archived briefs in window_")
    for b in us:
        lines.append(f"\n### {b['date']}")
        if b["headline"]:
            lines.append(f"**Headline:** {b['headline']}")
        for bl in b["bullets"]:
            lines.append(f"- {bl['lead']} — _{bl['snippet']}_")

    lines.append("\n## China edition")
    if not cn:
        lines.append("_no archived briefs in window_")
    for b in cn:
        lines.append(f"\n### {b['date']}")
        if b["headline"]:
            lines.append(f"**Headline:** {b['headline']}")
        for bl in b["bullets"]:
            lines.append(f"- {bl['lead']} — _{bl['snippet']}_")

    RUN_DIR.mkdir(exist_ok=True)
    out_path = RUN_DIR / "threads_collected.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    total_bullets = sum(len(b["bullets"]) for b in us) + sum(len(b["bullets"]) for b in cn)
    print(f"collected {len(us)} US briefs + {len(cn)} China briefs · {total_bullets} bullets total")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
