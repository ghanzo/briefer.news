#!/usr/bin/env python3
"""
email_template.py — Render the daily HTML email for briefer.news.

Built for email-client compatibility: table-based layout, inline CSS, system/
serif font stack (no web fonts; Gmail / Apple Mail / Outlook strip them
inconsistently). ~600px max width. Light-only palette to survive Gmail's
dark-mode auto-inversion.

Layout (2026-06-08 redesign): a clickable masthead (wordmark + pill both link to
the site), the day's top 3 U.S. events and top 3 China events as two scannable
sections — each linking to its full brief — and a prominent "read the full briefs"
CTA. The site link is front-and-center, not buried in the footer.

Usage (module):
    from email_template import render_email
    html = render_email(us={...}, china={...}, today='2026-06-08',
                        unsubscribe_url='https://briefer.news/unsubscribe?t=...')

CLI (writes to .run/email_preview.html for visual check in browser — NO send):
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
PAPER = "#FFFFFF"          # body background — pure white, immune to dark-mode shifts
INK = "#1A1614"            # primary text
INK_SOFT = "#3D332C"       # subtle dividers + dek body
INK_LIGHT = "#6B5D52"      # footer / muted text
SEPIA = "#7A4F2E"          # accent — section labels + links
BLACK = "#14110F"          # masthead box + CTA button background
CREAM = "#F2EBD9"          # text on dark background
SITE = "https://briefer.news/"


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
    """Compose the daily HTML email: a clickable masthead (→ site), the day's top
    3 U.S. events and top 3 China events as two scannable sections each linking to
    its full brief, and a prominent site CTA. Email-client-safe (table layout,
    inline CSS, serif fonts, light-only to survive dark-mode inversion).

    `us` / `china` each need: `url` (full edition URL) and `events` (list of
    {lead, desc}; the first 3 are shown). today is an ISO date string;
    unsubscribe_url is the signed token URL for this subscriber."""
    today_pretty = dt.date.fromisoformat(today).strftime("%A · %B %-d, %Y").upper()

    def _li(e):
        lead, desc = _bullet_parts(e)
        lead_html = f'<b>{html_lib.escape(lead)}.</b> ' if lead else ''
        return f'<li style="margin:0 0 16px;padding:0;">{lead_html}{html_lib.escape(desc)}</li>'

    def _section(flag, label, data, read_label):
        events = data.get("events", [])[:3]
        if not events:
            return ""
        bullets = "".join(_li(e) for e in events)
        return f"""
        <tr><td style="padding:26px 28px 0;">
          <div style="font-family:Menlo,Monaco,'Courier New',monospace;font-size:11px;letter-spacing:0.20em;text-transform:uppercase;color:{SEPIA};border-bottom:1px solid {INK_SOFT};padding-bottom:8px;font-weight:600;">{flag}&nbsp; {label}</div>
        </td></tr>
        <tr><td style="padding:16px 28px 2px;">
          <ul style="margin:0;padding:0 0 0 22px;font-size:17px;line-height:1.5;color:{INK};">{bullets}</ul>
        </td></tr>
        <tr><td style="padding:2px 28px 6px;">
          <a href="{data['url']}" style="font-family:Menlo,Monaco,'Courier New',monospace;font-size:12px;letter-spacing:0.08em;color:{SEPIA};text-decoration:none;font-weight:600;">{read_label} &rarr;</a>
        </td></tr>"""

    us_section = _section("&#127482;&#127480;", "United States", us, "Full U.S. brief")
    china_section = _section("&#127464;&#127475;", "China", china, "Full China brief")

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
  body, table, td {{ color-scheme: only light !important; }}
</style>
</head>
<body style="margin:0;padding:0;background:{PAPER};font-family:Georgia,'Times New Roman',serif;color:{INK};-webkit-font-smoothing:antialiased;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{PAPER};">
  <tr><td align="center" style="padding:24px 12px;">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;">

      <!-- Masthead — wordmark AND pill both link to the site -->
      <tr><td style="padding:8px 0 6px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr><td style="background:{BLACK};padding:30px 28px 26px;text-align:center;border-radius:3px;">
            <a href="{SITE}" style="text-decoration:none;">
              <div style="font-family:Georgia,'Times New Roman',serif;font-size:32px;font-weight:600;letter-spacing:0.01em;line-height:1;color:{CREAM};">Briefer News</div>
            </a>
            <div style="font-style:italic;font-size:14px;color:#C9BFA7;letter-spacing:0.02em;margin-top:11px;">Government data, synthesized.</div>
            <a href="{SITE}" style="display:inline-block;margin-top:16px;font-family:Menlo,Monaco,'Courier New',monospace;font-size:11px;letter-spacing:0.18em;color:{CREAM};text-decoration:none;border:1px solid #4A4036;border-radius:3px;padding:8px 18px;">VISIT BRIEFER.NEWS &rarr;</a>
          </td></tr>
        </table>
      </td></tr>

      <!-- Date stamp -->
      <tr><td style="padding:16px 28px 0;text-align:right;font-family:Menlo,Monaco,'Courier New',monospace;font-size:10px;letter-spacing:0.22em;color:{SEPIA};">{today_pretty}</td></tr>
      {us_section}
      {china_section}

      <!-- Prominent CTA -->
      <tr><td align="center" style="padding:30px 28px 8px;">
        <a href="{SITE}" style="display:inline-block;background:{BLACK};color:{CREAM};padding:14px 32px;border-radius:3px;font-family:Menlo,Monaco,'Courier New',monospace;font-size:12px;letter-spacing:0.16em;text-transform:uppercase;font-weight:600;text-decoration:none;">Read the full briefs &rarr;</a>
      </td></tr>

      <!-- Footer -->
      <tr><td style="padding:24px 28px 32px;border-top:1px solid {INK_SOFT};">
        <p style="font-family:Menlo,Monaco,'Courier New',monospace;font-size:10px;letter-spacing:0.12em;color:{INK_LIGHT};line-height:1.6;margin:18px 0 12px;text-align:center;">
          <a href="{SITE}" style="color:{INK_LIGHT};text-decoration:none;">briefer.news</a> &nbsp;&middot;&nbsp;
          <a href="https://briefer.news/about/" style="color:{INK_LIGHT};text-decoration:none;">about</a> &nbsp;&middot;&nbsp;
          <a href="https://briefer.news/sources/" style="color:{INK_LIGHT};text-decoration:none;">sources</a> &nbsp;&middot;&nbsp;
          <a href="https://briefer.news/usa/weekly/" style="color:{INK_LIGHT};text-decoration:none;">weekly digest</a>
        </p>
        <p style="font-size:11px;color:{INK_LIGHT};line-height:1.5;margin:0;text-align:center;">
          You're getting this because you subscribed at briefer.news. <a href="{unsubscribe_url}" style="color:{INK_LIGHT};text-decoration:underline;">Unsubscribe</a> (one click, no questions).
        </p>
      </td></tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""


def render_text_fallback(us: dict, china: dict, today: str, unsubscribe_url: str) -> str:
    """Plain-text version: intro + the day's top 3 U.S. and top 3 China event
    leads. Some spam filters and minimalist clients show this instead of HTML."""
    today_pretty = dt.date.fromisoformat(today).strftime("%A, %B %-d, %Y")

    def _tb(e):
        lead, desc = _bullet_parts(e)
        return f"  • {lead}. {desc}".rstrip() if (lead and desc) else f"  • {lead or desc}"

    def _sec(label, data):
        evs = data.get("events", [])[:3]
        if not evs:
            return ""
        body = "\n".join(_tb(e) for e in evs)
        return f"{label}\n{body}\n  Full brief: {data['url']}\n"

    us_t = _sec("UNITED STATES", us)
    china_t = _sec("CHINA", china)
    return f"""Briefer News — Government data, synthesized.
{today_pretty}
Visit: {SITE}

{us_t}
{china_t}———————————————————————————————————————————————
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
    """CLI: render with today's live content + write preview to .run/email_preview.html. No send."""
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
    print(f"  US events:    {len(us['events'])}  ({', '.join(e['lead'] for e in us['events'][:3])})")
    print(f"  China events: {len(china['events'])}  ({', '.join(e['lead'] for e in china['events'][:3])})")
    print(f"  HTML preview: {out_html} ({out_html.stat().st_size:,} bytes)")
    print(f"  Text version: {out_text} ({out_text.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
