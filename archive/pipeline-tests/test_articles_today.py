"""
test_articles_today.py — Source freshness health check.

For each RSS/rss_translate source in sources.yaml, fetches the feed and checks
whether it has published anything in the last 48 hours (today or yesterday UTC).

Modes:
  --no-fetch   RSS only — titles, dates, URLs (~2-3 min for all sources)
  (default)    RSS + fetch full article text via extractor.py (~10-15 min)
  --limit N    Only test the first N sources (useful for quick sanity checks)

Output: printed to console AND written to output/freshness_report.txt
"""

import argparse
import io
import os
import sys
import time

# ── Windows UTF-8 encoding fix (must be before any print) ──────────────────
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import socket
import yaml
from datetime import datetime, timezone, timedelta

# ── Global socket timeout — prevents feedparser from hanging on slow feeds ──
socket.setdefaulttimeout(30)

# ── Path setup: allow running from repo root or from pipeline/ ──────────────
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from scraper.discovery import fetch_rss
from scraper.extractor import extract_article


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

RSS_DELAY      = 0.3   # seconds between RSS fetches (be polite)
TEXT_PREVIEW   = 400   # max chars of article text to display
MAX_PER_SOURCE = 2     # max fresh articles to show per source


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_sources() -> list[dict]:
    config_path = os.path.join(_THIS_DIR, "config", "sources.yaml")
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("sources", [])


def freshness_cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=48)


def fmt_date(dt: datetime | None) -> str:
    if dt is None:
        return "date unknown"
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def is_fresh(stub: dict, cutoff: datetime) -> bool:
    """
    Return True if the stub should be included as 'fresh'.
    Stubs with no publish_date are treated as potentially fresh (can't filter out).
    """
    pd = stub.get("publish_date")
    if pd is None:
        return True   # unknown date — include it
    return pd >= cutoff


# ─────────────────────────────────────────────────────────────────────────────
# Per-source check
# ─────────────────────────────────────────────────────────────────────────────

def check_source(
    source: dict,
    cutoff: datetime,
    fetch_text: bool,
) -> dict:
    """
    Fetch one RSS source and return a result dict:
      {
        name, tier, type, category,
        total_entries,
        fresh_stubs: [stub, ...],     # up to MAX_PER_SOURCE
        all_old: bool,                # entries found but all pre-cutoff
        fetch_error: str | None,
        articles: [                   # parallel to fresh_stubs[:MAX_PER_SOURCE]
          { stub, text, method, error }
        ]
      }
    """
    result = {
        "name":         source.get("name", "?"),
        "tier":         source.get("tier", 2),
        "type":         source.get("type", "rss"),
        "category":     source.get("category", "?"),
        "total_entries": 0,
        "fresh_stubs":  [],
        "all_old":      False,
        "fetch_error":  None,
        "articles":     [],
    }

    try:
        stubs = list(fetch_rss(source, delay=0))
    except Exception as e:
        result["fetch_error"] = str(e)
        return result

    result["total_entries"] = len(stubs)

    if not stubs:
        return result

    fresh = [s for s in stubs if is_fresh(s, cutoff)]

    if not fresh:
        result["all_old"] = True
        return result

    result["fresh_stubs"] = fresh[:MAX_PER_SOURCE]

    if not fetch_text:
        return result

    # Full mode: fetch article text for each fresh stub
    for stub in result["fresh_stubs"]:
        # If RSS already included full text (e.g. state.gov content:encoded), use it
        if stub.get("full_text"):
            result["articles"].append({
                "stub":   stub,
                "text":   stub["full_text"],
                "method": stub.get("extraction_method", "rss_content"),
                "error":  None,
            })
            continue

        url  = stub.get("url", "")
        extractor = stub.get("extractor", "trafilatura")
        try:
            text, method = extract_article(url, extractor)
        except Exception as e:
            result["articles"].append({
                "stub":   stub,
                "text":   None,
                "method": "exception",
                "error":  str(e),
            })
            continue

        result["articles"].append({
            "stub":   stub,
            "text":   text,
            "method": method,
            "error":  None if text else f"extraction failed ({method})",
        })

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Report rendering
# ─────────────────────────────────────────────────────────────────────────────

def render_source_block(result: dict, fetch_text: bool) -> list[str]:
    lines = []
    header = (
        f"[{result['name']}]  "
        f"tier={result['tier']}  "
        f"{result['type']}  "
        f"{result['category']}"
    )
    lines.append(header)

    if result["fetch_error"]:
        lines.append(f"  ✗ fetch failed: {result['fetch_error']}")
        return lines

    total = result["total_entries"]
    fresh = result["fresh_stubs"]
    fresh_count = len(fresh)

    if total == 0:
        lines.append("  ✗ no entries in feed")
    elif result["all_old"]:
        lines.append(f"  ~ {total} entries found, all older than 48h")
    else:
        lines.append(f"  ✓ {fresh_count} fresh entries today/yesterday out of {total} total")

        articles = result["articles"]
        for i, stub in enumerate(fresh):
            date_str = fmt_date(stub.get("publish_date"))
            title    = stub.get("title", "(no title)")
            url      = stub.get("url", "")
            lines.append(f"  → [{date_str}] {title}")
            lines.append(f"    URL: {url}")

            if fetch_text:
                if i < len(articles):
                    art = articles[i]
                    if art["text"]:
                        preview = art["text"][:TEXT_PREVIEW].replace("\n", " ")
                        chars   = len(art["text"])
                        lines.append(
                            f"    Text ({chars} chars, {art['method']}): {preview}..."
                        )
                    else:
                        lines.append(f"    [extraction failed: {art['method']}]")
                else:
                    lines.append("    [text not fetched]")

    return lines


def render_report(
    results: list[dict],
    skipped: list[str],
    fetch_text: bool,
    elapsed: float,
) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("BRIEFER — SOURCE FRESHNESS REPORT")
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    mode = "full (RSS + article text)" if fetch_text else "fast (RSS only)"
    lines.append(f"Mode: {mode}  |  Elapsed: {elapsed:.0f}s")
    lines.append("=" * 70)
    lines.append("")

    for result in results:
        for line in render_source_block(result, fetch_text):
            lines.append(line)
        lines.append("")

    # ── Summary table ──────────────────────────────────────────────────────
    with_fresh  = [r for r in results if r["fresh_stubs"]]
    all_old     = [r for r in results if r["all_old"] and not r["fresh_stubs"]]
    no_entries  = [r for r in results if not r["all_old"] and not r["fresh_stubs"]]
    total       = len(results)
    total_fresh = sum(len(r["fresh_stubs"]) for r in results)

    # Text extraction stats (full mode only)
    if fetch_text:
        all_arts    = [a for r in results for a in r["articles"]]
        text_ok     = sum(1 for a in all_arts if a["text"])
        text_fail   = sum(1 for a in all_arts if not a["text"])

    lines.append("")
    lines.append("FRESHNESS SUMMARY")
    lines.append("═" * 50)
    lines.append(f"Sources with fresh content today/yesterday:  {len(with_fresh):>3} / {total}")
    lines.append(f"Sources with entries but all old:            {len(all_old):>3} / {total}")
    lines.append(f"Sources with no entries / fetch failed:      {len(no_entries):>3} / {total}")
    lines.append(f"Total fresh articles found:                  {total_fresh:>3}")
    if skipped:
        lines.append(f"Sources skipped (web_scrape/playwright):     {len(skipped):>3}")
    lines.append("─" * 50)
    if fetch_text:
        lines.append(f"Text extraction:  {text_ok} succeeded, {text_fail} failed")
    lines.append("")

    if skipped:
        lines.append("Skipped sources (require Playwright):")
        for name in skipped:
            lines.append(f"  • {name}")
        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Check which RSS sources have fresh content today/yesterday."
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Fast mode: RSS only, skip article text extraction.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Only process the first N sources (for testing).",
    )
    args = parser.parse_args()
    fetch_text = not args.no_fetch

    sources  = load_sources()
    cutoff   = freshness_cutoff()
    skipped  = []
    results  = []

    # Filter to active sources
    active_sources = [s for s in sources if s.get("active", True)]

    if args.limit:
        active_sources = active_sources[: args.limit]

    total_to_check = len(active_sources)
    rss_types      = {"rss", "rss_translate", "google_news"}

    print(f"Briefer source freshness check — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Cutoff: {fmt_date(cutoff)}")
    print(f"Mode: {'RSS only (--no-fetch)' if not fetch_text else 'RSS + article text'}")
    print(f"Sources to check: {sum(1 for s in active_sources if s.get('type','rss') in rss_types)} RSS")
    print()

    start = time.time()

    for i, source in enumerate(active_sources, 1):
        src_type = source.get("type", "rss")
        name     = source.get("name", "?")

        if src_type not in rss_types:
            skipped.append(name)
            print(f"[{i}/{total_to_check}] SKIP  {name}  ({src_type})")
            continue

        print(f"[{i}/{total_to_check}] Checking: {name} ...", end=" ", flush=True)

        result = check_source(source, cutoff, fetch_text)
        results.append(result)

        # Quick status to console
        if result["fetch_error"]:
            print(f"ERROR: {result['fetch_error'][:80]}")
        elif result["fresh_stubs"]:
            print(f"{len(result['fresh_stubs'])} fresh / {result['total_entries']} total")
        elif result["all_old"]:
            print(f"all old ({result['total_entries']} entries)")
        else:
            print("no entries")

        time.sleep(RSS_DELAY)

    elapsed = time.time() - start
    report  = render_report(results, skipped, fetch_text, elapsed)

    # Write to file
    os.makedirs(os.path.join(_THIS_DIR, "output"), exist_ok=True)
    out_path = os.path.join(_THIS_DIR, "output", "freshness_report.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)

    # Print to console
    print()
    print(report)
    print(f"Report written to: {out_path}")


if __name__ == "__main__":
    main()
