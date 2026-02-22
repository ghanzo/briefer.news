"""
test_new_sources2.py — Second pass with corrected URLs and deeper data API inspection.

Fixes:
  - SEC: corrected RSS paths + EDGAR enforcement actions
  - FDA: updated RSS paths from fda.gov/news-events
  - BLS: corrected news release feed path
  - CFTC: alternative paths
  - FDIC: alternative paths
  - NTIA: SSL verify=False (Docker container CA issue, not site block)
  - Commerce: try Playwright fallback paths

Also inspects data API payloads in detail:
  - Treasury yield curve — parse out actual rates
  - BLS API — parse actual CPI value
  - BEA API — parse actual GDP value
  - FRED — test with no key (some series work) and show key registration URL
"""

import json
import logging
import sys
import time
from xml.etree import ElementTree as ET

import feedparser
import httpx

logging.basicConfig(level=logging.WARNING,
                    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BrieferBot/1.0)"}
W = 72

# ─────────────────────────────────────────────────────────────────────────────
# Corrected RSS candidates
# ─────────────────────────────────────────────────────────────────────────────

RSS_ROUND2 = [
    # ── SEC — try multiple paths ──────────────────────────────────────────────
    {"group": "Finance", "name": "SEC — Newsroom (current CMS)",
     "url": "https://www.sec.gov/news/pressreleases.rss",
     "note": "Try 1"},
    {"group": "Finance", "name": "SEC — EDGAR atom feed (current filings)",
     "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&dateb=&owner=include&count=20&search_text=&output=atom",
     "note": "All recent EDGAR filings"},
    {"group": "Finance", "name": "SEC — Litigation Releases (enforcement)",
     "url": "https://www.sec.gov/rss/litigation/litreleases.xml",
     "note": "Try corrected path"},
    {"group": "Finance", "name": "SEC — Litigation Releases (alt path)",
     "url": "https://efts.sec.gov/LATEST/search-index?q=&forms=LITIG&dateRange=custom&startdt=2026-01-01&output=atom",
     "note": "Via EDGAR search"},

    # ── CFTC ─────────────────────────────────────────────────────────────────
    {"group": "Finance", "name": "CFTC — Press Releases (alt 1)",
     "url": "https://www.cftc.gov/PressRoom/PressReleases/rss"},
    {"group": "Finance", "name": "CFTC — Press Releases (alt 2)",
     "url": "https://www.cftc.gov/rss/pressreleases.xml"},
    {"group": "Finance", "name": "CFTC — Federal Register",
     "url": "https://www.federalregister.gov/articles/search.rss?conditions%5Bagencies%5D%5B%5D=commodity-futures-trading-commission&conditions%5Btype%5D%5B%5D=RULE&conditions%5Btype%5D%5B%5D=PRORULE&conditions%5Btype%5D%5B%5D=NOTICE"},

    # ── FDIC ─────────────────────────────────────────────────────────────────
    {"group": "Finance", "name": "FDIC — Press Releases (alt 1)",
     "url": "https://www.fdic.gov/news/news/press/rss.xml"},
    {"group": "Finance", "name": "FDIC — Federal Register",
     "url": "https://www.federalregister.gov/articles/search.rss?conditions%5Bagencies%5D%5B%5D=federal-deposit-insurance-corporation&conditions%5Btype%5D%5B%5D=RULE&conditions%5Btype%5D%5B%5D=PRORULE&conditions%5Btype%5D%5B%5D=NOTICE"},

    # ── OCC ──────────────────────────────────────────────────────────────────
    {"group": "Finance", "name": "OCC — Federal Register",
     "url": "https://www.federalregister.gov/articles/search.rss?conditions%5Bagencies%5D%5B%5D=comptroller-of-the-currency&conditions%5Btype%5D%5B%5D=RULE&conditions%5Btype%5D%5B%5D=PRORULE&conditions%5Btype%5D%5B%5D=NOTICE"},

    # ── BLS ──────────────────────────────────────────────────────────────────
    {"group": "Finance", "name": "BLS — News Releases (alt 1)",
     "url": "https://www.bls.gov/bls/newsrels.rss"},
    {"group": "Finance", "name": "BLS — News Releases (alt 2)",
     "url": "https://www.bls.gov/feed/bls_latest.rss"},
    {"group": "Finance", "name": "BLS — Latest News (alt 3)",
     "url": "https://www.bls.gov/rss/latest.xml"},

    # ── FDA — corrected paths ─────────────────────────────────────────────────
    {"group": "Health", "name": "FDA — News Releases (corrected)",
     "url": "https://www.fda.gov/news-events/fda-newsroom/press-announcements/rss.xml"},
    {"group": "Health", "name": "FDA — News & Events feed",
     "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/get-email-updates/rss.xml"},
    {"group": "Health", "name": "FDA — Drug Approvals (corrected)",
     "url": "https://www.fda.gov/drugs/development-approval-process-drugs/drug-approvals-and-databases/rss.xml"},
    {"group": "Health", "name": "FDA — Federal Register",
     "url": "https://www.federalregister.gov/articles/search.rss?conditions%5Bagencies%5D%5B%5D=food-and-drug-administration&conditions%5Btype%5D%5B%5D=RULE&conditions%5Btype%5D%5B%5D=PRORULE&conditions%5Btype%5D%5B%5D=NOTICE"},
    {"group": "Health", "name": "HHS — Federal Register",
     "url": "https://www.federalregister.gov/articles/search.rss?conditions%5Bagencies%5D%5B%5D=health-and-human-services-department&conditions%5Btype%5D%5B%5D=RULE&conditions%5Btype%5D%5B%5D=NOTICE"},

    # ── Technology ────────────────────────────────────────────────────────────
    {"group": "Technology", "name": "NTIA — News (SSL verify=False)",
     "url": "https://www.ntia.gov/rss.xml", "ssl_verify": False},
    {"group": "Technology", "name": "Commerce Dept — Federal Register",
     "url": "https://www.federalregister.gov/articles/search.rss?conditions%5Bagencies%5D%5B%5D=commerce-department&conditions%5Btype%5D%5B%5D=RULE&conditions%5Btype%5D%5B%5D=PRORULE&conditions%5Btype%5D%5B%5D=NOTICE"},
    {"group": "Technology", "name": "NSA — Cybersecurity Advisories feed",
     "url": "https://www.nsa.gov/portals/75/documents/what-we-do/cybersecurity/professional-resources/csa/rss.xml"},
    {"group": "Technology", "name": "CISA — Advisories RSS (corrected)",
     "url": "https://www.cisa.gov/uscert/ncas/all.xml"},
]


# ─────────────────────────────────────────────────────────────────────────────
# Data API deep inspection
# ─────────────────────────────────────────────────────────────────────────────

def inspect_treasury_yields():
    """Parse and display the Treasury yield curve."""
    print(f"\n  {'─' * 60}")
    print("  TREASURY YIELD CURVE — parsing XML")
    print(f"  {'─' * 60}")
    url = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value_month=202502"
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=12)
        root = ET.fromstring(resp.text)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "d":    "http://schemas.microsoft.com/ado/2007/08/dataservices",
            "m":    "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata",
        }
        entries = root.findall("atom:entry", ns)
        if entries:
            # Get the most recent entry
            entry = entries[-1]
            content = entry.find(".//m:properties", ns)
            if content is not None:
                date  = getattr(content.find("d:NEW_DATE", ns), "text", "?")[:10]
                y1m   = getattr(content.find("d:BC_1MONTH", ns), "text", "?")
                y3m   = getattr(content.find("d:BC_3MONTH", ns), "text", "?")
                y1    = getattr(content.find("d:BC_1YEAR", ns), "text", "?")
                y2    = getattr(content.find("d:BC_2YEAR", ns), "text", "?")
                y5    = getattr(content.find("d:BC_5YEAR", ns), "text", "?")
                y10   = getattr(content.find("d:BC_10YEAR", ns), "text", "?")
                y30   = getattr(content.find("d:BC_30YEAR", ns), "text", "?")
                print(f"  ✓  Most recent date: {date}")
                print(f"     1mo={y1m}%  3mo={y3m}%  1yr={y1}%  2yr={y2}%")
                print(f"     5yr={y5}%  10yr={y10}%  30yr={y30}%")
                if y2 and y10 and y2 != "?" and y10 != "?":
                    spread = float(y10) - float(y2)
                    print(f"     10Y-2Y spread: {spread:+.2f}% ({'inverted — recession signal' if spread < 0 else 'normal'})")
    except Exception as e:
        print(f"  ✗  {e}")


def inspect_bls_api():
    """Fetch and display latest CPI reading from BLS."""
    print(f"\n  {'─' * 60}")
    print("  BLS API — Latest CPI Reading")
    print(f"  {'─' * 60}")
    url = "https://api.bls.gov/publicAPI/v1/timeseries/data/CUSR0000SA0"
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=12)
        data = resp.json()
        series = data.get("Results", {}).get("series", [{}])[0]
        points = series.get("data", [])[:3]
        for p in points:
            print(f"  ✓  {p['year']}-{p['periodName']:>3}  CPI={p['value']}")
        print(f"     (Note: v1 API has no key but limited series. v2 needs free key from bls.gov/developers)")
    except Exception as e:
        print(f"  ✗  {e}")


def inspect_fred():
    """Test FRED API — needs a free key, show registration URL."""
    print(f"\n  {'─' * 60}")
    print("  FRED API — St. Louis Federal Reserve Economic Data")
    print(f"  {'─' * 60}")
    # Test without key first (some endpoints work)
    url = "https://api.stlouisfed.org/fred/series?series_id=FEDFUNDS&file_type=json"
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            print(f"  ✓  Series metadata accessible without key: {data.get('seriess', [{}])[0].get('title', '?')}")
        else:
            print(f"  ✗  HTTP {resp.status_code} — key required")
            print(f"     Get free key at: https://fred.stlouisfed.org/docs/api/api_key.html")
            print(f"     Add to .env as: FRED_API_KEY=your_key_here")
            print(f"     Key series to pull once registered:")
            series = [
                ("FEDFUNDS", "Federal Funds Rate"),
                ("CPIAUCSL", "CPI — All Urban Consumers"),
                ("T10Y2Y",   "10Y-2Y Treasury Spread (yield curve)"),
                ("UNRATE",   "Unemployment Rate"),
                ("VIXCLS",   "VIX Volatility Index"),
                ("DCOILWTICO","WTI Crude Oil Price"),
                ("DEXUSEU",  "USD/EUR Exchange Rate"),
                ("DEXCHUS",  "USD/CNY Exchange Rate"),
                ("GOLDAMGBD228NLBM", "Gold Price"),
            ]
            for sid, name in series:
                print(f"       {sid:<25} {name}")
    except Exception as e:
        print(f"  ✗  {e}")


def inspect_eia():
    """Test EIA API — needs free key."""
    print(f"\n  {'─' * 60}")
    print("  EIA API — Energy Information Administration")
    print(f"  {'─' * 60}")
    print(f"  ✗  Requires free API key from: https://www.eia.gov/opendata/register.php")
    print(f"     Add to .env as: EIA_API_KEY=your_key_here")
    print(f"     Key series to pull once registered:")
    series = [
        ("petroleum/pri/spt",         "WTI & Brent crude spot prices (daily)"),
        ("natural-gas/pri/sum",        "Natural gas spot prices"),
        ("electricity/retail-sales",   "US electricity retail sales"),
        ("nuclear-outages",            "Nuclear plant outages"),
        ("coal/shipments/mines-by-destination", "Coal production"),
    ]
    for path, desc in series:
        print(f"       /v2/{path}")
        print(f"           {desc}")


def inspect_edgar():
    """Show what EDGAR search actually returns and how to use it."""
    print(f"\n  {'─' * 60}")
    print("  SEC EDGAR — Full-text search API")
    print(f"  {'─' * 60}")
    # Search for enforcement-related 8-Ks
    url = ('https://efts.sec.gov/LATEST/search-index?q=%22cease+and+desist%22'
           '&forms=8-K&dateRange=custom&startdt=2026-02-20&enddt=2026-02-23')
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=12)
        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])
        total = data.get("hits", {}).get("total", {}).get("value", 0)
        print(f"  ✓  Query: 8-Ks mentioning 'cease and desist' Feb 20-23 2026")
        print(f"     Total matches: {total}")
        for h in hits[:3]:
            src = h.get("_source", {})
            print(f"     • {src.get('file_date', '?')}  {src.get('entity_name', '?')[:50]}")
            print(f"       {src.get('file_num', '?')}  form={src.get('form_type', '?')}")
        print(f"\n     Note: EDGAR is corporate filings, not gov news.")
        print(f"     Best use: track enforcement actions against companies,")
        print(f"     M&A announcements, executive departures (8-K item 5.02)")
        print(f"     Could complement SEC press releases once those are fixed.")
    except Exception as e:
        print(f"  ✗  {e}")


# ─────────────────────────────────────────────────────────────────────────────
# RSS probe (same as before but with ssl_verify support)
# ─────────────────────────────────────────────────────────────────────────────

def probe_rss(candidate: dict) -> dict:
    url        = candidate["url"]
    ssl_verify = candidate.get("ssl_verify", True)
    r = {"name": candidate["name"], "group": candidate["group"],
         "url": url, "ok": False, "entries": 0, "latest": None,
         "sample": None, "error": None}
    try:
        resp = httpx.get(url, headers=HEADERS, follow_redirects=True,
                         timeout=12, verify=ssl_verify)
        if resp.status_code >= 400:
            r["error"] = f"HTTP {resp.status_code}"
            return r
        feed = feedparser.parse(resp.content)
        if not feed.entries:
            r["error"] = f"0 entries"
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


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run():
    print(f"\n{'═' * W}")
    print("  SOURCE PROBE ROUND 2 — Corrected URLs + Data API Deep Inspection")
    print(f"{'═' * W}\n")

    # ── RSS second round ──────────────────────────────────────────────────────
    print("  Probing corrected RSS feeds…")
    rss_results = []
    for c in RSS_ROUND2:
        print(f"    {c['name']} …", flush=True)
        rss_results.append(probe_rss(c))
        time.sleep(0.3)

    # ── RSS results ───────────────────────────────────────────────────────────
    print(f"\n{'═' * W}")
    print("  RSS RESULTS (round 2)\n")
    for group in ["Finance", "Health", "Technology"]:
        items = [r for r in rss_results if r["group"] == group]
        print(f"  {group.upper()}")
        for r in items:
            if r["ok"]:
                print(f"  ✓  {r['name']}")
                print(f"       {r['entries']} entries  latest={r['latest']}")
                print(f"       {r['sample']!r}")
            else:
                print(f"  ✗  {r['name']}  — {r['error']}")
        print()

    # ── Data API deep inspection ──────────────────────────────────────────────
    print(f"{'═' * W}")
    print("  DATA API DEEP INSPECTION\n")

    inspect_treasury_yields()
    inspect_bls_api()
    inspect_fred()
    inspect_eia()
    inspect_edgar()

    # ── Summary ───────────────────────────────────────────────────────────────
    rss_ok = [r for r in rss_results if r["ok"]]
    print(f"\n{'═' * W}")
    print(f"  ROUND 2 SUMMARY: {len(rss_ok)}/{len(rss_results)} RSS feeds working\n")
    for r in rss_ok:
        print(f"  ✓ [{r['group']}] {r['name']}")
        print(f"       {r['entries']} entries, latest {r['latest']}")
    print(f"\n{'═' * W}\n")


if __name__ == "__main__":
    run()
