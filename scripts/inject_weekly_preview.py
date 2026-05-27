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
    /* The 'This week' section renders as <ul class="items week-items">, so
       it inherits the full event styling (counter numbering, .event-details
       progressive disclosure, sup citations, .when tags). The week-items
       modifier exists in case we ever want to differentiate visually. */
    .weekly-preview { margin: 22px 0 22px; }
    ul.items.week-items { margin-top: 6px; }
    .weekly-preview-link {
      display: inline-block; margin-top: 4px;
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
    """Pull headline + lead paragraph + top events (with body + cite) from a weekly.

    Each event extracted as a dict with `lead`, `body`, `cite_html` so we can
    render the daily's "This week" section with the same progressive-disclosure
    format as the daily events (lede collapsed, body + cite on click)."""
    result = {"headline": "", "lead": "", "events": []}

    m = re.search(r'<h2 class="headline">\s*(.+?)\s*</h2>', html, re.DOTALL)
    if m:
        result["headline"] = re.sub(r"\s+", " ", m.group(1)).strip()

    m = re.search(r'<p class="week-read">\s*(.+?)\s*</p>', html, re.DOTALL)
    if m:
        result["lead"] = re.sub(r"\s+", " ", m.group(1)).strip()

    # Extract top 5 events with full body + cite from <ul class="week-bullets">
    bullets_m = re.search(r'<ul class="week-bullets">(.+?)</ul>', html, re.DOTALL)
    if bullets_m:
        for li_m in re.finditer(r'<li>([\s\S]+?)</li>', bullets_m.group(1)):
            li_content = li_m.group(1).strip()
            # Lede = <b>...</b>
            lead_m = re.search(r'<b>([^<]+)</b>', li_content)
            if not lead_m:
                continue
            lead = re.sub(r"\s+", " ", lead_m.group(1)).strip().rstrip(".")
            # Everything after </b> through end of li is the body + cite + when
            after_b = li_content[lead_m.end():]
            # The weekly uses <span class="week-tag"> for the date; the daily
            # uses <span class="when">. Normalize so the daily's styling works.
            after_b = after_b.replace('class="week-tag"', 'class="when"')
            result["events"].append({
                "lead": lead,
                "body_html": after_b.strip(),
            })
            if len(result["events"]) >= 5:
                break

    return result


def render_preview(weekly: dict, edition_path: str) -> str:
    """Render "This week" using the same progressive-disclosure format as
    the daily Events section — each item is a collapsed lede that expands
    on click to show body + citation. Reuses `<ul class="items">` styling
    so the visual treatment matches Events perfectly (counter numbering,
    sepia accent, when-tag, sup citation, etc.)."""
    events = weekly.get("events", [])
    if events:
        items_html = []
        for ev in events:
            lead_safe = html_lib.escape(html_lib.unescape(ev["lead"]))
            body_html = ev["body_html"]  # already HTML; keep entities as-is
            items_html.append(
                f'      <li><details class="event-details">'
                f'<summary class="event-summary"><b>{lead_safe}.</b></summary> '
                f'{body_html}'
                f'</details></li>'
            )
        body = (
            '    <ul class="items week-items">\n'
            + "\n".join(items_html)
            + "\n    </ul>\n"
        )
    else:
        body = ""

    return (
        '\n  <h3 class="section-label">This week</h3>\n'
        '  <div class="weekly-preview">\n'
        + body
        + f'    <a class="weekly-preview-link" href="/{edition_path}/weekly/">Read the full digest &rarr;</a>\n'
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

    # Insertion anchor (in priority order):
    #   1. Before <h3>Allied Governments</h3>  — events → week → allied → voices
    #   2. Before <h3>Outside the Gate</h3>    — China brief equivalent of allied
    #   3. Before <h3>Voices</h3>              — fallback if no allied section today
    #   4. Before <details class="sources-details"> — fallback for older briefs
    #   5. Before </main>                      — last-resort fallback
    # NOTE: Voices anchors on the H3 LABEL, not the <div class="voices">, because
    # the label sits OUTSIDE the div as a sibling — anchoring on the div would
    # place "This week" between the label and its content.
    anchors = [
        r'(\s*<h3 class="section-label">Allied Governments</h3>)',
        r'(\s*<h3 class="section-label">Outside the Gate</h3>)',
        r'(\s*<h3 class="section-label">Voices</h3>)',
        r'(\s*<details class="sources-details")',
        r'(\s*</main>)',
    ]
    new_html = daily_html
    inserted = False
    for anchor in anchors:
        new_html, n = re.subn(
            anchor,
            lambda m: "\n" + preview_html.rstrip("\n") + m.group(1),
            daily_html, count=1, flags=re.DOTALL,
        )
        if n > 0:
            inserted = True
            break
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
