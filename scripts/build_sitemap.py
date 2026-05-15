#!/usr/bin/env python3
"""
build_sitemap.py — Generate sitemap.xml from the static page list + every
archived brief in the nginx volume.

Static pages:    fixed list with priority + changefreq
Dynamic pages:   walk the archive directories; one entry per dated HTML
                 file with <lastmod> from the file mtime

Output: .run/sitemap.xml

The site has no inbound links yet, so Googlebot has no easy path into
the archive entries. With this sitemap, the daily briefs + archive +
weekly + about + sources all get discovered and indexed faster.

Usage:
  python3 scripts/build_sitemap.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUN_DIR = REPO / ".run"
NGINX_CONTAINER = "briefer_nginx"
ARCHIVE_BASE = "/usr/share/nginx/html"
SITE = "https://briefer.news"

STATIC_PAGES = [
    # path,                  changefreq, priority
    ("/",                    "daily",    "0.9"),
    ("/about/",              "monthly",  "0.5"),
    ("/sources/",            "weekly",   "0.6"),
    ("/usa/",                "daily",    "1.0"),
    ("/china/",              "daily",    "1.0"),
    ("/usa/weekly/",         "daily",    "0.8"),
    ("/china/weekly/",       "daily",    "0.8"),
    ("/usa/archive/",        "daily",    "0.6"),
    ("/china/archive/",      "daily",    "0.6"),
]


def list_archive_with_mtime(rel_path: str) -> list[tuple[str, str]]:
    """Return [(filename, mtime ISO)] for dated HTML files in the volume directory."""
    try:
        out = subprocess.check_output(
            ["docker", "exec", NGINX_CONTAINER, "sh", "-c",
             # Use -e to print ISO mtime, then filename. ls -1 --time-style on busybox alpine.
             f"cd {ARCHIVE_BASE}/{rel_path} 2>/dev/null && ls -1 *.html 2>/dev/null | "
             f"while read f; do echo \"$(stat -c '%y' $f | cut -d' ' -f1)|$f\"; done"],
            text=True, timeout=20,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []
    rows: list[tuple[str, str]] = []
    for line in out.splitlines():
        if "|" not in line:
            continue
        mtime, fname = line.split("|", 1)
        if not re.match(r"^\d{4}-\d{2}-\d{2}\.html$", fname.strip()):
            continue
        rows.append((fname.strip(), mtime.strip()))
    return rows


def build_sitemap() -> str:
    today = date.today().isoformat()
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

    # Static pages
    for path, changefreq, priority in STATIC_PAGES:
        lines.append("  <url>")
        lines.append(f"    <loc>{SITE}{path}</loc>")
        lines.append(f"    <lastmod>{today}</lastmod>")
        lines.append(f"    <changefreq>{changefreq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")

    # Archive entries (date-stamped daily briefs)
    archive_sources = [
        ("usa/archive",   "/usa/archive"),
        ("china/archive", "/china/archive"),
        ("archive",       "/archive"),   # legacy pre-2026-05-12 single-edition era
    ]
    for rel, url_prefix in archive_sources:
        for fname, mtime in list_archive_with_mtime(rel):
            lines.append("  <url>")
            lines.append(f"    <loc>{SITE}{url_prefix}/{fname}</loc>")
            lines.append(f"    <lastmod>{mtime}</lastmod>")
            lines.append("    <changefreq>never</changefreq>")
            lines.append("    <priority>0.4</priority>")
            lines.append("  </url>")

    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main() -> int:
    RUN_DIR.mkdir(exist_ok=True)
    out_path = RUN_DIR / "sitemap.xml"
    xml = build_sitemap()
    out_path.write_text(xml, encoding="utf-8")
    n = xml.count("<url>")
    print(f"sitemap: {n} URLs · {len(xml)} bytes · {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
