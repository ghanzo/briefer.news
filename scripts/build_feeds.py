#!/usr/bin/env python3
"""
build_feeds.py — Generate per-edition RSS 2.0 feeds from the archived
daily briefs in the nginx volume.

Each archived brief becomes one <item>: the headline as the title, the
dek plus the Events bullets as the description, the archive permalink
as link + guid, and the brief's date as pubDate.

A daily brief is an ideal RSS product — this feed is the site's
returning-reader hook: a visitor can subscribe once and get every
morning's brief in their reader.

Output:
  .run/feed_usa.xml    — https://briefer.news/usa/feed.xml
  .run/feed_china.xml  — https://briefer.news/china/feed.xml

Reads the archive via the same docker-exec-into-nginx pattern as
archive_index.py and build_sitemap.py.

Usage:
  python3 scripts/build_feeds.py
"""

from __future__ import annotations

import html as html_lib
import re
import subprocess
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUN_DIR = REPO / ".run"
NGINX_CONTAINER = "briefer_nginx"
ARCHIVE_BASE = "/usr/share/nginx/html"
SITE = "https://briefer.news"

# Most recent N briefs to carry in each feed.
MAX_ITEMS = 30

# Briefs publish in the US morning; use a fixed per-day publish time
# (14:00 UTC ≈ 07:00 PDT, when the US synth runs) for pubDate.
PUBLISH_HOUR_UTC = 14

HEADLINE_RE = re.compile(r'<h2 class="headline">\s*(.+?)\s*</h2>', re.DOTALL)
DEK_RE = re.compile(r'<p class="dek">(.+?)</p>', re.DOTALL)
# The Events list only — `<ul class="items">` exactly, NOT the allied
# section's `<ul class="items allied-items">`.
ITEMS_RE = re.compile(r'<ul class="items">(.+?)</ul>', re.DOTALL)
LI_RE = re.compile(r'<li>(.+?)</li>', re.DOTALL)
LEAD_RE = re.compile(r'<b>(.+?)</b>', re.DOTALL)
SUP_RE = re.compile(r'<sup>.*?</sup>', re.DOTALL)
WHEN_RE = re.compile(r'<span class="when">.*?</span>', re.DOTALL)
TAG_RE = re.compile(r'<[^>]+>')


# ── Volume reads ────────────────────────────────────────────────────────────

def _list_archive_files(rel_path: str) -> list[str]:
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


def _read_archive_file(rel_path: str, filename: str) -> str:
    try:
        return subprocess.check_output(
            ["docker", "exec", NGINX_CONTAINER, "cat",
             f"{ARCHIVE_BASE}/{rel_path}/{filename}"],
            text=True, timeout=15,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""


# ── Parsing ─────────────────────────────────────────────────────────────────

def _clean(raw: str) -> str:
    """Strip tags + entities, collapse whitespace, to plain Unicode text."""
    text = TAG_RE.sub("", raw)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_brief(html: str) -> dict:
    """Pull headline, dek, and Events bullets from an archived brief."""
    h = HEADLINE_RE.search(html)
    d = DEK_RE.search(html)
    bullets: list[dict] = []
    items = ITEMS_RE.search(html)
    if items:
        for li_m in LI_RE.finditer(items.group(1)):
            li = li_m.group(1)
            lead_m = LEAD_RE.search(li)
            lead = _clean(lead_m.group(1)) if lead_m else ""
            # desc = the li with the bold lead, the citation sup, and the
            # date·agency span removed.
            body = li
            if lead_m:
                body = body.replace(lead_m.group(0), "", 1)
            body = SUP_RE.sub("", body)
            body = WHEN_RE.sub("", body)
            desc = _clean(body)
            if lead or desc:
                bullets.append({"lead": lead, "desc": desc})
    return {
        "headline": _clean(h.group(1)) if h else "(untitled brief)",
        "dek": _clean(d.group(1)) if d else "",
        "bullets": bullets,
    }


def collect_edition(rel_paths: list[tuple[str, str]]) -> list[dict]:
    """rel_paths: [(volume_dir, url_prefix)]. Returns per-day briefs, newest
    first, capped at MAX_ITEMS."""
    briefs: list[dict] = []
    seen: set[str] = set()
    for vol_dir, url_prefix in rel_paths:
        for fname in _list_archive_files(vol_dir):
            day = fname.removesuffix(".html")
            if day in seen:
                continue
            try:
                day_dt = datetime.strptime(day, "%Y-%m-%d")
            except ValueError:
                continue
            html = _read_archive_file(vol_dir, fname)
            if not html:
                continue
            seen.add(day)
            parsed = extract_brief(html)
            parsed["date"] = day
            parsed["date_obj"] = day_dt
            parsed["url"] = f"{SITE}{url_prefix}/{fname}"
            briefs.append(parsed)
    briefs.sort(key=lambda b: b["date_obj"], reverse=True)
    return briefs[:MAX_ITEMS]


# ── RSS rendering ───────────────────────────────────────────────────────────

def _xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def _item_description(brief: dict) -> str:
    """HTML body for the <description>, wrapped in CDATA by the caller."""
    parts: list[str] = []
    if brief["dek"]:
        parts.append(f"<p>{brief['dek']}</p>")
    if brief["bullets"]:
        lis = []
        for b in brief["bullets"]:
            lead = f"<strong>{b['lead']}</strong> " if b["lead"] else ""
            lis.append(f"<li>{lead}{b['desc']}</li>")
        parts.append("<ul>\n" + "\n".join(lis) + "\n</ul>")
    parts.append(f'<p><a href="{brief["url"]}">Read the full brief &rarr;</a></p>')
    body = "\n".join(parts)
    # CDATA cannot contain the literal sequence "]]>".
    return body.replace("]]>", "]] >")


def build_rss(title: str, home: str, feed_url: str,
              description: str, briefs: list[dict]) -> str:
    now = format_datetime(datetime.now(timezone.utc))
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        f"    <title>{_xml_escape(title)}</title>",
        f"    <link>{home}</link>",
        f'    <atom:link href="{feed_url}" rel="self" type="application/rss+xml"/>',
        f"    <description>{_xml_escape(description)}</description>",
        "    <language>en-us</language>",
        f"    <lastBuildDate>{now}</lastBuildDate>",
        "    <ttl>720</ttl>",
    ]
    for b in briefs:
        pub = b["date_obj"].replace(hour=PUBLISH_HOUR_UTC, tzinfo=timezone.utc)
        lines += [
            "    <item>",
            f"      <title>{_xml_escape(b['headline'])}</title>",
            f"      <link>{b['url']}</link>",
            f'      <guid isPermaLink="true">{b["url"]}</guid>',
            f"      <pubDate>{format_datetime(pub)}</pubDate>",
            f"      <description><![CDATA[{_item_description(b)}]]></description>",
            "    </item>",
        ]
    lines += ["  </channel>", "</rss>", ""]
    return "\n".join(lines)


# ── Main ────────────────────────────────────────────────────────────────────

EDITIONS = {
    "usa": {
        "title": "Briefer News — U.S. Edition",
        "home": f"{SITE}/usa/",
        "feed_url": f"{SITE}/usa/feed.xml",
        "description": "A daily brief from U.S. government sources.",
        # US pulls from the multi-edition archive and the legacy
        # pre-2026-05-12 single-edition archive.
        "rel_paths": [("usa/archive", "/usa/archive"), ("archive", "/archive")],
    },
    "china": {
        "title": "Briefer News — China Edition",
        "home": f"{SITE}/china/",
        "feed_url": f"{SITE}/china/feed.xml",
        "description": "A daily brief from Chinese government sources.",
        "rel_paths": [("china/archive", "/china/archive")],
    },
}


def main() -> int:
    RUN_DIR.mkdir(exist_ok=True)
    for key, meta in EDITIONS.items():
        briefs = collect_edition(meta["rel_paths"])
        xml = build_rss(meta["title"], meta["home"], meta["feed_url"],
                        meta["description"], briefs)
        out_path = RUN_DIR / f"feed_{key}.xml"
        out_path.write_text(xml, encoding="utf-8")
        print(f"feed {key}: {len(briefs)} item(s) · {len(xml)} bytes · {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
