#!/usr/bin/env python3
"""
weekly_aggregate.py — Read the past 7 days of archived daily briefs for
one edition and emit a structured JSON document with every section the
weekly synth needs.

Reuses the same nginx-volume-via-docker-exec pattern as the rest of
the pipeline. Pulls:
  - headline
  - dek (if present — older briefs lacked one)
  - thread chips (if present — landed 2026-05-15)
  - voices (with attribution, cite url, cite title, date label)
  - bullets (lead, desc, cite url, cite title, source, date label)
  - strategy_cards (China edition only — Strategic Backdrop section)

Missing sections are returned as null / empty list — the synth tolerates.

Usage:
  python3 scripts/weekly_aggregate.py us|china YYYY-MM-DD [output_path]
"""

from __future__ import annotations

import html as html_lib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUN_DIR = REPO / ".run"
NGINX_CONTAINER = "briefer_nginx"
ARCHIVE_BASE = "/usr/share/nginx/html"


# ── Section-level regexes ───────────────────────────────────────────────────

HEADLINE_RE = re.compile(
    r'<h2 class="headline">\s*(.+?)\s*</h2>', re.DOTALL
)
# Dek: new bulleted form (post 2026-05-27) preferred; legacy paragraph fallback.
DEK_BULLETS_RE = re.compile(r'<ul class="dek-bullets">(.+?)</ul>', re.DOTALL)
DEK_BULLET_LI_RE = re.compile(r'<li[^>]*>(.+?)</li>', re.DOTALL)
DEK_RE = re.compile(
    r'<p class="dek">(.+?)</p>', re.DOTALL
)
THREAD_STRIP_RE = re.compile(
    r'<p class="thread-strip">(.+?)</p>', re.DOTALL
)
THREAD_CHIP_RE = re.compile(
    r'<span class="thread-chip">(?:\s*<b>([^<]+)</b>\s*&middot;\s*([^<]+))</span>',
    re.DOTALL,
)
ITEMS_BLOCK_RE = re.compile(
    r'<ul class="items">(.+?)</ul>', re.DOTALL
)
BULLET_LI_RE = re.compile(
    r'<li>\s*'
    r'<b>(?P<lead>[^<]+)</b>\s*'
    r'(?P<desc>.*?)'
    r'<sup>\s*<a[^>]*\bclass="cite"[^>]*\bhref="(?P<url>[^"]+)"'
    r'[^>]*\btitle="(?P<src_title>[^"]+)"[^>]*>(?P<marker>[^<]+)</a>\s*</sup>'
    r'(?P<rest>.*?)'
    r'</li>',
    re.DOTALL,
)
WHEN_SPAN_RE = re.compile(
    r'<span class="when">([^<]+)</span>', re.DOTALL
)
PULL_BLOCK_RE = re.compile(
    r'<blockquote class="pull">(.+?)</blockquote>', re.DOTALL
)
PULL_QUOTE_RE = re.compile(
    r'<p>\s*&ldquo;(.+?)&rdquo;\s*</p>', re.DOTALL
)
PULL_CITE_RE = re.compile(
    r'<cite>(?P<attribution>.+?)<sup>\s*<a[^>]*\bclass="cite"[^>]*\bhref="(?P<url>[^"]+)"'
    r'[^>]*\btitle="(?P<src_title>[^"]+)"[^>]*>(?P<marker>[^<]+)</a>\s*</sup>\s*</cite>',
    re.DOTALL,
)
BACKDROP_BLOCK_RE = re.compile(
    r'<div class="backdrop">(.+?)</div>\s*(?:<h3|<div|<section)',
    re.DOTALL,
)
STRATEGY_ARTICLE_RE = re.compile(
    r'<article>\s*'
    r'<h4 class="strategy-title">([^<]+)</h4>\s*'
    r'<p class="strategy-status">([^<]+)</p>\s*'
    r'<p class="strategy-blurb">([^<]+)</p>\s*'
    r'</article>',
    re.DOTALL,
)


# ── Volume reads ────────────────────────────────────────────────────────────

def _list_archive_files(edition_path: str) -> list[str]:
    try:
        out = subprocess.check_output(
            ["docker", "exec", NGINX_CONTAINER, "sh", "-c",
             f"ls {ARCHIVE_BASE}/{edition_path}/archive/ 2>/dev/null"],
            text=True, timeout=15,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []
    return [n.strip() for n in out.splitlines()
            if re.match(r"^\d{4}-\d{2}-\d{2}\.html$", n.strip())]


def _read_archive_file(edition_path: str, filename: str) -> str:
    try:
        return subprocess.check_output(
            ["docker", "exec", NGINX_CONTAINER, "cat",
             f"{ARCHIVE_BASE}/{edition_path}/archive/{filename}"],
            text=True, timeout=15,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""


# ── Parsing helpers ────────────────────────────────────────────────────────

def _clean_text(raw: str) -> str:
    """Strip whitespace, collapse internal whitespace, unescape entities."""
    text = html_lib.unescape(raw).strip()
    return re.sub(r"\s+", " ", text)


def _split_when(when_raw: str) -> tuple[str, str]:
    """Parse '<DATE> · <SOURCE>' → (date_label, source)."""
    parts = re.split(r"\s*(?:·|·)\s*", when_raw, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return when_raw, ""


def extract_headline(html: str) -> str | None:
    m = HEADLINE_RE.search(html)
    if not m:
        return None
    return _clean_text(m.group(1))


def extract_dek(html: str) -> str | None:
    """Return dek text (bullets joined by ' · ' or legacy paragraph)."""
    m = DEK_BULLETS_RE.search(html)
    if m:
        bullets = [_clean_text(b) for b in DEK_BULLET_LI_RE.findall(m.group(1))]
        joined = " · ".join(b for b in bullets if b)
        return joined or None
    m = DEK_RE.search(html)
    if not m:
        return None
    return _clean_text(m.group(1))


def extract_threads(html: str) -> list[str]:
    m = THREAD_STRIP_RE.search(html)
    if not m:
        return []
    chips = []
    for chip_m in THREAD_CHIP_RE.finditer(m.group(1)):
        count_part = _clean_text(chip_m.group(1))
        name_part = _clean_text(chip_m.group(2))
        chips.append(f"{count_part} · {name_part}")
    return chips


def extract_bullets(html: str) -> list[dict]:
    bullets: list[dict] = []
    for items_m in ITEMS_BLOCK_RE.finditer(html):
        block = items_m.group(1)
        for li_m in BULLET_LI_RE.finditer(block):
            when_match = WHEN_SPAN_RE.search(li_m.group("rest"))
            when_raw = _clean_text(when_match.group(1)) if when_match else ""
            date_label, source = _split_when(when_raw)
            bullets.append({
                "lead": _clean_text(li_m.group("lead")),
                "desc": _clean_text(li_m.group("desc")),
                "marker": _clean_text(li_m.group("marker")),
                "url": html_lib.unescape(li_m.group("url")),
                "src_title": _clean_text(li_m.group("src_title")),
                "when_raw": when_raw,
                "date_label": date_label,
                "source": source,
            })
    return bullets


_VOICE_DATE_FORMATS = ("%B %d", "%b %d", "%b. %d")


def _parse_voice_date(date_label: str, today: date) -> Optional[date]:
    """Parse a voice cite's date label ('May 14' / 'Apr 24' / 'Apr. 24')
    against today's year. Returns None if unparseable.

    If parsed-date is in the future relative to today, assume the date
    rolled over from the previous year (Dec 31 vs Jan 1 case).
    """
    if not date_label:
        return None
    cleaned = date_label.strip().rstrip(".")
    for fmt in _VOICE_DATE_FORMATS:
        try:
            parsed = datetime.strptime(cleaned, fmt).date().replace(year=today.year)
            if parsed > today:
                parsed = parsed.replace(year=today.year - 1)
            return parsed
        except ValueError:
            continue
    return None


def extract_voices(html: str, today: Optional[date] = None,
                   week_start: Optional[date] = None) -> list[dict]:
    """Extract voices from a daily brief's HTML.

    When today + week_start are provided, voices whose cite date falls
    outside [week_start, today] are dropped — enforces WEEKLY.md's hard
    quote-recency rule before the synth ever sees them.

    Voices with unparseable date labels are kept (better to surface a
    candidate the synth can verify than to silently drop signal).
    """
    voices: list[dict] = []
    for pull_m in PULL_BLOCK_RE.finditer(html):
        block = pull_m.group(1)
        quote_m = PULL_QUOTE_RE.search(block)
        cite_m = PULL_CITE_RE.search(block)
        if not quote_m or not cite_m:
            continue
        quote = _clean_text(quote_m.group(1))
        attribution_raw = cite_m.group("attribution")
        # Attribution is typically "Speaker name &middot; DATE" — split on the middot
        attribution_clean = _clean_text(attribution_raw)
        parts = re.split(r"\s*(?:·|·)\s*", attribution_clean, maxsplit=1)
        if len(parts) == 2:
            speaker = parts[0].strip()
            date_label = parts[1].strip()
        else:
            speaker = attribution_clean
            date_label = ""

        if today and week_start and date_label:
            parsed = _parse_voice_date(date_label, today)
            if parsed and (parsed < week_start or parsed > today):
                continue  # outside the week — drop before synth picks

        voices.append({
            "quote": quote,
            "speaker": speaker,
            "date_label": date_label,
            "url": html_lib.unescape(cite_m.group("url")),
            "src_title": _clean_text(cite_m.group("src_title")),
            "marker": _clean_text(cite_m.group("marker")),
        })
    return voices


def extract_strategy_cards(html: str) -> list[dict]:
    m = BACKDROP_BLOCK_RE.search(html)
    if not m:
        return []
    cards: list[dict] = []
    for card_m in STRATEGY_ARTICLE_RE.finditer(m.group(1)):
        cards.append({
            "title": _clean_text(card_m.group(1)),
            "status": _clean_text(card_m.group(2)),
            "blurb": _clean_text(card_m.group(3)),
        })
    return cards


# ── Per-day orchestrator ────────────────────────────────────────────────────

def extract_day(html: str, brief_date: str, edition: str,
                today: Optional[date] = None,
                week_start: Optional[date] = None) -> dict:
    return {
        "date": brief_date,
        "headline": extract_headline(html),
        "dek": extract_dek(html),
        "threads": extract_threads(html),
        "bullets": extract_bullets(html),
        "voices": extract_voices(html, today=today, week_start=week_start),
        "strategy_cards": extract_strategy_cards(html) if edition == "china" else [],
    }


def collect_week(edition: str, today: date) -> dict:
    edition_path = "usa" if edition == "us" else "china"
    files = _list_archive_files(edition_path)
    cutoff = today - timedelta(days=6)

    days: list[dict] = []
    for fname in files:
        try:
            brief_date = datetime.strptime(fname.removesuffix(".html"), "%Y-%m-%d").date()
        except ValueError:
            continue
        if brief_date < cutoff or brief_date > today:
            continue
        html = _read_archive_file(edition_path, fname)
        if not html:
            continue
        days.append(extract_day(html, brief_date.isoformat(), edition,
                                today=today, week_start=cutoff))

    days.sort(key=lambda d: d["date"], reverse=True)

    return {
        "edition": edition,
        "week_start": cutoff.isoformat(),
        "week_end": today.isoformat(),
        "days": days,
    }


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: weekly_aggregate.py us|china YYYY-MM-DD [output_path]", file=sys.stderr)
        return 2

    edition = sys.argv[1].lower()
    if edition not in ("us", "china"):
        print(f"edition must be 'us' or 'china', got {edition}", file=sys.stderr)
        return 2

    try:
        today = datetime.strptime(sys.argv[2], "%Y-%m-%d").date()
    except ValueError as e:
        print(f"bad date: {e}", file=sys.stderr)
        return 2

    doc = collect_week(edition, today)

    if len(sys.argv) >= 4:
        out_path = Path(sys.argv[3])
    else:
        RUN_DIR.mkdir(exist_ok=True)
        out_path = RUN_DIR / f"weekly_{edition}.json"
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"week {doc['week_start']} → {doc['week_end']} ({edition})")
    print(f"  {len(doc['days'])} day(s) of archived briefs found")
    for d in doc["days"]:
        n_b = len(d["bullets"])
        n_v = len(d["voices"])
        n_sc = len(d["strategy_cards"])
        dek_state = "dek" if d["dek"] else "no-dek"
        print(f"   {d['date']}: {n_b} bullets, {n_v} voices, sc={n_sc}, {dek_state}")
    print(f"  wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
