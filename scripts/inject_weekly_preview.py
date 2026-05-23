#!/usr/bin/env python3
"""
inject_weekly_preview.py — Build the "This week" section for each daily
brief from the just-written weekly digest, then patch it into the live
daily HTML.

The "This week" section follows the same visual identity as Voices /
Events: a section-label header followed by a summary block (weekly's
headline + lead paragraph) and an optional drop-down listing the top
events of the week, plus a link to the full digest.

Output ends up at /usa/index.html and /china/index.html on the public
site. The script is idempotent — strips any previous .weekly-preview
block before injecting.

Cadence: runs from daily_digests.sh after weekly.sh, so each morning's
daily reflects the just-synthesized weekly.
"""

from __future__ import annotations

import html as html_lib
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUN_DIR = REPO / ".run"
NGINX_CONTAINER = "briefer_nginx"

WEEKLY_PREVIEW_CSS = """
    /* BEGIN-WEEKLY-PREVIEW-CSS (managed by scripts/inject_weekly_preview.py) */
    .weekly-preview-headline {
      font-family: 'EB Garamond', Garamond, Georgia, serif;
      font-size: 22px; line-height: 1.3; font-weight: 500;
      color: var(--ink); margin: 0 0 12px;
    }
    .weekly-preview-lead {
      font-size: 17px; line-height: 1.55;
      color: var(--ink); margin: 0 0 16px;
    }
    details.weekly-preview-events { margin: 0 0 16px; }
    details.weekly-preview-events > summary.weekly-preview-events-summary {
      cursor: pointer; list-style: none; display: inline-block;
      padding: 6px 12px; background: transparent;
      border: 1px solid var(--ink-soft); border-radius: 2px;
      font-family: 'IBM Plex Mono', ui-monospace, monospace;
      font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase;
      font-weight: 500; color: var(--ink-soft); user-select: none;
      transition: color 0.15s, border-color 0.15s, background-color 0.15s;
    }
    details.weekly-preview-events > summary.weekly-preview-events-summary::-webkit-details-marker { display: none; }
    details.weekly-preview-events > summary.weekly-preview-events-summary::before { content: "+ "; font-weight: 600; }
    details.weekly-preview-events[open] > summary.weekly-preview-events-summary {
      margin-bottom: 10px; color: var(--paper);
      background: var(--sepia); border-color: var(--sepia);
    }
    details.weekly-preview-events[open] > summary.weekly-preview-events-summary::before { content: "\\2212 "; }
    details.weekly-preview-events > summary.weekly-preview-events-summary:hover {
      color: var(--ink); border-color: var(--ink-light);
    }
    details.weekly-preview-events[open] > summary.weekly-preview-events-summary:hover {
      background: var(--sepia); color: var(--paper); border-color: var(--sepia);
    }
    .weekly-preview-events-list { list-style: none; padding: 0; margin: 8px 0 0; }
    .weekly-preview-events-list li {
      padding: 6px 0 6px 18px; position: relative; font-size: 15px;
      color: var(--ink); border-top: 1px solid var(--ink-soft);
    }
    .weekly-preview-events-list li:first-child { border-top: none; }
    .weekly-preview-events-list li::before {
      content: "·"; position: absolute; left: 4px;
      color: var(--sepia); font-weight: 600;
    }
    .weekly-preview-link {
      font-family: 'IBM Plex Mono', ui-monospace, monospace;
      font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase;
      color: var(--sepia); text-decoration: none;
      border-bottom: 1px dotted var(--sepia); padding-bottom: 2px;
    }
    .weekly-preview-link:hover { border-bottom-style: solid; }
    /* END-WEEKLY-PREVIEW-CSS */
"""


def _docker_read(path: str) -> str:
    try:
        return subprocess.check_output(
            ["docker", "exec", NGINX_CONTAINER, "cat", path],
            text=True, timeout=15,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""


def _docker_write(local_path: Path, dst_path: str) -> bool:
    rel = dst_path.replace("/usr/share/nginx/html/", "", 1)
    src_dir = local_path.parent
    src_name = local_path.name
    try:
        subprocess.check_call(
            ["docker", "run", "--rm",
             "-v", f"{src_dir}:/src:ro",
             "-v", "briefernewsapp_site_output:/dst",
             "alpine", "sh", "-c",
             f"cp /src/{src_name} /dst/{rel}"],
            timeout=30,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def _s3_get(s3_path: str) -> str:
    return subprocess.check_output(
        ["/Users/maxgoshay/.local/bin/aws", "s3", "cp", s3_path, "-"],
        text=True,
    )


def _s3_put(local_path: Path, s3_path: str) -> bool:
    try:
        subprocess.check_call(
            ["/Users/maxgoshay/.local/bin/aws", "s3", "cp", str(local_path), s3_path,
             "--content-type", "text/html; charset=utf-8",
             "--cache-control", "no-store, no-cache"],
            timeout=60,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def extract_weekly(html: str) -> dict:
    """Pull headline + lead paragraph + top bullet-lead phrases from a weekly."""
    result = {"headline": "", "lead": "", "events": []}

    m = re.search(r'<h2 class="headline">\s*(.+?)\s*</h2>', html, re.DOTALL)
    if m:
        result["headline"] = re.sub(r"\s+", " ", m.group(1)).strip()

    m = re.search(r'<p class="week-read">\s*(.+?)\s*</p>', html, re.DOTALL)
    if m:
        result["lead"] = re.sub(r"\s+", " ", m.group(1)).strip()

    # Extract top 5 event lead phrases from <ul class="week-bullets">
    bullets_m = re.search(r'<ul class="week-bullets">(.+?)</ul>', html, re.DOTALL)
    if bullets_m:
        for li_m in re.finditer(r'<li>\s*<b>([^<]+)</b>', bullets_m.group(1)):
            lead_phrase = re.sub(r"\s+", " ", li_m.group(1)).strip().rstrip(".")
            if lead_phrase:
                result["events"].append(lead_phrase)
            if len(result["events"]) >= 5:
                break

    return result


def render_preview(weekly: dict, edition_path: str) -> str:
    headline = html_lib.escape(weekly["headline"]) if weekly["headline"] else "Read this week's digest"
    lead = weekly["lead"]  # already entity-encoded in source HTML; leave as-is

    events_html = ""
    if weekly["events"]:
        items = "\n".join(
            f'        <li>{html_lib.escape(e)}</li>' for e in weekly["events"]
        )
        events_html = (
            '\n    <details class="weekly-preview-events">\n'
            '      <summary class="weekly-preview-events-summary">This week\'s events</summary>\n'
            '      <ul class="weekly-preview-events-list">\n'
            f"{items}\n"
            "      </ul>\n"
            "    </details>"
        )

    return (
        '\n  <h3 class="section-label">This week</h3>\n'
        '  <div class="weekly-preview">\n'
        f'    <p class="weekly-preview-headline">{headline}</p>\n'
        + (f'    <p class="weekly-preview-lead">{lead}</p>\n' if lead else "")
        + events_html + "\n"
        f'    <a class="weekly-preview-link" href="/{edition_path}/weekly/">Read the full digest &rarr;</a>\n'
        '  </div>\n'
    )


def inject(daily_html: str, weekly: dict, edition_path: str) -> str:
    # Remove any previously-injected preview (legacy <p class="weekly-preview">
    # OR new <div class="weekly-preview"> block)
    daily_html = re.sub(
        r'\n\s*<p class="weekly-preview">.*?</p>\n',
        "\n",
        daily_html, flags=re.DOTALL,
    )
    daily_html = re.sub(
        r'\n\s*<h3 class="section-label">This week</h3>\s*<div class="weekly-preview">.*?</div>\n',
        "\n",
        daily_html, flags=re.DOTALL,
    )

    # Strip the previously-managed block AND any legacy unmanaged blocks
    # (older prototype eras carried italic + smaller weekly-preview styling
    # under a different comment marker). Then always inject fresh — the
    # managed CSS is the source of truth.
    daily_html = re.sub(
        r"\s*/\*\s*BEGIN-WEEKLY-PREVIEW-CSS.*?END-WEEKLY-PREVIEW-CSS\s*\*/\s*",
        "\n",
        daily_html, flags=re.DOTALL,
    )
    daily_html = re.sub(
        r"\s*/\*\s*[Tt]his[- ]?week[^*]*\*/\s*"
        r"(?:\.weekly-preview[^{]*\{[^}]*\}\s*"
        r"|details\.weekly-preview[^{]*\{[^}]*\}\s*"
        r"|details\.weekly-preview[^{]*::[^{]*\{[^}]*\}\s*)+",
        "\n",
        daily_html, flags=re.DOTALL,
    )
    daily_html = daily_html.replace("</style>", WEEKLY_PREVIEW_CSS + "\n  </style>", 1)

    preview_html = render_preview(weekly, edition_path)

    # Insert after the thread-strip's closing </p>
    new_html, n = re.subn(
        r'(<p class="thread-strip">.*?</p>)',
        lambda m: m.group(1) + preview_html.rstrip("\n"),
        daily_html, count=1, flags=re.DOTALL,
    )
    if n == 0:
        # Fallback: insert after the dek
        new_html, n = re.subn(
            r'(<p class="dek">.*?</p>)',
            lambda m: m.group(1) + preview_html.rstrip("\n"),
            daily_html, count=1, flags=re.DOTALL,
        )
    return new_html


def process_edition(edition: str) -> bool:
    edition_path = "usa" if edition == "us" else "china"

    weekly_path = f"/usr/share/nginx/html/{edition_path}/weekly/index.html"
    daily_path = f"/usr/share/nginx/html/{edition_path}/index.html"

    weekly_html = _docker_read(weekly_path)
    if not weekly_html:
        print(f"  [{edition}] no weekly digest at {weekly_path} — skipping")
        return False

    weekly = extract_weekly(weekly_html)
    if not weekly["headline"]:
        print(f"  [{edition}] could not parse weekly headline — skipping")
        return False
    print(f"  [{edition}] headline: {weekly['headline'][:60]}...")
    print(f"  [{edition}] lead:     {len(weekly['lead'])} chars")
    print(f"  [{edition}] events:   {len(weekly['events'])}")

    daily_html = _docker_read(daily_path)
    if not daily_html:
        print(f"  [{edition}] daily not in nginx volume; falling back to S3")
        daily_html = _s3_get(f"s3://briefer-news-site/{edition_path}/index.html")

    patched = inject(daily_html, weekly, edition_path)

    out_path = RUN_DIR / f"daily_with_weekly_{edition}.html"
    out_path.write_text(patched, encoding="utf-8")

    nginx_ok = _docker_write(out_path, daily_path)
    s3_ok = _s3_put(out_path, f"s3://briefer-news-site/{edition_path}/index.html")
    print(f"  [{edition}] nginx: {'ok' if nginx_ok else 'FAILED'}, s3: {'ok' if s3_ok else 'FAILED'}")
    return nginx_ok and s3_ok


def main() -> int:
    RUN_DIR.mkdir(exist_ok=True)
    any_changed = False
    for edition in ("us", "china"):
        if process_edition(edition):
            any_changed = True

    if any_changed:
        subprocess.run(
            ["/Users/maxgoshay/.local/bin/aws", "cloudfront", "create-invalidation",
             "--distribution-id", "EMV1VIFYTSI3U",
             "--paths", "/usa/index.html", "/usa/", "/china/index.html", "/china/",
             "--query", "Invalidation.Id", "--output", "text"],
            check=False,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
