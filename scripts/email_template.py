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


# Light palette designed to survive Gmail's dark-mode auto-inversion.
# Body background is pure white (#FFFFFF) — Gmail won't try to "smartly"
# darken or hue-shift it. The cream (#F5EFE2) we used before got
# misinterpreted as a "light tan we should darken." Color-scheme meta
# tags in the <head> tell Gmail this email is light-only.
PAPER = "#FFFFFF"          # body background — pure white, immune to dark-mode shifts
INK = "#1A1614"            # primary text
INK_SOFT = "#3D332C"       # subtle dividers + dek body
INK_LIGHT = "#6B5D52"      # footer / muted text
SEPIA = "#7A4F2E"          # accent — section labels + links
BLACK = "#14110F"          # masthead box background
CREAM = "#F2EBD9"          # masthead text on dark background


def render_email(us: dict, china: dict, today: str, unsubscribe_url: str) -> str:
    """Compose the HTML email.

    Each edition dict needs: headline, url (full /usa/ or /china/), events
    (list of 3 event lead strings). The dek is intentionally NOT used —
    the email shows brief headline + 3 event leads per edition, nothing
    else, per the operator's design call.
    today is an ISO date string (e.g., '2026-05-26').
    unsubscribe_url is the signed token URL specific to this subscriber.
    """
    today_pretty = dt.date.fromisoformat(today).strftime("%A · %B %-d, %Y").upper()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="only light">
<meta name="supported-color-schemes" content="only light">
<title>Briefer News — {today_pretty}</title>
<style>
  :root {{ color-scheme: only light; supported-color-schemes: only light; }}
  /* Force light treatment even in dark-mode-forcing clients */
  body, table, td {{ color-scheme: only light !important; }}
</style>
</head>
<body style="margin:0;padding:0;background:{PAPER};font-family:Georgia,'Times New Roman',serif;color:{INK};-webkit-font-smoothing:antialiased;">

<!-- Email-client wrapper: centered table for max-width control -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{PAPER};">
  <tr>
    <td align="center" style="padding:24px 12px;">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;">

        <!-- Masthead — inset dark box with cream gutters -->
        <tr><td style="padding:8px 0 18px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr><td style="background:{BLACK};color:{CREAM};padding:28px 28px 22px;text-align:center;border-radius:3px;">
              <div style="font-family:Georgia,'Times New Roman',serif;font-size:32px;font-weight:600;letter-spacing:0.01em;line-height:1;color:{CREAM};">Briefer News</div>
              <div style="font-style:italic;font-size:12px;color:#C9BFA7;letter-spacing:0.02em;margin-top:10px;">All sourcing from government · Everything cited · News without opinion</div>
            </td></tr>
          </table>
        </td></tr>

        <!-- Date stamp -->
        <tr><td style="padding:20px 24px 4px;text-align:right;font-family:Menlo,Monaco,'Courier New',monospace;font-size:10px;letter-spacing:0.22em;color:{SEPIA};">
          {today_pretty}
        </td></tr>

        <!-- U.S. edition -->
        <tr><td style="padding:8px 24px 0;">
          <div style="font-family:Menlo,Monaco,'Courier New',monospace;font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:{SEPIA};border-bottom:1px solid {INK_SOFT};padding-bottom:6px;margin-bottom:14px;font-weight:600;">U.S. Edition</div>
          <h2 style="font-family:Georgia,'Times New Roman',serif;font-size:24px;line-height:1.25;font-weight:500;color:{INK};margin:0 0 14px;">
            <a href="{us['url']}" style="color:{INK};text-decoration:none;">{html_lib.escape(us['headline'])}</a>
          </h2>
          <ul style="margin:0 0 28px;padding:0 0 0 20px;font-size:16px;line-height:1.5;color:{INK_SOFT};">
            {''.join(f'<li style="margin:0 0 8px;">{html_lib.escape(e)}</li>' for e in us.get('events', []))}
          </ul>
        </td></tr>

        <!-- Divider -->
        <tr><td style="padding:0 24px;">
          <hr style="border:none;border-top:1px solid {INK_SOFT};margin:0;">
        </td></tr>

        <!-- China edition -->
        <tr><td style="padding:24px 24px 0;">
          <div style="font-family:Menlo,Monaco,'Courier New',monospace;font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:{SEPIA};border-bottom:1px solid {INK_SOFT};padding-bottom:6px;margin-bottom:14px;font-weight:600;">China Edition</div>
          <h2 style="font-family:Georgia,'Times New Roman',serif;font-size:24px;line-height:1.25;font-weight:500;color:{INK};margin:0 0 14px;">
            <a href="{china['url']}" style="color:{INK};text-decoration:none;">{html_lib.escape(china['headline'])}</a>
          </h2>
          <ul style="margin:0 0 28px;padding:0 0 0 20px;font-size:16px;line-height:1.5;color:{INK_SOFT};">
            {''.join(f'<li style="margin:0 0 8px;">{html_lib.escape(e)}</li>' for e in china.get('events', []))}
          </ul>
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
    us_bullets = "\n".join(f"  • {e}" for e in us.get('events', []))
    china_bullets = "\n".join(f"  • {e}" for e in china.get('events', []))
    return f"""Briefer News — {today_pretty}
All sourcing from government · Everything cited · News without opinion

═══════════════════════════════════════════════════════════════
U.S. EDITION  ·  {us['url']}
═══════════════════════════════════════════════════════════════

{us['headline']}

{us_bullets}


═══════════════════════════════════════════════════════════════
CHINA EDITION  ·  {china['url']}
═══════════════════════════════════════════════════════════════

{china['headline']}

{china_bullets}


═══════════════════════════════════════════════════════════════

briefer.news · about: briefer.news/about · sources: briefer.news/sources

You're getting this because you subscribed at briefer.news.
Unsubscribe (one click, no questions): {unsubscribe_url}
"""


def _fetch_live(edition: str) -> dict:
    """Pull today's headline + top 3 event leads from the live brief for the CLI preview."""
    html = urllib.request.urlopen(f"https://briefer.news/{edition}/", timeout=20).read().decode('utf-8', errors='replace')
    h = re.search(r'<h2 class="headline">([\s\S]+?)</h2>', html)
    # Find the visible top-3 list (NOT the items-more collapsed list)
    ul = re.search(r'<ul class="items"(?! items-more)[^>]*>([\s\S]+?)</ul>', html)
    events = []
    if ul:
        items = re.findall(r'<li[^>]*>([\s\S]+?)</li>', ul.group(1))
        for item in items[:3]:
            # The event lead is the bolded prefix: <b>Lead phrase.</b>
            lead = re.search(r'<b>([\s\S]+?)</b>', item)
            if lead:
                text = re.sub(r'<[^>]+>', '', lead.group(1)).strip().rstrip('.')
                events.append(html_lib.unescape(text))
    return {
        'headline': html_lib.unescape(re.sub(r'<[^>]+>', '', h.group(1)).strip()) if h else "(no headline)",
        'events': events,
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
