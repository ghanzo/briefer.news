#!/usr/bin/env python3
"""
email_template.py — Render the daily HTML email for briefer.news.

Built for email-client compatibility: table-based layout, inline CSS,
system font stack (no web fonts; Gmail / Apple Mail / Outlook strip
them inconsistently). ~600px max width. Sepia + cream + ink palette
matching the site.

Usage (module):
    from email_template import render_email
    html = render_email(us={...}, china={...}, today='2026-05-26',
                        unsubscribe_url='https://briefer.news/unsub?t=...')

CLI (writes to .run/email_preview.html for visual check in browser):
    python3 scripts/email_template.py
"""

from __future__ import annotations

import datetime as dt
import html as html_lib
import re
import sys
import urllib.request
from pathlib import Path


# Dark palette — inverted from the site's kraft theme. Background is ink
# black; primary text is full cream; accent is the lighter cream-tan so
# it remains legible against the dark (sepia at #7A4F2E was contrast-
# borderline against #14110F).
BLACK = "#14110F"          # background
INK_SOFT = "#3D332C"       # subtle dividers
CREAM = "#F2EBD9"          # primary text + headings
CREAM_TAN = "#C9BFA7"      # secondary text (dek body, section labels)
SEPIA = "#A6754B"          # accent — brightened sepia so links pop on dark
# Backward-compat aliases used elsewhere in the template
PAPER = BLACK
INK = CREAM
INK_LIGHT = CREAM_TAN


def render_email(us: dict, china: dict, today: str, unsubscribe_url: str) -> str:
    """Compose the HTML email.

    Each edition dict needs: headline, dek, url (full /usa/ or /china/).
    today is an ISO date string (e.g., '2026-05-26').
    unsubscribe_url is the signed token URL specific to this subscriber.
    """
    today_pretty = dt.date.fromisoformat(today).strftime("%A · %B %-d, %Y").upper()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Briefer News — {today_pretty}</title>
</head>
<body style="margin:0;padding:0;background:{PAPER};font-family:Georgia,'Times New Roman',serif;color:{INK};-webkit-font-smoothing:antialiased;">

<!-- Email-client wrapper: centered table for max-width control -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{PAPER};">
  <tr>
    <td align="center" style="padding:24px 12px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;">

        <!-- Masthead -->
        <tr><td style="background:{BLACK};color:{CREAM};padding:22px 24px 16px;text-align:center;">
          <div style="font-family:Georgia,'Times New Roman',serif;font-size:32px;font-weight:600;letter-spacing:0.01em;line-height:1;">Briefer News</div>
          <div style="font-style:italic;font-size:12px;color:#C9BFA7;letter-spacing:0.02em;margin-top:8px;">All sourcing from government · Everything cited · News without opinion</div>
        </td></tr>

        <!-- Date stamp -->
        <tr><td style="padding:20px 24px 4px;text-align:right;font-family:Menlo,Monaco,'Courier New',monospace;font-size:10px;letter-spacing:0.22em;color:{SEPIA};">
          {today_pretty}
        </td></tr>

        <!-- U.S. edition -->
        <tr><td style="padding:8px 24px 0;">
          <div style="font-family:Menlo,Monaco,'Courier New',monospace;font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:{SEPIA};border-bottom:1px solid {INK_SOFT};padding-bottom:6px;margin-bottom:14px;font-weight:600;">U.S. Edition</div>
          <h2 style="font-family:Georgia,'Times New Roman',serif;font-size:24px;line-height:1.25;font-weight:500;color:{INK};margin:0 0 12px;">
            {html_lib.escape(us['headline'])}
          </h2>
          <p style="font-size:17px;line-height:1.55;color:{INK_SOFT};margin:0 0 16px;">
            {html_lib.escape(us['dek'])}
          </p>
          <p style="margin:4px 0 28px;">
            <a href="{us['url']}" style="font-family:Menlo,Monaco,'Courier New',monospace;font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:{SEPIA};text-decoration:none;border-bottom:1px dotted {SEPIA};padding-bottom:2px;">
              Read the full brief &rarr;
            </a>
          </p>
        </td></tr>

        <!-- Divider -->
        <tr><td style="padding:0 24px;">
          <hr style="border:none;border-top:1px solid {INK_SOFT};margin:0;">
        </td></tr>

        <!-- China edition -->
        <tr><td style="padding:24px 24px 0;">
          <div style="font-family:Menlo,Monaco,'Courier New',monospace;font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:{SEPIA};border-bottom:1px solid {INK_SOFT};padding-bottom:6px;margin-bottom:14px;font-weight:600;">China Edition</div>
          <h2 style="font-family:Georgia,'Times New Roman',serif;font-size:24px;line-height:1.25;font-weight:500;color:{INK};margin:0 0 12px;">
            {html_lib.escape(china['headline'])}
          </h2>
          <p style="font-size:17px;line-height:1.55;color:{INK_SOFT};margin:0 0 16px;">
            {html_lib.escape(china['dek'])}
          </p>
          <p style="margin:4px 0 28px;">
            <a href="{china['url']}" style="font-family:Menlo,Monaco,'Courier New',monospace;font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:{SEPIA};text-decoration:none;border-bottom:1px dotted {SEPIA};padding-bottom:2px;">
              Read the full brief &rarr;
            </a>
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:24px 24px 32px;border-top:1px solid {INK_SOFT};">
          <p style="font-family:Menlo,Monaco,'Courier New',monospace;font-size:10px;letter-spacing:0.12em;color:{INK_LIGHT};line-height:1.6;margin:0 0 12px;text-align:center;">
            <a href="https://briefer.news/" style="color:{INK_LIGHT};text-decoration:none;">briefer.news</a>
            &nbsp;·&nbsp;
            <a href="https://briefer.news/about/" style="color:{INK_LIGHT};text-decoration:none;">about</a>
            &nbsp;·&nbsp;
            <a href="https://briefer.news/sources/" style="color:{INK_LIGHT};text-decoration:none;">sources</a>
            &nbsp;·&nbsp;
            <a href="https://briefer.news/usa/weekly/" style="color:{INK_LIGHT};text-decoration:none;">weekly digest</a>
          </p>
          <p style="font-size:11px;color:{INK_LIGHT};line-height:1.5;margin:0;text-align:center;">
            You're getting this because you subscribed at briefer.news. <a href="{unsubscribe_url}" style="color:{INK_LIGHT};text-decoration:underline;">Unsubscribe</a> (one click, no questions).
          </p>
        </td></tr>

      </table>
    </td>
  </tr>
</table>

</body>
</html>"""


def render_text_fallback(us: dict, china: dict, today: str, unsubscribe_url: str) -> str:
    """Plain-text version for clients that prefer/require text/plain. Some
    spam filters and minimalist clients show this instead of the HTML."""
    today_pretty = dt.date.fromisoformat(today).strftime("%A, %B %-d, %Y")
    return f"""Briefer News — {today_pretty}
All sourcing from government · Everything cited · News without opinion

═══════════════════════════════════════════════════════════════
U.S. EDITION
═══════════════════════════════════════════════════════════════

{us['headline']}

{us['dek']}

Read the full brief: {us['url']}


═══════════════════════════════════════════════════════════════
CHINA EDITION
═══════════════════════════════════════════════════════════════

{china['headline']}

{china['dek']}

Read the full brief: {china['url']}


═══════════════════════════════════════════════════════════════

briefer.news · about: briefer.news/about · sources: briefer.news/sources

You're getting this because you subscribed at briefer.news.
Unsubscribe (one click, no questions): {unsubscribe_url}
"""


def _fetch_live(edition: str) -> dict:
    """Pull today's headline + dek from the live brief for the CLI preview."""
    html = urllib.request.urlopen(f"https://briefer.news/{edition}/", timeout=20).read().decode('utf-8', errors='replace')
    h = re.search(r'<h2 class="headline">([^<]+)</h2>', html)
    d = re.search(r'<p class="dek">([\s\S]+?)</p>', html)
    return {
        'headline': html_lib.unescape(h.group(1).strip()) if h else "(no headline)",
        'dek': html_lib.unescape(re.sub(r'<[^>]+>', '', d.group(1)).strip()) if d else "(no dek)",
        'url': f"https://briefer.news/{edition}/",
    }


def _cli() -> int:
    """CLI: render with today's live content + write preview to .run/email_preview.html."""
    today = dt.date.today().isoformat()
    us = _fetch_live('usa')
    china = _fetch_live('china')
    unsub = "https://briefer.news/unsubscribe?token=PREVIEW_TOKEN"

    html = render_email(us, china, today, unsub)
    text = render_text_fallback(us, china, today, unsub)

    out_html = Path(__file__).resolve().parent.parent / ".run" / "email_preview.html"
    out_text = Path(__file__).resolve().parent.parent / ".run" / "email_preview.txt"
    out_html.parent.mkdir(exist_ok=True)
    out_html.write_text(html, encoding='utf-8')
    out_text.write_text(text, encoding='utf-8')
    print(f"  HTML preview: {out_html} ({out_html.stat().st_size:,} bytes)")
    print(f"  Text version: {out_text} ({out_text.stat().st_size:,} bytes)")
    print(f"  Open the HTML in a browser to see the rendered email.")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
