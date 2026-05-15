#!/usr/bin/env python3
"""
Generate /china/archive/index.html and /usa/archive/index.html from the
S3 archive listings. Run after each synth so the archive pages stay current.

Usage:
  python3 scripts/build_archive_index.py <output-dir>

Writes:
  <output-dir>/china/archive/index.html
  <output-dir>/usa/archive/index.html

Lists archive entries newest-first. Source of truth is S3 (briefer-news-site).
"""

import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

S3_BUCKET = "briefer-news-site"
AWS = "/Users/maxgoshay/.local/bin/aws"

DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.html$")


def list_dates(edition: str) -> list[date]:
    """Return list of date objects for the YYYY-MM-DD.html files in s3://bucket/<edition>/archive/."""
    out = subprocess.check_output(
        [AWS, "s3", "ls", f"s3://{S3_BUCKET}/{edition}/archive/"],
        text=True,
    )
    dates: list[date] = []
    for line in out.splitlines():
        parts = line.split()
        if not parts:
            continue
        name = parts[-1]
        m = DATE_RE.match(name)
        if m:
            try:
                dates.append(date.fromisoformat(m.group(1)))
            except ValueError:
                pass
    dates.sort(reverse=True)
    return dates


CHINA_MASTHEAD = """
    <svg class="flag-mark" viewBox="0 0 48 28" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect x="0" y="0" width="48" height="28" fill="#C8252A"/>
      <circle cx="10" cy="9" r="3.5" fill="#FFDE00"/>
      <circle cx="18" cy="4" r="1.3" fill="#FFDE00"/>
      <circle cx="22" cy="7" r="1.3" fill="#FFDE00"/>
      <circle cx="22" cy="11" r="1.3" fill="#FFDE00"/>
      <circle cx="18" cy="14" r="1.3" fill="#FFDE00"/>
    </svg>"""

USA_MASTHEAD = """
    <svg class="flag-mark" viewBox="0 0 48 28" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect x="0" y="0" width="48" height="28" fill="#FFFFFF" stroke="#B22234" stroke-width="0.5"/>
      <rect x="0" y="0"  width="48" height="2.15" fill="#B22234"/>
      <rect x="0" y="4.3" width="48" height="2.15" fill="#B22234"/>
      <rect x="0" y="8.6" width="48" height="2.15" fill="#B22234"/>
      <rect x="0" y="12.9" width="48" height="2.15" fill="#B22234"/>
      <rect x="0" y="17.2" width="48" height="2.15" fill="#B22234"/>
      <rect x="0" y="21.5" width="48" height="2.15" fill="#B22234"/>
      <rect x="0" y="25.8" width="48" height="2.15" fill="#B22234"/>
      <rect x="0" y="0" width="19" height="15" fill="#3C3B6E"/>
    </svg>"""


def render(edition: str, dates: list[date]) -> str:
    edition_label = "China" if edition == "china" else "United States"
    edition_tagline = (
        "A daily brief from Chinese government sources"
        if edition == "china"
        else "A daily brief from U.S. government sources"
    )
    masthead = CHINA_MASTHEAD if edition == "china" else USA_MASTHEAD
    other_edition = "usa" if edition == "china" else "china"
    other_label = "United States" if other_edition == "usa" else "China"

    if dates:
        items = "\n".join(
            f'        <li><a href="{d.isoformat()}.html">{d.strftime("%A, %B %-d, %Y")}</a>'
            f'<span class="date-meta">{d.isoformat()}</span></li>'
            for d in dates
        )
        list_html = f'      <ul class="archive-list">\n{items}\n      </ul>'
    else:
        list_html = '      <p class="empty">No archive entries yet.</p>'

    build_stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    count = len(dates)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Briefer News &mdash; {edition_label} Archive</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --paper: #F5EFE2;
      --ink: #1A1614;
      --ink-soft: #3D332C;
      --ink-light: #6B5D52;
      --sepia: #7A4F2E;
      --rule: rgba(26,22,20,0.15);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: 'EB Garamond', 'Times New Roman', serif;
      font-size: 17px;
      line-height: 1.5;
    }}
    .container {{ max-width: 720px; margin: 0 auto; padding: 2rem 1.25rem 3rem; }}
    header.masthead {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding-bottom: 1rem;
      border-bottom: 2px solid var(--ink);
      flex-wrap: wrap;
    }}
    header.masthead svg.flag-mark {{ width: 48px; height: 28px; flex-shrink: 0; }}
    header.masthead .brand-block {{ display: flex; flex-direction: column; }}
    header.masthead h1 {{
      margin: 0;
      font-family: 'EB Garamond', serif;
      font-size: 1.55rem;
      font-weight: 700;
      letter-spacing: 0.01em;
    }}
    header.masthead .tagline {{
      margin: 0.05rem 0 0;
      color: var(--ink-light);
      font-size: 0.82rem;
    }}
    nav.editions {{
      margin-left: auto;
      font-size: 0.74rem;
      font-family: 'IBM Plex Mono', monospace;
      display: flex;
      gap: 0.4rem;
    }}
    nav.editions a {{
      color: var(--ink-light);
      text-decoration: none;
      padding: 0.25rem 0.5rem;
      border: 1px solid var(--rule);
      letter-spacing: 0.04em;
    }}
    nav.editions a.active {{
      color: var(--ink);
      border-color: var(--ink);
      background: rgba(26,22,20,0.05);
    }}
    h2.page-title {{
      font-family: 'IBM Plex Mono', monospace;
      font-size: 0.72rem;
      font-weight: 600;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--ink-light);
      margin: 2.25rem 0 1rem;
    }}
    .count {{
      font-family: 'IBM Plex Mono', monospace;
      font-size: 0.7rem;
      color: var(--ink-light);
      margin: -0.5rem 0 1.25rem;
    }}
    ul.archive-list {{
      list-style: none;
      padding: 0;
      margin: 0;
    }}
    ul.archive-list li {{
      padding: 0.85rem 0;
      border-bottom: 1px solid var(--rule);
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 1rem;
    }}
    ul.archive-list li:last-child {{ border-bottom: none; }}
    ul.archive-list a {{
      color: var(--ink);
      text-decoration: none;
      font-size: 1.08rem;
      font-weight: 500;
    }}
    ul.archive-list a:hover {{
      color: var(--sepia);
      text-decoration: underline;
    }}
    ul.archive-list .date-meta {{
      font-family: 'IBM Plex Mono', monospace;
      font-size: 0.68rem;
      color: var(--ink-light);
      letter-spacing: 0.04em;
      flex-shrink: 0;
    }}
    p.back-link {{
      margin-top: 2.25rem;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 0.74rem;
    }}
    p.back-link a {{
      color: var(--ink-light);
      text-decoration: none;
      border-bottom: 1px solid var(--rule);
      padding-bottom: 1px;
    }}
    p.back-link a:hover {{ color: var(--ink); border-color: var(--ink); }}
    p.empty {{ color: var(--ink-light); font-style: italic; }}
    footer.site {{
      margin-top: 3.5rem;
      padding-top: 1rem;
      border-top: 1px solid var(--rule);
      font-family: 'IBM Plex Mono', monospace;
      font-size: 0.66rem;
      color: var(--ink-light);
      letter-spacing: 0.04em;
      text-align: center;
    }}
    footer.site a {{ color: inherit; }}
    @media (max-width: 540px) {{
      header.masthead {{ gap: 0.5rem; }}
      header.masthead h1 {{ font-size: 1.3rem; }}
      nav.editions {{ width: 100%; margin: 0.5rem 0 0; }}
      ul.archive-list li {{ flex-direction: column; gap: 0.15rem; }}
      ul.archive-list .date-meta {{ font-size: 0.62rem; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header class="masthead">{masthead}
      <div class="brand-block">
        <h1>Briefer News</h1>
        <p class="tagline">{edition_tagline}</p>
      </div>
      <nav class="editions">
        <a href="../../{other_edition}/" >{other_label}</a>
        <a href="../" class="active">{edition_label}</a>
      </nav>
    </header>

    <h2 class="page-title">Archive</h2>
    <p class="count">{count} brief{'s' if count != 1 else ''} on record</p>

{list_html}

    <p class="back-link"><a href="../">&larr; Today&rsquo;s {edition_label} brief</a></p>

    <footer class="site">
      Briefer News &middot; <a href="https://briefer.news">briefer.news</a> &middot; index regenerated {build_stamp}
    </footer>
  </div>
</body>
</html>
"""


def main():
    if len(sys.argv) < 2:
        print("Usage: build_archive_index.py <output-dir>", file=sys.stderr)
        sys.exit(2)
    out_dir = Path(sys.argv[1])

    for edition in ("china", "usa"):
        dates = list_dates(edition)
        html = render(edition, dates)
        edition_dir = out_dir / edition / "archive"
        edition_dir.mkdir(parents=True, exist_ok=True)
        path = edition_dir / "index.html"
        path.write_text(html, encoding="utf-8")
        print(f"wrote {path} ({len(dates)} entries)")


if __name__ == "__main__":
    main()
