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

# Single source of truth for infra constants (AWS path, S3_BUCKET, DIST_ID).
# config.py parses scripts/lib/env.sh — same values the shell scripts source.
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import config

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
        [config.AWS, "s3", "cp", s3_path, "-"],
        text=True,
    )


def _s3_put(local_path: Path, s3_path: str) -> bool:
    try:
        subprocess.check_call(
            [config.AWS, "s3", "cp", str(local_path), s3_path,
             "--content-type", "text/html; charset=utf-8",
             "--cache-control", "no-store, no-cache"],
            timeout=60,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def _normalize_lede(s: str) -> str:
    """Normalize an event lede for dedupe comparison.

    Strips HTML entities, whitespace, trailing period, and lowercases. So
    'Quad critical minerals.' and 'Quad critical minerals' and
    'Quad&nbsp;critical minerals.' all compare equal."""
    s = html_lib.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.rstrip(".").lower()


def extract_daily_signatures(daily_html: str) -> dict:
    """Pull both event ledes AND cite URLs from today's daily — the visible
    <ul class="items"> AND the collapsed <ul class="items items-more">.

    URL-based dedupe is more reliable than lede-based because the daily and
    weekly synths sometimes phrase the same event's lede differently
    (e.g. "Armenia partnership" vs "U.S.–Armenia partnership"); the cite
    URL is the canonical identifier for "same event."

    Returns dict with keys `ledes` (set of normalized phrases) and
    `urls` (set of cite URLs). The inject's dedupe checks both — drop a
    weekly event if its lede OR cite URL matches anything in today's brief."""
    ledes = set()
    urls = set()
    for ul_class in ("items", "items items-more"):
        ul_re = rf'<ul class="{re.escape(ul_class)}"[^>]*>([\s\S]+?)</ul>'
        ul_m = re.search(ul_re, daily_html)
        if not ul_m:
            continue
        block = ul_m.group(1)
        for b_m in re.finditer(r'<b>([^<]+)</b>', block):
            ledes.add(_normalize_lede(b_m.group(1)))
        for href_m in re.finditer(r'class="cite"\s+href="([^"]+)"', block):
            urls.add(href_m.group(1).strip())
    return {"ledes": ledes, "urls": urls}


# kept as a thin alias for any callers expecting the older API
def extract_daily_ledes(daily_html: str) -> set:
    return extract_daily_signatures(daily_html)["ledes"]


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

    # Extract up to 9 events with full body + cite from <ul class="week-bullets">.
    # Inject() then dedupes against today's daily and renders the top 6 flat.
    # Pulling more than 6 here gives the dedupe headroom — if some of the week's
    # top stories are today's lead stories, we still have 6 distinct items left.
    bullets_m = re.search(r'<ul class="week-bullets">(.+?)</ul>', html, re.DOTALL)
    if bullets_m:
        for li_m in re.finditer(r'<li>([\s\S]+?)</li>', bullets_m.group(1)):
            li_content = li_m.group(1).strip()
            lead_m = re.search(r'<b>([^<]+)</b>', li_content)
            if not lead_m:
                continue
            lead = re.sub(r"\s+", " ", lead_m.group(1)).strip().rstrip(".")
            after_b = li_content[lead_m.end():]
            # Weekly uses <span class="week-tag">; daily uses <span class="when">.
            after_b = after_b.replace('class="week-tag"', 'class="when"')
            result["events"].append({
                "lead": lead,
                "body_html": after_b.strip(),
            })
            if len(result["events"]) >= 9:
                break

    return result


def render_preview(weekly: dict, edition_path: str) -> str:
    """Render "This week" using the same progressive-disclosure format as
    the daily Events section — each item is a collapsed lede that expands
    on click to show body + citation. Reuses `<ul class="items">` styling
    so the visual treatment matches Events perfectly (counter numbering,
    sepia accent, when-tag, sup citation, etc.)."""
    events = weekly.get("events", [])
    def render_li(ev):
        lead_safe = html_lib.escape(html_lib.unescape(ev["lead"]))
        return (
            f'      <li><details class="event-details">'
            f'<summary class="event-summary"><b>{lead_safe}.</b></summary> '
            f'{ev["body_html"]}'
            f'</details></li>'
        )

    if events:
        # All 6 visible in one list — no "Show N more" group expander (removed
        # 2026-05-31 to match the daily Events + Voices flat layout). Each item
        # keeps its per-event click-to-expand chevron. The "Read the full digest"
        # link below still offers the complete weekly page.
        visible = events[:6]
        body = (
            '    <ul class="items week-items">\n'
            + "\n".join(render_li(ev) for ev in visible)
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


def _strip_removed_sections(html: str) -> str:
    """Strip any China-brief sections that were removed 2026-05-27 per operator
    but that the synth might still try to produce (Strategic Backdrop,
    Five-Year Plan, summit transcript). Defensive — if the synth follows
    its prompt, these are no-ops."""
    patterns = [
        # Strategic Backdrop wrapper (filled OR empty)
        r'\n?\s*<details class="collapsible-details"[^>]*>\s*<summary[^>]*>Strategic Backdrop</summary>[\s\S]*?</details>\n?',
        # Five-Year Plan wrapper
        r'\n?\s*<details class="collapsible-details"[^>]*>\s*<summary[^>]*>Five-Year Plan</summary>[\s\S]*?</details>\n?',
        # Bare h3 + content (in case synth omits the collapsible wrapper)
        r'\n?\s*<h3 class="section-label">Strategic Backdrop</h3>\s*<div class="backdrop">[\s\S]+?</div>\n?',
        r'\n?\s*<h3 class="section-label">Five-Year Plan</h3>\s*<article class="fyp">[\s\S]+?</article>\n?',
        # Orphan div.backdrop with no preceding h3
        r'\n?\s*<div class="backdrop">[\s\S]+?</div>\n?',
        # Orphan article.fyp with no preceding h3
        r'\n?\s*<article class="fyp">[\s\S]+?</article>\n?',
        # Summit transcript section (display:none-hidden, but still in DOM)
        r'\n?\s*<section class="transcript"[^>]*>[\s\S]+?</section>\n?',
    ]
    for pat in patterns:
        html = re.sub(pat, '\n', html, count=1, flags=re.DOTALL)
    return html


def inject(daily_html: str, weekly: dict, edition_path: str) -> str:
    # Strip any deprecated sections the synth might still produce (Strategic
    # Backdrop, Five-Year Plan, transcript). All removed 2026-05-27.
    daily_html = _strip_removed_sections(daily_html)

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

    # Dedupe — drop weekly events that already appear in today's "Today's
    # events" or the collapsed more-events block. Checks both lede strings
    # AND cite URLs since the synth sometimes phrases the same event's lede
    # differently between daily + weekly ("Armenia partnership" vs
    # "U.S.–Armenia partnership"). URL is the canonical match.
    sigs = extract_daily_signatures(daily_html)
    daily_ledes = sigs["ledes"]
    daily_urls = sigs["urls"]
    if daily_ledes or daily_urls:
        original_count = len(weekly.get("events", []))
        weekly = dict(weekly)
        kept = []
        for ev in weekly.get("events", []):
            lede_norm = _normalize_lede(ev["lead"])
            # Extract any cite URL from the body
            url_m = re.search(r'class="cite"\s+href="([^"]+)"', ev.get("body_html", ""))
            ev_url = url_m.group(1).strip() if url_m else None
            if lede_norm in daily_ledes:
                continue
            if ev_url and ev_url in daily_urls:
                continue
            kept.append(ev)
        # Cap the dedup'd list at 9 — 5 render visible, up to 4 in the
        # "Show N more weekly events" expander at the bottom of the section.
        weekly["events"] = kept[:9]
        deduped = original_count - len(kept)
        if deduped:
            print(f"    dedupe: dropped {deduped} duplicates (kept {len(weekly['events'])} of which 5 visible, {max(0, len(weekly['events'])-5)} in expander)")

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

    # Prefer S3 over nginx — S3 is the authoritative live version (sometimes
    # manually patched between syntheses). Nginx is the source the morning
    # synth wrote to, which may be staler than S3 if the operator applied
    # post-synth fixes. Falls back to nginx if S3 is unreachable.
    s3_url = f"s3://{config.S3_BUCKET}/{edition_path}/index.html"
    daily_html = _s3_get(s3_url)
    if not daily_html:
        print(f"  [{edition}] S3 unreachable; falling back to nginx volume")
        daily_html = _docker_read(daily_path)

    patched = inject(daily_html, weekly, edition_path)

    out_path = RUN_DIR / f"daily_with_weekly_{edition}.html"
    out_path.write_text(patched, encoding="utf-8")

    nginx_ok = _docker_write(out_path, daily_path)
    s3_ok = _s3_put(out_path, f"s3://{config.S3_BUCKET}/{edition_path}/index.html")
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
            [config.AWS, "cloudfront", "create-invalidation",
             "--distribution-id", config.DIST_ID,
             "--paths", "/usa/index.html", "/usa/", "/china/index.html", "/china/",
             "--query", "Invalidation.Id", "--output", "text"],
            check=False,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
