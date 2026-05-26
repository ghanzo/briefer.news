"""
test_blocked_alts.py — Probe alternative data sources for FTC, FBI, FCC.

Strategy:
  FTC  — Federal Register agency RSS + probe any FTC RSS endpoints
  FBI  — DOJ press releases already covered; probe FBI Vault FOIA RSS + Fed Register
  FCC  — Federal Register agency RSS + probe FCC daily digest

For each candidate, checks whether it's a valid feed with recent entries.
"""

import logging
import sys
import time
from datetime import datetime, timezone

import feedparser
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("test_blocked_alts")

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BrieferBot/1.0)"}

CANDIDATES = [
    # ── FTC ──────────────────────────────────────────────────────────────────
    {
        "name":     "FTC — Federal Register (all actions)",
        "url":      "https://www.federalregister.gov/articles/search.rss?conditions%5Bagencies%5D%5B%5D=federal-trade-commission",
        "group":    "FTC",
    },
    {
        "name":     "FTC — Federal Register (rules + notices only)",
        "url":      "https://www.federalregister.gov/articles/search.rss?conditions%5Bagencies%5D%5B%5D=federal-trade-commission&conditions%5Btype%5D%5B%5D=RULE&conditions%5Btype%5D%5B%5D=PRORULE&conditions%5Btype%5D%5B%5D=NOTICE",
        "group":    "FTC",
    },
    {
        "name":     "FTC — RSS feed (press-release.xml)",
        "url":      "https://www.ftc.gov/feeds/press-release.xml",
        "group":    "FTC",
    },
    {
        "name":     "FTC — RSS feed (news.xml)",
        "url":      "https://www.ftc.gov/feeds/news.xml",
        "group":    "FTC",
    },
    {
        "name":     "FTC — RSS feed (atom)",
        "url":      "https://www.ftc.gov/rss.xml",
        "group":    "FTC",
    },
    # ── FBI ──────────────────────────────────────────────────────────────────
    {
        "name":     "FBI — Vault FOIA releases RSS",
        "url":      "https://vault.fbi.gov/fdps.rss",
        "group":    "FBI",
    },
    {
        "name":     "DOJ — Press Releases (covers FBI actions)",
        "url":      "https://www.justice.gov/rss/press-releases.xml",
        "group":    "FBI",
    },
    {
        "name":     "DOJ — FBI-tagged press releases",
        "url":      "https://www.justice.gov/rss/component/fbi.xml",
        "group":    "FBI",
    },
    # ── FCC ──────────────────────────────────────────────────────────────────
    {
        "name":     "FCC — Federal Register (all actions)",
        "url":      "https://www.federalregister.gov/articles/search.rss?conditions%5Bagencies%5D%5B%5D=federal-communications-commission",
        "group":    "FCC",
    },
    {
        "name":     "FCC — Federal Register (rules + notices)",
        "url":      "https://www.federalregister.gov/articles/search.rss?conditions%5Bagencies%5D%5B%5D=federal-communications-commission&conditions%5Btype%5D%5B%5D=RULE&conditions%5Btype%5D%5B%5D=PRORULE&conditions%5Btype%5D%5B%5D=NOTICE",
        "group":    "FCC",
    },
    {
        "name":     "FCC — Daily Digest RSS",
        "url":      "https://www.fcc.gov/news-events/rss-feeds/daily-digest",
        "group":    "FCC",
    },
    {
        "name":     "FCC — RSS (news.xml)",
        "url":      "https://www.fcc.gov/rss.xml",
        "group":    "FCC",
    },
]


def probe_feed(candidate: dict) -> dict:
    url  = candidate["url"]
    name = candidate["name"]
    result = {
        "name":         name,
        "url":          url,
        "group":        candidate["group"],
        "ok":           False,
        "entry_count":  0,
        "latest_date":  None,
        "sample_title": None,
        "sample_url":   None,
        "error":        None,
    }

    # Pre-fetch with httpx so we control the timeout; feedparser has no timeout
    try:
        resp = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=12)
        if resp.status_code >= 400:
            result["error"] = f"HTTP {resp.status_code}"
            return result
        raw_content = resp.content
    except Exception as e:
        result["error"] = f"fetch: {str(e)[:80]}"
        return result

    try:
        feed = feedparser.parse(raw_content)

        if not feed.entries:
            if feed.bozo:
                result["error"] = f"bozo: {str(feed.bozo_exception)[:80]}"
            else:
                result["error"] = "empty feed (0 entries)"
            return result

        result["ok"]          = True
        result["entry_count"] = len(feed.entries)

        entry = feed.entries[0]
        raw_date = entry.get("published") or entry.get("updated") or entry.get("dc_date")
        if raw_date:
            try:
                from dateutil import parser as dp
                dt = dp.parse(raw_date)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                result["latest_date"] = dt.strftime("%Y-%m-%d")
            except Exception:
                result["latest_date"] = raw_date[:10]

        result["sample_title"] = (entry.get("title") or "")[:80]
        result["sample_url"]   = entry.get("link", "")[:100]

    except Exception as e:
        result["error"] = str(e)[:100]

    return result


def run() -> None:
    print("\n" + "═" * 72)
    print("  ALTERNATIVE SOURCE PROBE — FTC / FBI / FCC")
    print("═" * 72 + "\n")

    results = []
    for c in CANDIDATES:
        print(f"  Probing: {c['name']} …", flush=True)
        r = probe_feed(c)
        results.append(r)
        time.sleep(0.3)

    # Print by group
    for group in ["FTC", "FBI", "FCC"]:
        group_results = [r for r in results if r["group"] == group]
        print(f"\n{'─' * 72}")
        print(f"  {group}")
        print(f"{'─' * 72}")
        for r in group_results:
            if r["ok"]:
                print(f"\n  ✓  {r['name']}")
                print(f"       entries    : {r['entry_count']}")
                print(f"       latest     : {r['latest_date']}")
                print(f"       sample     : {r['sample_title']!r}")
                print(f"       url        : {r['sample_url']}")
            else:
                print(f"\n  ✗  {r['name']}")
                print(f"       error : {r['error']}")

    print(f"\n{'═' * 72}")
    working = [r for r in results if r["ok"]]
    print(f"\n  SUMMARY: {len(working)}/{len(results)} feeds working\n")
    for r in working:
        print(f"  [{r['group']}] {r['name']}")
        print(f"         {r['entry_count']} entries, latest {r['latest_date']}")
    print()


if __name__ == "__main__":
    run()
