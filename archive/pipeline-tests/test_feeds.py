"""
test_feeds.py — Check which RSS feeds are live and returning entries.

Prints a status table: URL, HTTP status, entry count, and first headline.

Usage:
  python test_feeds.py           # check all active sources
  python test_feeds.py --new     # check only the newly added gov sources
"""

import argparse
import sys
import feedparser

# ── Feeds to verify ───────────────────────────────────────────────────────────
# Format: (label, url)

NEW_GOV_FEEDS = [
    # White House & Defense
    ("White House",                  "https://www.whitehouse.gov/feed/"),
    ("DoD — News",                   "https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=20"),
    ("DARPA",                        "https://www.darpa.mil/rss.xml"),

    # Trade / Sanctions / Export Controls
    ("Treasury — Press Releases",    "https://home.treasury.gov/news/press-releases.xml"),
    ("OFAC — Sanctions",             "https://home.treasury.gov/policy-issues/office-of-foreign-assets-control-sanctions-programs-and-information/rss"),
    ("USTR — Press Releases",        "https://ustr.gov/about-us/policy-offices/press-office/press-releases/rss.xml"),
    ("BIS — Fed Register filter",    "https://www.federalregister.gov/articles/search.rss?conditions%5Bagencies%5D%5B%5D=industry-and-security-bureau&conditions%5Btype%5D%5B%5D=RULE&conditions%5Btype%5D%5B%5D=PRORULE&conditions%5Btype%5D%5B%5D=NOTICE"),
    ("Federal Register — EO/Rules",  "https://www.federalregister.gov/articles/search.rss?conditions%5Btype%5D%5B%5D=PRESDOCU&conditions%5Btype%5D%5B%5D=RULE&conditions%5Btype%5D%5B%5D=PRORULE"),

    # National Security & Cyber
    ("DOJ — National Security",      "https://www.justice.gov/rss/national-security.xml"),
    ("CISA — Alerts",                "https://www.cisa.gov/uscert/ncas/alerts.xml"),
    ("GAO — Reports",                "https://www.gao.gov/rss/reports.xml"),

    # Energy & Nuclear
    ("EIA — Today in Energy",        "https://www.eia.gov/rss/todayinenergy.xml"),
    ("EIA — Natural Gas",            "https://www.eia.gov/rss/ngs.xml"),
    ("DOE — News",                   "https://www.energy.gov/rss.xml"),
    ("NRC — Press Releases",         "https://www.nrc.gov/reading-rm/doc-collections/news/rss/nrc-news.xml"),
    ("Federal Reserve — Speeches",   "https://www.federalreserve.gov/feeds/speeches.xml"),
    ("Federal Reserve — Press",      "https://www.federalreserve.gov/feeds/press_all.xml"),

    # Science / Health / Ecosystem
    ("NASA — Breaking News",         "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
    ("NOAA — News",                  "https://www.noaa.gov/media-release/feed"),
    ("EPA — News Releases",          "https://www.epa.gov/newsreleases/search/rss"),
    ("NIH — News Releases",          "https://www.nih.gov/rss/news-releases.xml"),
    ("CDC — Newsroom",               "https://tools.cdc.gov/api/v2/resources/media/403372.rss"),
    ("USGS — News",                  "https://www.usgs.gov/rss/science-news.xml"),
    ("IAEA — News",                  "https://www.iaea.org/feeds/topnews.xml"),

    # Chinese state media (already verified but re-check)
    ("Xinhua — World",               "http://www.xinhuanet.com/english/rss/worldrss.xml"),
    ("People's Daily — World",       "http://en.people.cn/rss/90777.xml"),
    ("Global Times — World",         "https://www.globaltimes.cn/rss/outbrain.xml"),
    ("CGTN — World",                 "https://www.cgtn.com/subscribe/rss/section/world.do"),
    ("China Daily — World",          "http://www.chinadaily.com.cn/rss/world_rss.xml"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BrieferBot/1.0; +https://briefer.news)"
}

COL_W = 32  # label column width


def check_feed(label: str, url: str) -> dict:
    try:
        feed = feedparser.parse(url, request_headers=HEADERS)
        status = feed.get("status", 0)
        entries = len(feed.entries)
        first = feed.entries[0].get("title", "")[:70] if entries else ""
        bozo = feed.bozo
        return {"label": label, "status": status, "entries": entries, "first": first, "bozo": bozo, "ok": entries > 0}
    except Exception as e:
        return {"label": label, "status": 0, "entries": 0, "first": str(e)[:70], "bozo": True, "ok": False}


def main():
    feeds = NEW_GOV_FEEDS

    print(f"\n{'SOURCE':<{COL_W}} {'HTTP':>4}  {'ENTRIES':>7}  FIRST HEADLINE")
    print("─" * 110)

    ok_count = 0
    fail_count = 0

    for label, url in feeds:
        r = check_feed(label, url)
        status_str = str(r["status"]) if r["status"] else "ERR"
        marker = "✓" if r["ok"] else "✗"
        print(f"{marker} {r['label']:<{COL_W-2}} {status_str:>4}  {r['entries']:>7}  {r['first']}")
        if r["ok"]:
            ok_count += 1
        else:
            fail_count += 1

    print("─" * 110)
    print(f"\n{ok_count} live  |  {fail_count} dead/empty\n")


if __name__ == "__main__":
    main()
