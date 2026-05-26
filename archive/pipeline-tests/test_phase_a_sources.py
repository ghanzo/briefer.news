"""
test_phase_a_sources.py — Probe Phase A RSS candidates from SOURCES_PLAN.md.

Tests all RSS feeds that are "likely_open" or unconfirmed in the plan.
Runs locally (no Docker needed). Reports entry counts and freshness.

Usage: python test_phase_a_sources.py
"""

import io
import sys
import time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import feedparser
import httpx
from datetime import datetime, timezone

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    )
}

CANDIDATES = [
    # ── Europe ──────────────────────────────────────────────────────────────────
    ("EUR", "Bank of England — News",          "https://www.bankofengland.co.uk/rss/news"),
    ("EUR", "EC Newsroom RSS (try 1)",         "https://ec.europa.eu/newsroom/index.cfm?do=rss"),
    ("EUR", "EC Newsroom RSS (try 2)",         "https://ec.europa.eu/commission/presscorner/api/documents?keyword=&institution=&service=&dateTo=&dateFrom=&representationTo=&representationFrom=&type=IP,STATEMENT,MEX&limit=10&format=rss"),
    ("EUR", "NATO News",                       "https://www.nato.int/cps/en/natohq/news.htm?selectedLocale=en&rss=1"),
    ("EUR", "NATO RSS",                        "https://www.nato.int/docu/update/rss-en.xml"),
    ("EUR", "European Parliament — News RSS",  "https://www.europarl.europa.eu/rss/doc/top-stories/en.xml"),
    ("EUR", "Council of EU — Press",          "https://www.consilium.europa.eu/en/press/press-releases/?rss=true"),
    ("EUR", "Bundesbank — Press RSS",          "https://www.bundesbank.de/dynamic/action/en/presse/pressemitteilungen/736294/rssselect"),

    # ── Russia ───────────────────────────────────────────────────────────────────
    ("RUS", "Kremlin — Russian feed (HTTP)",   "http://kremlin.ru/events/all/feed"),
    ("RUS", "TASS — Russian (mezhdunarodnaya)","https://tass.ru/mezhdunarodnaya-panorama"),
    ("RUS", "TASS — Russian RSS",              "https://tass.ru/rss/v2.xml"),
    ("RUS", "MFA Russia — feed",               "https://www.mid.ru/ru/press_service/spokesman/briefings/rss/"),

    # ── Middle East ──────────────────────────────────────────────────────────────
    ("MID", "Kuwait KUNA RSS",                 "https://www.kuna.net.kw/rss"),
    ("MID", "Kuwait KUNA RSS (alt)",           "https://www.kuna.net.kw/NewsAgencyPublicSite/xml/english/rss.xml"),
    ("MID", "Iran IRNA RSS",                   "https://www.irna.ir/rss"),
    ("MID", "Iran IRNA RSS (English)",         "https://en.irna.ir/rss"),
    ("MID", "Iran Tasnim — English RSS",       "https://www.tasnimnews.com/en/rss"),
    ("MID", "Iran Tasnim — English (alt)",     "https://www.tasnimnews.com/en/rss/feed/default"),
    ("MID", "Qatar QNA — RSS",                 "https://www.qna.org.qa/rss"),

    # ── India ────────────────────────────────────────────────────────────────────
    ("IND", "PIB RSS (try browser UA)",        "https://www.pib.gov.in/RssMain.aspx"),
    ("IND", "PIB RSS (alt 1)",                 "https://pib.gov.in/newsite/erelease.aspx"),
    ("IND", "RBI — Press Releases",           "https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"),
    ("IND", "RBI — RSS",                      "https://rbi.org.in/rss.aspx"),
    ("IND", "Ministry of Finance",            "https://finmin.nic.in/press-room"),
    ("IND", "MEA — Press releases",           "https://www.mea.gov.in/press-releases.htm"),

    # ── US gaps ──────────────────────────────────────────────────────────────────
    ("USA", "USDA — Press Releases RSS",      "https://www.usda.gov/media/press-releases/rss"),
    ("USA", "USDA — RSS alt",                 "https://content.govdelivery.com/accounts/USDAOC/bulletins/rss"),
    ("USA", "DOJ — Civil Rights RSS",         "https://www.justice.gov/rss/civil-rights.xml"),
    ("USA", "DOJ — All news RSS",             "https://www.justice.gov/news.xml"),
    ("USA", "Treasury — Press releases RSS",  "https://home.treasury.gov/news/press-releases/rss"),
    ("USA", "Treasury — RSS alt",             "https://treasury.gov/resource-center/data-chart-center/interest-rates/Feeds.aspx"),

    # ── South America ────────────────────────────────────────────────────────────
    ("SAM", "Brazil — Agencia Brasil RSS",    "https://agenciabrasil.ebc.com.br/rss/politica/feed.xml"),
    ("SAM", "Brazil — Agencia Brasil EN",     "https://agenciabrasil.ebc.com.br/en/rss/geral/feed.xml"),
    ("SAM", "Argentina — Casa Rosada",        "https://www.casarosada.gob.ar/rss"),
    ("SAM", "Venezuela — PDVSA News",         "https://www.pdvsa.com/index.php?option=com_content&view=category&id=48&format=feed"),
    ("SAM", "Colombia Cancilleria",           "https://www.cancilleria.gov.co/feed"),

    # ── Asia non-China ───────────────────────────────────────────────────────────
    ("ASI", "MFA Japan RSS (English)",        "https://www.mofa.go.jp/press/release/rss.xml"),
    ("ASI", "MFA Japan RSS (alt)",            "https://www.mofa.go.jp/rss/rss-en.xml"),
    ("ASI", "Bank of Japan RSS",              "https://www.boj.or.jp/en/announcements/release/rss.xml"),
    ("ASI", "MFA Korea RSS",                  "https://www.mofa.go.kr/eng/rss/pressReleases.xml"),
    ("ASI", "Bank of Korea",                  "https://www.bok.or.kr/eng/bbs/B0000034/list.do?menuNo=600011&boardType=G"),
    ("ASI", "Taiwan MFA — RSS",               "https://www.mofa.gov.tw/en/rss.aspx"),
    ("ASI", "Mainland Affairs Council",       "https://www.mac.gov.tw/en/News.aspx?n=D2D52F72FECE98F3"),
    ("ASI", "Singapore MAS RSS",              "https://www.mas.gov.sg/news"),
    ("ASI", "Singapore MTI RSS",              "https://www.mti.gov.sg/Newsroom/Press-Releases"),
    ("ASI", "ASEAN Secretariat",              "https://asean.org/feed"),
]


def probe_rss(url: str, timeout: int = 10) -> dict:
    """Try to fetch and parse a URL as RSS. Returns status info."""
    try:
        resp = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=timeout, verify=False)
        if resp.status_code != 200:
            return {"status": f"HTTP {resp.status_code}", "entries": 0, "latest": None, "content_type": ""}

        feed = feedparser.parse(resp.text)
        entries = len(feed.entries)
        content_type = resp.headers.get("content-type", "")

        latest = None
        for entry in feed.entries[:3]:
            raw = entry.get("published") or entry.get("updated") or entry.get("dc_date")
            if raw:
                try:
                    from dateutil import parser as dp
                    latest = dp.parse(raw)
                    break
                except Exception:
                    pass

        freshness = "?"
        if latest:
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=timezone.utc)
            days_old = (datetime.now(timezone.utc) - latest).days
            freshness = f"{days_old}d ago"

        if entries == 0 and not feed.feed:
            return {"status": "not_rss", "entries": 0, "latest": freshness, "content_type": content_type[:40]}

        return {"status": "ok", "entries": entries, "latest": freshness, "content_type": content_type[:40]}

    except httpx.TimeoutException:
        return {"status": "timeout", "entries": 0, "latest": None, "content_type": ""}
    except Exception as e:
        return {"status": f"error: {str(e)[:40]}", "entries": 0, "latest": None, "content_type": ""}


def main():
    print("Phase A RSS Source Probe")
    print("=" * 80)

    current_region = None
    results = []

    for region, name, url in CANDIDATES:
        if region != current_region:
            current_region = region
            print(f"\n  [{region}]")

        result = probe_rss(url)
        status = result["status"]
        entries = result["entries"]
        freshness = result["latest"] or ""

        if status == "ok" and entries > 0:
            icon = "OK"
        elif status == "ok" and entries == 0:
            icon = "EMPTY"
        elif status == "not_rss":
            icon = "NOT_RSS"
        elif "HTTP" in str(status):
            icon = status
        elif "timeout" in str(status):
            icon = "TIMEOUT"
        else:
            icon = "FAIL"

        results.append((region, name, url, icon, entries, freshness))
        print(f"    [{icon:<8}] {entries:>3} entries  {freshness:<12}  {name}")
        time.sleep(0.3)

    print("\n" + "=" * 80)
    print("SUMMARY — Accessible feeds:")
    accessible = [(r, n, u, ic, e, f) for r, n, u, ic, e, f in results if ic == "OK" and e > 0]
    for region, name, url, icon, entries, freshness in accessible:
        print(f"  [{region}] {entries:>3} entries  {freshness:<12}  {name}")
        print(f"         {url}")

    print(f"\n{len(accessible)}/{len(results)} accessible")


if __name__ == "__main__":
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except ImportError:
        pass
    main()
