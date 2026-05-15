#!/usr/bin/env python3
"""
inject_weekly_preview.py — Read each edition's weekly digest headline
from the nginx volume and patch it into today's deployed daily brief
as a small "This week" callout immediately below the thread strip.

Intended to run from daily_digests.sh AFTER weekly.sh, so the callout
reflects the just-synthesized weekly. Also handles backfill scenarios
where the daily was rendered before the weekly-preview CSS / HTML was
introduced — the script injects the CSS too if missing.

Usage:
  python3 scripts/inject_weekly_preview.py
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
    /* This-week preview — backfill 2026-05-14 evening */
    .weekly-preview { margin: -12px 0 22px; padding: 0; }
    .weekly-preview a {
      display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
      color: var(--sepia); text-decoration: none; padding-bottom: 4px;
      border-bottom: 1px dotted transparent;
    }
    .weekly-preview a:hover { border-bottom-color: var(--sepia); }
    .weekly-preview-label {
      font-family: 'IBM Plex Mono', ui-monospace, monospace;
      font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase;
      font-weight: 600; white-space: nowrap; color: var(--sepia);
    }
    .weekly-preview-headline {
      font-family: 'EB Garamond', Garamond, Georgia, serif;
      font-style: italic; font-size: 16px; line-height: 1.4;
      color: var(--ink); font-weight: 400;
    }
    .weekly-preview-arrow { color: var(--sepia); font-weight: 500; }
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
    """Push local_path into the nginx-shared docker volume via an alpine
    one-shot container. The nginx container mounts the volume read-only
    so `docker cp` into it fails; using alpine with the volume mounted
    RW matches the pattern used by synth/og_weekly/weekly scripts.

    dst_path: path inside the volume, e.g. /usr/share/nginx/html/usa/index.html
    (we map this to /dst/usa/index.html since the alpine container mounts
    briefernewsapp_site_output at /dst).
    """
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


def extract_weekly_headline(html: str) -> str | None:
    """Pull the <h2 class=\"headline\"> text from a weekly digest page."""
    m = re.search(r'<h2 class="headline">\s*(.+?)\s*</h2>', html, re.DOTALL)
    if not m:
        return None
    text = re.sub(r"\s+", " ", m.group(1)).strip()
    return text


def inject(daily_html: str, weekly_headline: str, edition_path: str) -> str:
    """Patch daily HTML with .weekly-preview block + CSS (if missing)."""
    # Decode entity references so the headline reads cleanly inside <span>
    headline_text = html_lib.unescape(weekly_headline)
    # Re-escape for safe insertion
    safe_headline = html_lib.escape(headline_text, quote=False)

    preview_html = (
        f'\n  <p class="weekly-preview">\n'
        f'    <a href="/{edition_path}/weekly/">\n'
        f'      <span class="weekly-preview-label">&#8599; This week</span>\n'
        f'      <span class="weekly-preview-headline">&ldquo;{safe_headline}&rdquo;</span>\n'
        f'      <span class="weekly-preview-arrow">&rarr;</span>\n'
        f'    </a>\n'
        f'  </p>\n'
    )

    # Remove any previously-injected preview (idempotent)
    daily_html = re.sub(
        r'\n\s*<p class="weekly-preview">.*?</p>\n',
        "\n",
        daily_html, flags=re.DOTALL,
    )

    # Inject CSS if not already present
    if ".weekly-preview" not in daily_html:
        daily_html = daily_html.replace("</style>", WEEKLY_PREVIEW_CSS + "\n  </style>", 1)

    # Insert preview after the thread strip's closing </p>
    new_html, n = re.subn(
        r'(<p class="thread-strip">.*?</p>)',
        lambda m: m.group(1) + preview_html.rstrip("\n"),
        daily_html, count=1, flags=re.DOTALL,
    )
    if n == 0:
        # Fallback: insert after the dek if thread-strip not present
        new_html, n = re.subn(
            r'(<p class="dek">.*?</p>)',
            lambda m: m.group(1) + preview_html.rstrip("\n"),
            daily_html, count=1, flags=re.DOTALL,
        )
    return new_html


def process_edition(edition: str) -> bool:
    """edition in {'us', 'china'}"""
    edition_path = "usa" if edition == "us" else "china"

    weekly_path = f"/usr/share/nginx/html/{edition_path}/weekly/index.html"
    daily_path = f"/usr/share/nginx/html/{edition_path}/index.html"

    weekly_html = _docker_read(weekly_path)
    if not weekly_html:
        print(f"  [{edition}] no weekly digest found at {weekly_path} — skipping")
        return False

    headline = extract_weekly_headline(weekly_html)
    if not headline:
        print(f"  [{edition}] could not parse weekly headline — skipping")
        return False
    print(f"  [{edition}] weekly headline: {headline[:80]}...")

    daily_html = _docker_read(daily_path)
    if not daily_html:
        print(f"  [{edition}] daily not in nginx volume; falling back to S3")
        daily_html = _s3_get(f"s3://briefer-news-site/{edition_path}/index.html")

    patched = inject(daily_html, headline, edition_path)

    # Write patched HTML to .run + push to nginx volume + push to S3
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
        # CloudFront invalidation for both daily roots
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
