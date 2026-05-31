#!/usr/bin/env python3
"""brief_parser.py — the single source of truth for reading a rendered
briefer.news brief (US or China edition) into structured data.

Why this exists: the brief HTML is an unversioned contract with ~12 consumers
(weekly_aggregate, morning_brief_gather, build_feeds, drafter, researcher,
threads_propose, inject_weekly_preview, email_send, …). They each hard-coded
their own regex against the markup, so the 2026-05-27 progressive-disclosure
change silently broke several (weekly extracted 0 bullets, the scorer failed
its dek check forever). This module is the ONE place that understands the
current shape; point every consumer at parse_brief() and the next structural
change breaks in exactly one loud, tested place.

Stdlib only (no bs4) — matches the rest of scripts/ so it runs on the host
without a venv. The synth output is a stable machine-generated template, so
targeted regex over it is reliable; the fixtures in tests keep it honest.

Public API:
    parse_brief(html: str) -> dict      # the union-of-fields contract below
    parse_url(url: str)    -> dict
    parse_file(path)       -> dict

Returned dict (see UNION below):
    date, headline, headline_words, title, canonical, meta_description,
    dek (None post-2026-05-27), threads ([]),
    events[]  {lead, body, desc, cite_url, cite_title, cite_marker,
               when_raw, date_label, source, tier}   tier∈visible|more|week|allied
    events_visible_count, events_more_count,
    voices[]  {quote, speaker, date_label, cite_url, cite_title, cite_marker}
    sources[] {publisher, title, url, marker}
    section_labels[], has_more_events, has_voices, has_this_week,
    has_allied, has_outside_gate, strategy_cards (None)

CLI:
    python3 scripts/brief_parser.py .run/usa_brief_today.html
    python3 scripts/brief_parser.py https://briefer.news/china/ --json
"""
from __future__ import annotations

import argparse
import html as _html
import json
import re
import sys
import urllib.request
from pathlib import Path

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _text(s: str | None) -> str:
    """Strip tags, unescape entities, collapse whitespace."""
    if not s:
        return ""
    s = _TAG_RE.sub("", s)
    s = _html.unescape(s)
    return _WS_RE.sub(" ", s).strip()


def _attr(tag: str, name: str) -> str | None:
    m = re.search(rf'{name}="([^"]*)"', tag)
    return _html.unescape(m.group(1)) if m else None


def _first(pattern: str, text: str, flags=re.S) -> str | None:
    m = re.search(pattern, text, flags)
    return m.group(1) if m else None


def _ul_inner(html: str, exact_class: str) -> str | None:
    """Return the inner HTML of <ul class="EXACT">…</ul> (exact class match,
    non-greedy to the first </ul> — event <li>s never nest a <ul>)."""
    m = re.search(rf'<ul class="{re.escape(exact_class)}">(.*?)</ul>', html, re.S)
    return m.group(1) if m else None


def _parse_event_li(li: str, tier: str) -> dict:
    # Lead: the <summary> wrapper (old collapsible-event layout) OR the opening
    # <b>...</b> (flat full-body layout, 2026-05-30: all events visible, no
    # chevron). Support BOTH so frozen-fixture renders and new renders parse.
    lead_html = _first(r"<summary[^>]*>(.*?)</summary>", li)
    if not lead_html:
        lead_html = _first(r"<b>(.*?)</b>", li)
    lead = _text(lead_html)
    # Body = text after the lead, up to the first <sup> or <span class="when">.
    if "</summary>" in li:
        after = li.split("</summary>", 1)[1]
    elif "</b>" in li:
        after = li.split("</b>", 1)[1]
    else:
        after = li
    body_html = re.split(r'<sup\b|<span class="when"', after, 1)[0]
    body = _text(body_html)
    cite_url = cite_title = cite_marker = None
    cm = re.search(r'<a class="cite"([^>]*)>(.*?)</a>',li, re.S)
    if cm:
        cite_url = _attr(cm.group(1), "href")
        cite_title = _attr(cm.group(1), "title")
        cite_marker = _text(cm.group(2))
    when_raw = _text(_first(r'<span class="when">(.*?)</span>', li))
    date_label, source = "", ""
    if when_raw:
        parts = re.split(r"\s*[·]\s*", when_raw, 1)
        date_label = parts[0].strip()
        source = parts[1].strip() if len(parts) > 1 else ""
    return {
        "lead": lead, "body": body, "desc": body,
        "cite_url": cite_url, "cite_title": cite_title, "cite_marker": cite_marker,
        "when_raw": when_raw, "date_label": date_label, "source": source,
        "tier": tier,
    }


def _events_for_tier(html: str, exact_class: str, tier: str) -> list[dict]:
    inner = _ul_inner(html, exact_class)
    if inner is None:
        return []
    return [_parse_event_li(li, tier)
            for li in re.findall(r"<li>(.*?)</li>", inner, re.S)]


def _parse_voices(html: str) -> list[dict]:
    region = _first(r'<div class="voices">(.*?)</div>', html)
    if region is None:
        return []
    out = []
    for bq in re.findall(r'<blockquote class="pull">(.*?)</blockquote>', region, re.S):
        quote = _text(_first(r"<p>(.*?)</p>", bq)).strip("“”\"")
        cite_block = _first(r"<cite>(.*?)</cite>", bq) or ""
        cite_url = cite_title = cite_marker = None
        cm = re.search(r'<a class="cite"([^>]*)>(.*?)</a>',cite_block, re.S)
        if cm:
            cite_url = _attr(cm.group(1), "href")
            cite_title = _attr(cm.group(1), "title")
            cite_marker = _text(cm.group(2))
        # Attribution text is everything before the <sup> citation.
        attr = _text(re.split(r"<sup\b", cite_block, 1)[0])
        speaker, date_label = attr, ""
        parts = re.split(r"\s*[·]\s*", attr, 1)
        if len(parts) > 1:
            speaker, date_label = parts[0].strip(), parts[1].strip()
        out.append({"quote": quote, "speaker": speaker, "date_label": date_label,
                    "cite_url": cite_url, "cite_title": cite_title,
                    "cite_marker": cite_marker})
    return out


def _parse_sources(html: str) -> list[dict]:
    sec = _first(r'<section class="sources">(.*?)</section>', html)
    if sec is None:
        return []
    out = []
    for ol_tag, ol_inner in re.findall(r"<ol\b([^>]*)>(.*?)</ol>", sec, re.S):
        lettered = 'type="a"' in ol_tag
        for i, li in enumerate(re.findall(r"<li>(.*?)</li>", ol_inner, re.S)):
            pub = _text(_first(r'<span class="pub">(.*?)</span>', li))
            url = _attr(re.search(r"<a\b([^>]*)>", li).group(1), "href") \
                if re.search(r"<a\b([^>]*)>", li) else None
            # Title sits between the curly quotes that follow </span>.
            tail = li.split("</span>", 1)[1] if "</span>" in li else li
            title = _text(_first(r"“(.*?)”", _html.unescape(tail)))
            marker = chr(ord("a") + i) if lettered else str(i + 1)
            out.append({"publisher": pub, "title": title, "url": url,
                        "marker": marker})
    return out


def parse_brief(html: str) -> dict:
    """Parse a rendered brief HTML string into the union-of-fields contract."""
    headline = _text(_first(r'<h2 class="headline">(.*?)</h2>', html))
    visible = _events_for_tier(html, "items", "visible")
    more = _events_for_tier(html, "items items-more", "more")
    week = _events_for_tier(html, "items week-items", "week")
    allied = _events_for_tier(html, "items allied-items", "allied")
    events = visible + more + week + allied

    section_labels = [_text(s) for s in
                      re.findall(r'<h3 class="section-label">(.*?)</h3>', html, re.S)]

    # dek: removed from the body 2026-05-27. None for current briefs.
    dek_block = _first(r'<ul class="dek-bullets">(.*?)</ul>', html) \
        or _first(r'<p class="dek">(.*?)</p>', html)
    dek = _text(dek_block) or None

    return {
        "date": _text(_first(r'<div class="stamp">(.*?)</div>', html)),
        "title": _text(_first(r"<title>(.*?)</title>", html)),
        "canonical": _attr(re.search(r"<link rel=\"canonical\"([^>]*)>", html).group(1),
                            "href") if re.search(r'<link rel="canonical"', html) else None,
        "meta_description": _attr(
            re.search(r'<meta name="description"([^>]*)>', html).group(1), "content")
            if re.search(r'<meta name="description"', html) else None,
        "headline": headline,
        "headline_words": len(headline.split()) if headline else 0,
        "dek": dek,
        "threads": [],
        "events": events,
        "events_visible_count": len(visible),
        "events_more_count": len(more),
        "voices": _parse_voices(html),
        "sources": _parse_sources(html),
        "section_labels": section_labels,
        "has_more_events": bool(more) or 'class="more-events"' in html,
        "has_voices": bool(_parse_voices(html)),
        "has_this_week": bool(week) or "This week" in " ".join(section_labels),
        "has_allied": bool(allied),
        "has_outside_gate": "Outside the Gate" in " ".join(section_labels),
        "strategy_cards": None,
    }


def parse_url(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "brief_parser/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return parse_brief(r.read().decode("utf-8", "replace"))


def parse_file(path) -> dict:
    return parse_brief(Path(path).read_text(encoding="utf-8"))


def _summary(d: dict) -> str:
    lines = [
        f"date            : {d['date']}",
        f"headline        : {d['headline']}  ({d['headline_words']} words)",
        f"meta_description: {'present' if d['meta_description'] else 'MISSING'}"
        f" ({len(d['meta_description'] or '')} chars)",
        f"dek (on-page)   : {'present' if d['dek'] else 'none (expected post-2026-05-27)'}",
        f"events          : {d['events_visible_count']} visible + {d['events_more_count']} more"
        f" + {sum(1 for e in d['events'] if e['tier']=='week')} week"
        f" + {sum(1 for e in d['events'] if e['tier']=='allied')} allied"
        f"  = {len(d['events'])} total",
        f"voices          : {len(d['voices'])}",
        f"sources         : {len(d['sources'])}",
        f"sections        : {', '.join(d['section_labels'])}",
        f"flags           : more={d['has_more_events']} voices={d['has_voices']}"
        f" week={d['has_this_week']} allied={d['has_allied']} outside_gate={d['has_outside_gate']}",
        f"canonical       : {d['canonical']}",
    ]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Parse a rendered briefer.news brief.")
    ap.add_argument("source", help="path to an .html file or an http(s) URL")
    ap.add_argument("--json", action="store_true", help="emit the full parsed dict as JSON")
    args = ap.parse_args(argv)
    d = parse_url(args.source) if args.source.startswith("http") else parse_file(args.source)
    print(json.dumps(d, indent=2, ensure_ascii=False) if args.json else _summary(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
