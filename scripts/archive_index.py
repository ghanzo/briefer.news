#!/usr/bin/env python3
"""
archive_index.py — Build a chronological index page of past daily briefs
for each edition.

Reads from the nginx docker volume (same docker-exec pattern as
weekly_aggregate.py). For each archived HTML file, extracts the
headline and dek (if present), then renders a single index page
per edition.

US edition pulls from BOTH /archive/ (legacy, pre-2026-05-12 single-edition)
AND /usa/archive/ (multi-edition era). China edition pulls only from
/china/archive/.

Output:
  .run/archive_index_usa.html
  .run/archive_index_china.html

Usage:
  python3 scripts/archive_index.py [YYYY-MM-DD]
"""

from __future__ import annotations

import html as html_lib
import re
import subprocess
import sys
from datetime import datetime, date
from pathlib import Path
from string import Template

REPO = Path(__file__).resolve().parent.parent
RUN_DIR = REPO / ".run"
NGINX_CONTAINER = "briefer_nginx"
ARCHIVE_BASE = "/usr/share/nginx/html"

HEADLINE_RE = re.compile(r'<h2 class="headline">\s*(.+?)\s*</h2>', re.DOTALL)
# Dek: new bulleted form (post 2026-05-27) preferred; legacy paragraph fallback.
DEK_BULLETS_RE = re.compile(r'<ul class="dek-bullets">(.+?)</ul>', re.DOTALL)
DEK_BULLET_LI_RE = re.compile(r'<li[^>]*>(.+?)</li>', re.DOTALL)
DEK_RE = re.compile(r'<p class="dek">(.+?)</p>', re.DOTALL)


def _extract_dek(html: str) -> str | None:
    m = DEK_BULLETS_RE.search(html)
    if m:
        bullets = [_clean(b) for b in DEK_BULLET_LI_RE.findall(m.group(1))]
        joined = " · ".join(b for b in bullets if b)
        return joined or None
    m = DEK_RE.search(html)
    return _clean(m.group(1)) if m else None


def _list_archive_files(rel_path: str) -> list[str]:
    """rel_path examples: 'usa/archive', 'china/archive', 'archive' (legacy)"""
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


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    text = html_lib.unescape(text).strip()
    return re.sub(r"\s+", " ", text)


def collect_briefs(rel_path: str, archive_url_prefix: str) -> list[dict]:
    """Return [{date, headline, dek, url}] sorted desc by date."""
    out: list[dict] = []
    for fname in _list_archive_files(rel_path):
        try:
            d = datetime.strptime(fname.removesuffix(".html"), "%Y-%m-%d").date()
        except ValueError:
            continue
        html = _read_archive_file(rel_path, fname)
        if not html:
            continue
        h_match = HEADLINE_RE.search(html)
        out.append({
            "date": d.isoformat(),
            "date_obj": d,
            "headline": _clean(h_match.group(1)) if h_match else "(no headline parsed)",
            "dek": _extract_dek(html),
            "url": f"{archive_url_prefix}{fname}",
        })
    out.sort(key=lambda b: b["date_obj"], reverse=True)
    return out


PAGE_TPL = Template(r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Archive · Briefer News$EDITION_TITLE_SUFFIX</title>
  <meta name="description" content="Chronological archive of past Briefer News$EDITION_TITLE_SUFFIX daily briefs.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root, body.theme-kraft {
      --paper: #F5EFE2;
      --ink: #1A1614;
      --ink-soft: #3D332C;
      --ink-light: #6B5D52;
      --sepia: #7A4F2E;
      --black: #14110F;
      --cream: #F2EBD9;
      --tagline: #C9BFA7;
    }
    * { box-sizing: border-box; }
    html, body {
      margin: 0; padding: 0;
      background: var(--paper); color: var(--ink);
      font-family: 'EB Garamond', Garamond, Georgia, serif;
      font-size: 21px; line-height: 1.55;
      -webkit-font-smoothing: antialiased;
      overflow-x: hidden;
    }
    header.masthead {
      background: var(--black); color: var(--cream);
      padding: 22px 24px 16px; text-align: center;
      border-bottom: 1px solid var(--ink);
    }
    header.masthead h1 {
      font-family: 'EB Garamond', Garamond, Georgia, serif;
      font-weight: 600;
      font-size: clamp(28px, 4.4vw, 44px);
      letter-spacing: 0.01em;
      margin: 0 0 6px; line-height: 1;
    }
    header.masthead p.tagline {
      font-style: italic;
      font-weight: 400;
      font-size: clamp(12px, 1.3vw, 14px);
      color: var(--tagline);
      letter-spacing: 0.02em;
      margin: 0;
    }
    main {
      max-width: 760px;
      margin: 0 auto;
      padding: 18px 24px 60px;
    }
    h2.page-title {
      font-family: 'EB Garamond', Garamond, Georgia, serif;
      font-size: clamp(26px, 3vw, 32px);
      font-weight: 500;
      line-height: 1.2;
      margin: 0 0 8px;
    }
    p.page-intro {
      color: var(--ink-light);
      max-width: 60ch;
      margin: 0 0 32px;
      font-size: 17px;
      line-height: 1.5;
      padding-top: 12px;
      position: relative;
    }
    p.page-intro::before {
      content: '';
      display: block;
      width: 40px; height: 2px;
      background: var(--sepia);
      margin: 0 0 12px;
    }
    ul.archive-list {
      list-style: none;
      padding: 0; margin: 0;
    }
    ul.archive-list li {
      padding: 16px 0;
      border-top: 1px solid var(--ink-soft);
    }
    ul.archive-list li:last-child {
      border-bottom: 1px solid var(--ink-soft);
    }
    .archive-date {
      font-family: 'IBM Plex Mono', ui-monospace, monospace;
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--sepia);
      margin: 0 0 8px;
    }
    .archive-headline {
      font-family: 'EB Garamond', Garamond, Georgia, serif;
      font-size: 20px;
      font-weight: 500;
      line-height: 1.3;
      margin: 0 0 6px;
    }
    .archive-headline a {
      color: var(--ink);
      text-decoration: none;
      border-bottom: 1px dotted var(--ink-light);
    }
    .archive-headline a:hover { border-bottom-color: var(--sepia); color: var(--sepia); }
    .archive-dek {
      font-size: 16px;
      line-height: 1.45;
      color: var(--ink-light);
      margin: 0;
      max-width: 64ch;
    }
    .archive-empty {
      padding: 24px;
      border: 1px dashed var(--ink-light);
      border-radius: 3px;
      color: var(--ink-light);
      font-style: italic;
    }
    footer.site-foot {
      margin-top: 48px;
      padding-top: 18px;
      border-top: 1px solid var(--ink-soft);
      display: flex;
      flex-wrap: wrap;
      gap: 8px 22px;
      font-family: 'IBM Plex Mono', ui-monospace, monospace;
      font-size: 11px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }
    footer.site-foot a {
      color: var(--sepia);
      text-decoration: none;
      border-bottom: 1px dotted var(--sepia);
    }
    footer.site-foot a:hover { border-bottom-style: solid; }
  </style>
</head>
<body class="theme-kraft">
  <header class="masthead">
    <h1>Briefer News</h1>
    <p class="tagline">Archive$EDITION_TAGLINE_SUFFIX</p>
  </header>

  <main>
    <h2 class="page-title">Daily briefs &middot; archive</h2>
    <p class="page-intro">$INTRO_TEXT</p>

    $LIST_HTML

    <footer class="site-foot">
      <a href="$EDITION_HOME">← $EDITION_LABEL daily brief</a>
      <a href="$WEEKLY_HREF">↗ Weekly digest</a>
      <a href="/about/">About</a>
      <a href="/sources/">Sources</a>
    </footer>
  </main>
</body>
</html>
""")


MONTHS = ["", "January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def render_list(briefs: list[dict]) -> str:
    if not briefs:
        return '<div class="archive-empty">No archived briefs found yet.</div>'
    items = ['<ul class="archive-list">']
    for b in briefs:
        d = b["date_obj"]
        date_label = f"{d.strftime('%A').upper()} &middot; {MONTHS[d.month][:3].upper()} {d.day}, {d.year}"
        headline = html_lib.escape(b["headline"])
        url = html_lib.escape(b["url"], quote=True)
        dek_html = ""
        if b["dek"]:
            dek_html = f'<p class="archive-dek">{html_lib.escape(b["dek"])}</p>'
        items.append(
            f'<li><p class="archive-date">{date_label}</p>'
            f'<p class="archive-headline"><a href="{url}">{headline}</a></p>'
            f'{dek_html}</li>'
        )
    items.append('</ul>')
    return "\n    ".join(items)


def render_page(edition: str, briefs: list[dict]) -> str:
    if edition == "us":
        edition_label = "U.S."
        edition_home = "/usa/"
        weekly_href = "/usa/weekly/"
        edition_title_suffix = " (U.S.)"
        edition_tagline_suffix = " &middot; U.S."
        intro_text = (
            "Past daily briefs from U.S.-government sources, most recent first. "
            "Each entry links to the full brief as it was published that morning."
        )
    else:
        edition_label = "China"
        edition_home = "/china/"
        weekly_href = "/china/weekly/"
        edition_title_suffix = " (China)"
        edition_tagline_suffix = " &middot; China"
        intro_text = (
            "Past daily briefs from Chinese-government sources, most recent first. "
            "Each entry links to the full brief as it was published that morning."
        )

    list_html = render_list(briefs)

    return PAGE_TPL.substitute(
        EDITION_TITLE_SUFFIX=edition_title_suffix,
        EDITION_TAGLINE_SUFFIX=edition_tagline_suffix,
        INTRO_TEXT=intro_text,
        LIST_HTML=list_html,
        EDITION_HOME=edition_home,
        EDITION_LABEL=edition_label,
        WEEKLY_HREF=weekly_href,
    )


def main() -> int:
    # us edition pulls from both legacy /archive/ and /usa/archive/
    us_legacy = collect_briefs("archive", "/archive/")
    us_current = collect_briefs("usa/archive", "/usa/archive/")
    us = us_current + us_legacy
    us.sort(key=lambda b: b["date_obj"], reverse=True)

    cn = collect_briefs("china/archive", "/china/archive/")

    RUN_DIR.mkdir(exist_ok=True)
    (RUN_DIR / "archive_index_usa.html").write_text(render_page("us", us), encoding="utf-8")
    (RUN_DIR / "archive_index_china.html").write_text(render_page("china", cn), encoding="utf-8")
    print(f"us:    {len(us)} brief(s)")
    print(f"china: {len(cn)} brief(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
