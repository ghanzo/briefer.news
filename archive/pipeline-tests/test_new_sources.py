"""
test_new_sources.py — Probe RSS feeds and data APIs for gaps #2-6.

Covers:
  #2 Finance     — SEC, CFTC, FDIC, BLS news releases
  #3 Technology  — Commerce Dept, NTIA, NSA, AI Safety Institute
  #4 Health      — FDA (press releases + drug approvals + food safety)
  #5 Econ data   — FRED API, BLS API, BEA API, EIA API, Treasury yields
  #6 Energy reg  — FERC

For RSS/feeds: checks reachability + entry count + latest date.
For data APIs:  checks endpoint accessibility + sample payload shape.
"""

import json
import logging
import sys
import time

import feedparser
import httpx

logging.basicConfig(
    level=logging.WARNING,   # suppress httpx noise
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("test_new_sources")

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BrieferBot/1.0)"}

# ─────────────────────────────────────────────────────────────────────────────
# RSS / Feed candidates
# ─────────────────────────────────────────────────────────────────────────────

RSS_CANDIDATES = [
    # ── Finance ──────────────────────────────────────────────────────────────
    {"group": "Finance",    "name": "SEC — Press Releases",
     "url": "https://www.sec.gov/rss/news/pressreleases.rss"},
    {"group": "Finance",    "name": "SEC — Enforcement Actions (Lit Releases)",
     "url": "https://www.sec.gov/rss/litigation/litreleases.xml"},
    {"group": "Finance",    "name": "SEC — Trading Suspensions",
     "url": "https://www.sec.gov/rss/litigation/suspensions.xml"},
    {"group": "Finance",    "name": "CFTC — Press Releases",
     "url": "https://www.cftc.gov/rss/pressreleases"},
    {"group": "Finance",    "name": "FDIC — Press Releases",
     "url": "https://www.fdic.gov/news/press-releases/rss.xml"},
    {"group": "Finance",    "name": "OCC — News Releases",
     "url": "https://www.occ.gov/news-issuances/news-releases/rss.xml"},
    {"group": "Finance",    "name": "BLS — News Releases",
     "url": "https://www.bls.gov/feed/news_release.rss"},

    # ── Technology ────────────────────────────────────────────────────────────
    {"group": "Technology", "name": "Commerce Dept — News",
     "url": "https://www.commerce.gov/feeds/news"},
    {"group": "Technology", "name": "NTIA — News",
     "url": "https://www.ntia.gov/rss.xml"},
    {"group": "Technology", "name": "NTIA — Blog",
     "url": "https://www.ntia.gov/blog/rss.xml"},
    {"group": "Technology", "name": "NSA — Cybersecurity Advisories",
     "url": "https://www.nsa.gov/rss/press_releases/"},
    {"group": "Technology", "name": "CISA — Known Exploited Vulnerabilities",
     "url": "https://www.cisa.gov/known-exploited-vulnerabilities.json"},  # JSON, not RSS
    {"group": "Technology", "name": "AI Safety Institute (NIST) — News",
     "url": "https://www.nist.gov/artificial-intelligence/rss.xml"},
    {"group": "Technology", "name": "USPTO — Patents RSS",
     "url": "https://www.uspto.gov/rss/NewPat.xml"},

    # ── Health ────────────────────────────────────────────────────────────────
    {"group": "Health",     "name": "FDA — Press Announcements",
     "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-announcements/rss.xml"},
    {"group": "Health",     "name": "FDA — Drug Approvals",
     "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/fda-drug-approvals/rss.xml"},
    {"group": "Health",     "name": "FDA — Food Safety Recalls",
     "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/recalls-market-withdrawals-safety-alerts/rss.xml"},
    {"group": "Health",     "name": "FDA — Medical Devices",
     "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/medical-devices/rss.xml"},
    {"group": "Health",     "name": "HHS — News",
     "url": "https://www.hhs.gov/news/index.html"},

    # ── Energy Regulation ─────────────────────────────────────────────────────
    {"group": "Energy",     "name": "FERC — News Releases",
     "url": "https://www.ferc.gov/news-events/news/rss"},
    {"group": "Energy",     "name": "FERC — Orders & Notices",
     "url": "https://www.ferc.gov/news-events/news/orders-rss"},
    {"group": "Energy",     "name": "FERC — Federal Register",
     "url": "https://www.federalregister.gov/articles/search.rss?conditions%5Bagencies%5D%5B%5D=federal-energy-regulatory-commission&conditions%5Btype%5D%5B%5D=RULE&conditions%5Btype%5D%5B%5D=PRORULE&conditions%5Btype%5D%5B%5D=NOTICE"},
]

# ─────────────────────────────────────────────────────────────────────────────
# Data API candidates
# ─────────────────────────────────────────────────────────────────────────────

API_CANDIDATES = [
    # ── FRED (St. Louis Fed) — no key needed for public series ───────────────
    {"group": "Econ Data",  "name": "FRED API — Federal Funds Rate",
     "url": "https://api.stlouisfed.org/fred/series/observations?series_id=FEDFUNDS&sort_order=desc&limit=3&file_type=json&api_key=annualreviews",
     "note": "FEDFUNDS — benchmark rate. api_key=annualreviews is public demo key"},
    {"group": "Econ Data",  "name": "FRED API — CPI (inflation)",
     "url": "https://api.stlouisfed.org/fred/series/observations?series_id=CPIAUCSL&sort_order=desc&limit=3&file_type=json&api_key=annualreviews",
     "note": "CPIAUCSL — Consumer Price Index"},
    {"group": "Econ Data",  "name": "FRED API — 10Y-2Y Yield Curve Spread",
     "url": "https://api.stlouisfed.org/fred/series/observations?series_id=T10Y2Y&sort_order=desc&limit=3&file_type=json&api_key=annualreviews",
     "note": "T10Y2Y — recession early warning signal"},
    {"group": "Econ Data",  "name": "FRED API — Unemployment Rate",
     "url": "https://api.stlouisfed.org/fred/series/observations?series_id=UNRATE&sort_order=desc&limit=3&file_type=json&api_key=annualreviews",
     "note": "UNRATE"},

    # ── BLS Data API (no key needed for basic access) ────────────────────────
    {"group": "Econ Data",  "name": "BLS API — CPI series",
     "url": "https://api.bls.gov/publicAPI/v1/timeseries/data/CUSR0000SA0",
     "note": "BLS v1 (no key). CPI-U all items. v2 needs free registration key for more series"},

    # ── BEA API (key required — free registration at bea.gov) ────────────────
    {"group": "Econ Data",  "name": "BEA API — GDP (key required)",
     "url": "https://apps.bea.gov/api/data/?UserID=DEMO_KEY&method=GetData&DataSetName=NIPA&TableName=T10101&Frequency=Q&Year=2025&ResultFormat=JSON",
     "note": "Needs free BEA API key from bea.gov/tools/api-key. DEMO_KEY may work"},

    # ── Treasury ─────────────────────────────────────────────────────────────
    {"group": "Econ Data",  "name": "Treasury — Yield Curve (daily rates)",
     "url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value_month=202502",
     "note": "XML feed of daily Treasury yield curve rates"},

    # ── EIA Data API (key required — free) ───────────────────────────────────
    {"group": "Econ Data",  "name": "EIA API — WTI Crude Oil Price",
     "url": "https://api.eia.gov/v2/petroleum/pri/spt/data/?api_key=DEMO&frequency=daily&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&length=3",
     "note": "Needs free EIA API key from eia.gov/opendata. DEMO key may not work"},

    # ── SEC EDGAR ─────────────────────────────────────────────────────────────
    {"group": "Finance",    "name": "SEC EDGAR — Recent filings feed",
     "url": "https://efts.sec.gov/LATEST/search-index?q=%22form+type%22&dateRange=custom&startdt=2026-02-21&enddt=2026-02-22&forms=8-K",
     "note": "8-K current reports (material events). No key needed."},
    {"group": "Finance",    "name": "SEC EDGAR — Full-text search API",
     "url": "https://efts.sec.gov/LATEST/search-index?q=%22executive+order%22&forms=8-K&dateRange=custom&startdt=2026-02-20&enddt=2026-02-22",
     "note": "EDGAR full-text search — queryable"},
]


# ─────────────────────────────────────────────────────────────────────────────
# Probe functions
# ─────────────────────────────────────────────────────────────────────────────

def probe_rss(candidate: dict) -> dict:
    url = candidate["url"]
    r = {"name": candidate["name"], "group": candidate["group"],
         "url": url, "ok": False, "entries": 0, "latest": None,
         "sample": None, "error": None}
    try:
        resp = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=12)
        if resp.status_code >= 400:
            r["error"] = f"HTTP {resp.status_code}"
            return r
        feed = feedparser.parse(resp.content)
        if not feed.entries:
            r["error"] = f"0 entries (bozo={feed.bozo})"
            return r
        r["ok"]      = True
        r["entries"] = len(feed.entries)
        entry = feed.entries[0]
        raw_date = entry.get("published") or entry.get("updated") or ""
        if raw_date:
            try:
                from dateutil import parser as dp
                r["latest"] = dp.parse(raw_date).strftime("%Y-%m-%d")
            except Exception:
                r["latest"] = raw_date[:10]
        r["sample"] = (entry.get("title") or "")[:80]
    except Exception as e:
        r["error"] = str(e)[:100]
    return r


def probe_api(candidate: dict) -> dict:
    url = candidate["url"]
    r = {"name": candidate["name"], "group": candidate["group"],
         "url": url, "note": candidate.get("note", ""),
         "ok": False, "shape": None, "sample": None, "error": None}
    try:
        resp = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=12)
        r["status"] = resp.status_code
        if resp.status_code >= 400:
            r["error"] = f"HTTP {resp.status_code}"
            # Show body snippet for API errors (often informative)
            r["body_snippet"] = resp.text[:150]
            return r
        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            try:
                data = resp.json()
                # Describe shape
                if isinstance(data, dict):
                    r["shape"] = f"dict keys: {list(data.keys())[:6]}"
                elif isinstance(data, list):
                    r["shape"] = f"list[{len(data)}]"
                r["sample"] = str(data)[:200]
                r["ok"] = True
            except Exception:
                r["shape"] = "json parse failed"
                r["sample"] = resp.text[:150]
        elif "xml" in content_type or resp.text.strip().startswith("<"):
            r["shape"] = "XML"
            r["sample"] = resp.text[:200]
            r["ok"] = True
        else:
            r["shape"] = f"content-type: {content_type}"
            r["sample"] = resp.text[:150]
            r["ok"] = resp.status_code < 400
    except Exception as e:
        r["error"] = str(e)[:100]
    return r


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run():
    W = 72
    print(f"\n{'═' * W}")
    print("  NEW SOURCE PROBE — Finance / Tech / Health / Econ Data / Energy Reg")
    print(f"{'═' * W}\n")

    # ── RSS ──────────────────────────────────────────────────────────────────
    print("  Probing RSS feeds…")
    rss_results = []
    for c in RSS_CANDIDATES:
        print(f"    {c['name']} …", flush=True)
        rss_results.append(probe_rss(c))
        time.sleep(0.3)

    # ── APIs ─────────────────────────────────────────────────────────────────
    print("\n  Probing data APIs…")
    api_results = []
    for c in API_CANDIDATES:
        print(f"    {c['name']} …", flush=True)
        api_results.append(probe_api(c))
        time.sleep(0.3)

    # ── Print RSS results by group ────────────────────────────────────────────
    print(f"\n{'═' * W}")
    print("  RSS / FEED RESULTS")
    for group in ["Finance", "Technology", "Health", "Energy"]:
        items = [r for r in rss_results if r["group"] == group]
        print(f"\n  {'─' * 60}")
        print(f"  {group.upper()}")
        print(f"  {'─' * 60}")
        for r in items:
            if r["ok"]:
                print(f"  ✓  {r['name']}")
                print(f"       entries={r['entries']}  latest={r['latest']}")
                print(f"       sample : {r['sample']!r}")
            else:
                print(f"  ✗  {r['name']}")
                print(f"       error  : {r['error']}")

    # ── Print API results ─────────────────────────────────────────────────────
    print(f"\n{'═' * W}")
    print("  DATA API RESULTS")
    for group in ["Econ Data", "Finance"]:
        items = [r for r in api_results if r["group"] == group]
        if not items:
            continue
        print(f"\n  {'─' * 60}")
        print(f"  {group.upper()}")
        print(f"  {'─' * 60}")
        for r in items:
            status_str = f"  ✓" if r["ok"] else f"  ✗"
            print(f"{status_str}  {r['name']}")
            if r.get("note"):
                print(f"       note   : {r['note']}")
            if r["ok"]:
                print(f"       shape  : {r['shape']}")
                print(f"       sample : {r['sample']!r:.120}")
            else:
                print(f"       error  : {r.get('error') or r.get('body_snippet', '')}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'═' * W}")
    rss_ok  = [r for r in rss_results  if r["ok"]]
    api_ok  = [r for r in api_results  if r["ok"]]
    rss_bad = [r for r in rss_results  if not r["ok"]]
    api_bad = [r for r in api_results  if not r["ok"]]

    print(f"\n  RSS:  {len(rss_ok)}/{len(rss_results)} working")
    for r in rss_ok:
        print(f"    ✓ [{r['group']}] {r['name']}  ({r['entries']} entries, latest {r['latest']})")

    print(f"\n  APIs: {len(api_ok)}/{len(api_results)} accessible")
    for r in api_ok:
        print(f"    ✓ [{r['group']}] {r['name']}")

    if rss_bad or api_bad:
        print(f"\n  Failed:")
        for r in rss_bad + api_bad:
            print(f"    ✗ [{r['group']}] {r['name']}  — {r.get('error','?')}")

    print(f"\n{'═' * W}\n")


if __name__ == "__main__":
    run()
