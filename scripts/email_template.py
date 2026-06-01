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


def _bullet_parts(e) -> tuple[str, str]:
    """Normalize an event to (lead, desc). Accepts the {lead, desc} dict the
    extractors produce, or a bare string (legacy = lead only)."""
    if isinstance(e, dict):
        return (e.get("lead") or "").strip(), (e.get("desc") or "").strip()
    return str(e).strip(), ""


def extract_events(brief_html: str, n: int = 3) -> list[dict]:
    """Top-n VISIBLE events from a rendered brief as {lead, desc} dicts.

    lead = the <b>…</b> topic phrase; desc = the sentence(s) after </summary>,
    with the citation <sup> and the <span class="when"> date/source tag removed.
    Reads only the visible <ul class="items"> list, never the items-more
    collapsed block. Shared by the live send (email_send.py) and the CLI preview
    so the two can't drift."""
    ul = re.search(r'<ul class="items"(?! items-more)[^>]*>([\s\S]+?)</ul>', brief_html)
    if not ul:
        return []
    out = []
    for item in re.findall(r'<li[^>]*>([\s\S]+?)</li>', ul.group(1))[:n]:
        b = re.search(r'<b>([\s\S]+?)</b>', item)
        lead = html_lib.unescape(re.sub(r'<[^>]+>', '', b.group(1))).strip().rstrip('.') if b else ''
        after = item.split('</summary>', 1)[1] if '</summary>' in item else item
        after = re.sub(r'<sup[\s\S]*?</sup>', '', after)                 # drop citation markers
        after = re.sub(r'<span class="when"[\s\S]*?</span>', '', after)  # drop the date/source tag
        desc = html_lib.unescape(re.sub(r'<[^>]+>', ' ', after))
        desc = re.sub(r'\s+', ' ', desc).strip()
        if lead or desc:
            out.append({"lead": lead, "desc": desc})
    return out


def render_email(us: dict, china: dict, today: str, unsubscribe_url: str) -> str:
    """Compose the daily HTML email — a deliberately simple, scannable layout
    (operator's 2026-06-01 redesign): a one-line intro ("Briefer News —
    government data, synthesized") and the day's top 3 U.S. event leads as
    bullets, each on its own line, then a link to the full brief.

    `us` needs: url (full /usa/) and events (list of event lead strings; the
    first 3 are shown). `china` is accepted for backward compatibility with the
    caller but intentionally NOT rendered — China still publishes on the site,
    just not in the daily email. today is an ISO date string; unsubscribe_url is
    the signed token URL for this subscriber.
    """
    today_pretty = dt.date.fromisoformat(today).strftime("%A · %B %-d, %Y").upper()

    def _li(e):
        lead, desc = _bullet_parts(e)
        lead_html = f'<b>{html_lib.escape(lead)}.</b> ' if lead else ''
        return f'<li style="margin:0 0 18px;padding:0;">{lead_html}{html_lib.escape(desc)}</li>'

    bullets = "".join(_li(e) for e in us.get("events", [])[:3])
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

        <!-- Masthead — inset dark box; tagline IS the intro -->
        <tr><td style="padding:8px 0 18px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr><td style="background:{BLACK};color:{CREAM};padding:30px 28px 26px;text-align:center;border-radius:3px;">
              <div style="font-family:Georgia,'Times New Roman',serif;font-size:32px;font-weight:600;letter-spacing:0.01em;line-height:1;color:{CREAM};">Briefer News</div>
              <div style="font-style:italic;font-size:14px;color:#C9BFA7;letter-spacing:0.02em;margin-top:12px;">Government data, synthesized.</div>
            </td></tr>
          </table>
        </td></tr>

        <!-- Date stamp -->
        <tr><td style="padding:18px 28px 0;text-align:right;font-family:Menlo,Monaco,'Courier New',monospace;font-size:10px;letter-spacing:0.22em;color:{SEPIA};">
          {today_pretty}
        </td></tr>

        <!-- Lead-in label -->
        <tr><td style="padding:16px 28px 0;">
          <div style="font-family:Menlo,Monaco,'Courier New',monospace;font-size:11px;letter-spacing:0.22em;text-transform:uppercase;color:{SEPIA};border-bottom:1px solid {INK_SOFT};padding-bottom:8px;font-weight:600;">Today · top developments</div>
        </td></tr>

        <!-- Three bullets, each on its own line -->
        <tr><td style="padding:18px 28px 4px;">
          <ul style="margin:0;padding:0 0 0 22px;font-size:18px;line-height:1.5;color:{INK};">
            {bullets}
          </ul>
        </td></tr>

        <!-- Read the full brief -->
        <tr><td style="padding:14px 28px 30px;">
          <a href="{us['url']}" style="font-family:Menlo,Monaco,'Courier New',monospace;font-size:13px;letter-spacing:0.08em;color:{SEPIA};text-decoration:none;font-weight:600;">Read today's full brief →</a>
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:22px 28px 32px;border-top:1px solid {INK_SOFT};">
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
    """Plain-text version (US-only, matching the simplified HTML): intro + the
    day's top 3 U.S. event leads as bullets. Some spam filters and minimalist
    clients show this instead of the HTML. `china` is unused (see render_email)."""
    today_pretty = dt.date.fromisoformat(today).strftime("%A, %B %-d, %Y")

    def _tb(e):
        lead, desc = _bullet_parts(e)
        return f"  • {lead}. {desc}".rstrip() if (lead and desc) else f"  • {lead or desc}"

    bullets = "\n".join(_tb(e) for e in us.get('events', [])[:3])
    return f"""Briefer News — Government data, synthesized.
{today_pretty}

TODAY · TOP DEVELOPMENTS

{bullets}

Read today's full brief: {us['url']}

———————————————————————————————————————————————
briefer.news · about: briefer.news/about · sources: briefer.news/sources

You're getting this because you subscribed at briefer.news.
Unsubscribe (one click, no questions): {unsubscribe_url}
"""


def _fetch_live(edition: str) -> dict:
    """Pull today's headline + top 3 events from the live brief for the CLI preview."""
    html = urllib.request.urlopen(f"https://briefer.news/{edition}/", timeout=20).read().decode('utf-8', errors='replace')
    h = re.search(r'<h2 class="headline">([\s\S]+?)</h2>', html)
    return {
        'headline': html_lib.unescape(re.sub(r'<[^>]+>', '', h.group(1)).strip()) if h else "(no headline)",
        'events': extract_events(html),
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
