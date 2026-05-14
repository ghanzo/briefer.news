#!/usr/bin/env python3
"""
og_weekly_render.py — Render the OG weekly digest page for each edition
from the aggregator JSON.

Input:  .run/og_weekly.json  (or path given as 1st arg)
Output: .run/og_week_usa.html and .run/og_week_china.html

Mechanical templating — no Claude synthesis at this stage. The dailies
already do the editorial work; the weekly is collation.
"""

from __future__ import annotations

import html as html_lib
import json
import sys
from datetime import date, datetime
from pathlib import Path
from string import Template

REPO = Path(__file__).resolve().parent.parent
RUN_DIR = REPO / ".run"

PAGE_TPL = Template(r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Briefer News — Outside the Gate · Week of $WEEK_LABEL · $EDITION_LABEL</title>
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
      font-size: 20px; line-height: 1.5;
      -webkit-font-smoothing: antialiased;
      overflow-x: hidden;
    }
    header.masthead {
      background: var(--black); color: var(--cream);
      padding: 20px 24px 16px; text-align: center;
      border-bottom: 1px solid var(--ink);
    }
    header.masthead h1 {
      font-family: 'EB Garamond', Garamond, Georgia, serif;
      font-weight: 600;
      font-size: clamp(28px, 4.2vw, 42px);
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
    .stamp {
      max-width: 740px;
      margin: 0 auto;
      padding: 10px 24px 0;
      text-align: right;
      font-family: 'IBM Plex Mono', ui-monospace, monospace;
      font-size: 11px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--sepia);
    }
    main.brief {
      max-width: 740px;
      margin: 0 auto;
      padding: 8px 24px 48px;
    }
    .page-title {
      font-family: 'EB Garamond', Garamond, Georgia, serif;
      font-size: clamp(24px, 2.8vw, 30px);
      font-weight: 500; line-height: 1.2;
      margin: 0 0 6px;
    }
    .page-intro {
      font-size: 17px;
      line-height: 1.5;
      color: var(--ink-light);
      margin: 0 0 28px;
      max-width: 60ch;
      padding-top: 12px;
      position: relative;
    }
    .page-intro::before {
      content: '';
      display: block;
      width: 40px;
      height: 2px;
      background: var(--sepia);
      margin: 0 0 12px;
    }

    h3.day-divider {
      font-family: 'IBM Plex Mono', ui-monospace, monospace;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--sepia);
      margin: 28px 0 14px;
      padding-bottom: 6px;
      border-bottom: 1px solid var(--ink-soft);
    }

    /* OG item list — mirrors the daily brief styling */
    ul.outside-gate {
      list-style: none;
      margin: 0; padding: 0;
      border-left: 2px solid var(--sepia);
      padding-left: 16px;
    }
    ul.outside-gate li {
      margin: 0 0 16px;
      font-size: 16px;
      line-height: 1.5;
      color: var(--ink);
    }
    ul.outside-gate li:last-child { margin-bottom: 0; }
    ul.outside-gate li b { color: var(--ink); }
    ul.outside-gate li .when {
      display: block;
      margin-top: 4px;
      font-family: 'IBM Plex Mono', ui-monospace, monospace;
      font-size: 10px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--ink-light);
    }
    ul.outside-gate li sup .cite {
      color: var(--sepia);
      text-decoration: none;
    }

    /* Empty-state */
    .og-empty {
      margin: 36px 0;
      padding: 18px 20px;
      border: 1px dashed var(--ink-light);
      border-radius: 3px;
      color: var(--ink-light);
      font-size: 16px;
      font-style: italic;
      line-height: 1.5;
    }

    /* Footer */
    footer.weekly-foot {
      margin-top: 44px;
      padding-top: 18px;
      border-top: 1px solid var(--ink-soft);
      display: flex;
      flex-wrap: wrap;
      gap: 18px;
      font-family: 'IBM Plex Mono', ui-monospace, monospace;
      font-size: 11px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }
    footer.weekly-foot a {
      color: var(--sepia);
      text-decoration: none;
      border-bottom: 1px dotted var(--sepia);
    }
    footer.weekly-foot a:hover { border-bottom-style: solid; }
  </style>
</head>
<body class="theme-kraft">
  <header class="masthead">
    <h1>Briefer News</h1>
    <p class="tagline">Outside the Gate · weekly · $EDITION_LABEL</p>
  </header>

  <div class="stamp">Week of $WEEK_LABEL</div>

  <main class="brief">
    <h2 class="page-title">Outside the Gate — this week in inbound signals</h2>
    <p class="page-intro">Non-$INTRO_NOUN-gov signals across the past seven days &mdash; what the world has been doing in response to, or parallel to, the daily brief. Pulled from the same archived briefs that ship Monday through Friday, grouped by date.</p>

    $ITEMS_HTML

    <footer class="weekly-foot">
      <a href="/$EDITION_PATH/">← $EDITION_LABEL daily brief</a>
      <a href="/">↗ Briefer News home</a>
    </footer>
  </main>
</body>
</html>
""")


MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]


def format_week_label(week_start_iso: str, week_end_iso: str) -> str:
    """Render '8 – 14 May, 2026' (same month) or '28 April – 4 May, 2026' (span)."""
    s = datetime.strptime(week_start_iso, "%Y-%m-%d").date()
    e = datetime.strptime(week_end_iso, "%Y-%m-%d").date()
    if s.month == e.month and s.year == e.year:
        return f"{s.day} – {e.day} {MONTH_NAMES[s.month]}, {s.year}"
    if s.year == e.year:
        return f"{s.day} {MONTH_NAMES[s.month]} – {e.day} {MONTH_NAMES[e.month]}, {s.year}"
    return f"{s.day} {MONTH_NAMES[s.month]} {s.year} – {e.day} {MONTH_NAMES[e.month]} {e.year}"


def format_day_divider(date_iso: str) -> str:
    d = datetime.strptime(date_iso, "%Y-%m-%d").date()
    weekday = d.strftime("%A").upper()
    return f"{MONTH_NAMES[d.month][:3].upper()} {d.day}, {d.year} &middot; {weekday}"


def group_items_by_date(items: list[dict]) -> list[tuple[str, list[dict]]]:
    """Group items by their brief-publish-date (already sorted desc)."""
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for it in items:
        d = it["date"]
        if d not in groups:
            groups[d] = []
            order.append(d)
        groups[d].append(it)
    return [(d, groups[d]) for d in order]


def render_items(items: list[dict]) -> str:
    if not items:
        return (
            '<div class="og-empty">No Outside the Gate items archived this week yet. '
            'The section came online 2026-05-15; weekly digests fill in as daily '
            'briefs publish.</div>'
        )
    parts: list[str] = []
    for date_iso, day_items in group_items_by_date(items):
        parts.append(f'<h3 class="day-divider">{format_day_divider(date_iso)}</h3>')
        parts.append('<ul class="outside-gate">')
        for it in day_items:
            lead = html_lib.escape(it["lead"])
            desc = it["desc"]  # already cleaned by aggregator (entities un-escaped, whitespace collapsed)
            # Re-escape any raw < > & that might have leaked through
            desc = html_lib.escape(desc, quote=False).replace("&amp;ldquo;", "&ldquo;").replace("&amp;rdquo;", "&rdquo;")
            url = html_lib.escape(it["url"], quote=True)
            src_title = html_lib.escape(it["src_title"], quote=True)
            letter = it["letter"]
            when_raw = html_lib.escape(it["when_raw"]).replace(" · ", " &middot; ")
            parts.append(
                f'<li><b>{lead}</b> {desc}'
                f'<sup><a class="cite" href="{url}" title="{src_title}" target="_blank" rel="noopener">{letter}</a></sup>'
                f'<span class="when">{when_raw}</span></li>'
            )
        parts.append('</ul>')
    return "\n    ".join(parts)


def render_page(doc: dict, edition: str) -> str:
    """Render one edition's page from the aggregator JSON."""
    if edition == "us":
        edition_label = "U.S."
        edition_path = "usa"
        intro_noun = "U.S."
    elif edition == "china":
        edition_label = "China"
        edition_path = "china"
        intro_noun = "PRC"
    else:
        raise ValueError(f"unknown edition: {edition}")

    week_label = format_week_label(doc["week_start"], doc["week_end"])
    items_html = render_items(doc.get(edition, []))

    return PAGE_TPL.substitute(
        WEEK_LABEL=week_label,
        EDITION_LABEL=edition_label,
        EDITION_PATH=edition_path,
        INTRO_NOUN=intro_noun,
        ITEMS_HTML=items_html,
    )


def main() -> int:
    if len(sys.argv) >= 2:
        in_path = Path(sys.argv[1])
    else:
        in_path = RUN_DIR / "og_weekly.json"
    if not in_path.exists():
        print(f"input JSON not found: {in_path}", file=sys.stderr)
        return 1

    doc = json.loads(in_path.read_text(encoding="utf-8"))

    RUN_DIR.mkdir(exist_ok=True)
    for edition in ("us", "china"):
        out_path = RUN_DIR / f"og_week_{'usa' if edition == 'us' else 'china'}.html"
        out_path.write_text(render_page(doc, edition), encoding="utf-8")
        n_items = len(doc.get(edition, []))
        print(f"  {edition}: {n_items} item(s) → {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
