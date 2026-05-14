#!/usr/bin/env python3
"""
og_weekly_aggregate.py — Read the last 7 days of archived daily briefs
(both editions) and emit a JSON document collecting all Outside the Gate
items found.

Source of truth: the nginx docker volume `briefernewsapp_site_output`,
mounted at /usr/share/nginx/html/{usa,china}/archive/ in the running
`briefer_nginx` container.

Output JSON shape:
  {
    "week_start": "2026-05-08",
    "week_end":   "2026-05-14",
    "us":   [{date, source, letter, url, lead, desc, when_raw}, ...],
    "china":[{date, source, letter, url, lead, desc, when_raw}, ...]
  }

Sorted by date desc within each edition. Missing OG sections (older
briefs from before OG landed) are silently skipped.

Usage:
  python3 scripts/og_weekly_aggregate.py YYYY-MM-DD [output_path]
"""

from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUN_DIR = REPO / ".run"
NGINX_CONTAINER = "briefer_nginx"
ARCHIVE_BASE = "/usr/share/nginx/html"  # inside container

# Match an <ul class="outside-gate"> ... </ul> block; greedy enough to
# stop at the next </ul> closure even with nested <span> / <sup> tags.
OG_BLOCK_RE = re.compile(
    r'<ul class="outside-gate">(.+?)</ul>', re.DOTALL
)

# Match a single <li> inside an OG block; tolerant of attribute order
# and embedded HTML entities.
OG_LI_RE = re.compile(
    r'<li>\s*'
    r'<b>(?P<lead>[^<]+)</b>\s*'
    r'(?P<desc>.*?)'
    r'<sup>\s*<a[^>]*\bclass="cite"[^>]*\bhref="(?P<url>[^"]+)"'
    r'[^>]*\btitle="(?P<src_title>[^"]+)"[^>]*>(?P<letter>[a-z])</a>\s*</sup>'
    r'\s*<span class="when">(?P<when>[^<]+)</span>\s*'
    r'</li>',
    re.DOTALL,
)


def _list_archive_files(edition: str) -> list[str]:
    """Return list of archive HTML filenames for the edition (YYYY-MM-DD.html)."""
    try:
        out = subprocess.check_output(
            ["docker", "exec", NGINX_CONTAINER, "sh", "-c",
             f"ls {ARCHIVE_BASE}/{edition}/archive/ 2>/dev/null"],
            text=True, timeout=15,
        )
    except subprocess.CalledProcessError:
        return []
    except subprocess.TimeoutExpired:
        print(f"timeout listing {edition} archive", file=sys.stderr)
        return []
    return [n.strip() for n in out.splitlines() if re.match(r"^\d{4}-\d{2}-\d{2}\.html$", n.strip())]


def _read_archive_file(edition: str, filename: str) -> str:
    """Read a single archived brief from the nginx volume."""
    try:
        return subprocess.check_output(
            ["docker", "exec", NGINX_CONTAINER, "cat",
             f"{ARCHIVE_BASE}/{edition}/archive/{filename}"],
            text=True, timeout=15,
        )
    except subprocess.CalledProcessError:
        return ""
    except subprocess.TimeoutExpired:
        print(f"timeout reading {filename}", file=sys.stderr)
        return ""


def extract_og_items(html_text: str, brief_date: str) -> list[dict]:
    """Pull every <li> out of the Outside the Gate <ul> block."""
    block_match = OG_BLOCK_RE.search(html_text)
    if not block_match:
        return []
    block = block_match.group(1)
    items = []
    for m in OG_LI_RE.finditer(block):
        when_raw = html.unescape(m.group("when")).strip()
        # "May 12 · Reuters" — split on the middle-dot (rendered as · or &middot;)
        parts = re.split(r"\s*(?:·|·)\s*", when_raw, maxsplit=1)
        if len(parts) == 2:
            date_label, source = parts[0].strip(), parts[1].strip()
        else:
            date_label, source = when_raw, ""
        items.append({
            "date": brief_date,                       # brief publish date (YYYY-MM-DD)
            "letter": m.group("letter"),              # cite marker
            "url": html.unescape(m.group("url")),
            "lead": html.unescape(m.group("lead")).strip(),
            "desc": _clean_desc(m.group("desc")),
            "when_raw": when_raw,                     # original "May 12 · Reuters"
            "date_label": date_label,                 # "May 12"
            "source": source,                         # "Reuters"
            "src_title": html.unescape(m.group("src_title")).strip(),
        })
    return items


def _clean_desc(raw: str) -> str:
    """Strip stray whitespace + entities from the description fragment."""
    text = html.unescape(raw).strip()
    # collapse internal whitespace
    text = re.sub(r"\s+", " ", text)
    return text


def collect_edition(edition: str, today: date) -> list[dict]:
    """Walk the last 7 days of archived briefs for the edition; collect OG items."""
    files = _list_archive_files(edition)
    cutoff = today - timedelta(days=6)  # inclusive of today gives a 7-day window
    items: list[dict] = []
    for fname in files:
        try:
            brief_date = datetime.strptime(fname.removesuffix(".html"), "%Y-%m-%d").date()
        except ValueError:
            continue
        if brief_date < cutoff or brief_date > today:
            continue
        html_text = _read_archive_file(edition, fname)
        if not html_text:
            continue
        items.extend(extract_og_items(html_text, brief_date.isoformat()))
    # Sort by brief date desc; within a date, keep file order (already chronological per letter)
    items.sort(key=lambda it: it["date"], reverse=True)
    return items


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: og_weekly_aggregate.py YYYY-MM-DD [output_path]", file=sys.stderr)
        return 2
    try:
        today = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    except ValueError as e:
        print(f"bad date: {e}", file=sys.stderr)
        return 2

    week_start = today - timedelta(days=6)

    us_items = collect_edition("usa", today)
    china_items = collect_edition("china", today)

    out_doc = {
        "week_start": week_start.isoformat(),
        "week_end": today.isoformat(),
        "us": us_items,
        "china": china_items,
    }

    out_path: Path
    if len(sys.argv) >= 3:
        out_path = Path(sys.argv[2])
    else:
        RUN_DIR.mkdir(exist_ok=True)
        out_path = RUN_DIR / "og_weekly.json"

    out_path.write_text(json.dumps(out_doc, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"week {week_start} → {today}")
    print(f"  us:    {len(us_items)} item(s)")
    print(f"  china: {len(china_items)} item(s)")
    print(f"  wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
