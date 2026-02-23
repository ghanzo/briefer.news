"""
test_international_sources.py — Probe international RSS feeds and web sources.

Covers:
  Energy/Industry   — IEA, OPEC, Baker Hughes, EIA (cross-check), Wood Mac
  Innovation        — Hacker News, GitHub Trending, arXiv AI, Y Combinator
  Europe            — EU institutions, ECB, NATO, UK, OSCE
  International     — UN, WHO, IMF, World Bank, WTO, BIS (Basel), OECD
  Middle East       — Al Jazeera, Saudi SPA, Israel MFA, UAE WAM, Arab League
  Asia (non-China)  — Japan MFA, Japan Cabinet, BOJ, South Korea MFA, Taiwan MFA,
                      Singapore PM, MAS Singapore, ASEAN
  China             — Xinhua, MFA China, State Council, MOFCOM, People's Daily
  Russia            — Kremlin, MFA Russia, TASS
  India             — PIB, MEA India, RBI
  South America     — Agência Brasil, ECLAC, OAS
  Africa            — African Union, African Dev Bank, South Africa Gov

For RSS/feeds: reachability + entry count + latest date + sample title.
"""

import sys
import io
import time
import logging

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import feedparser
import httpx

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("test_international")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BrieferBot/1.0; +https://briefer.news)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}
TIMEOUT = 15


# ─────────────────────────────────────────────────────────────────────────────
# Candidates
# ─────────────────────────────────────────────────────────────────────────────

CANDIDATES = [

    # ── ENERGY INDUSTRY ───────────────────────────────────────────────────────
    # These are tier-1 primary sources for the physical substrate layer.
    # IEA and OPEC are the authoritative global energy data bodies.
    # Baker Hughes rig count is the best weekly leading indicator for production.
    {"group": "Energy Industry", "name": "IEA — News & Reports",
     "url": "https://www.iea.org/news.xml"},
    {"group": "Energy Industry", "name": "IEA — RSS (alt)",
     "url": "https://www.iea.org/api/rss/feed"},
    {"group": "Energy Industry", "name": "OPEC — Press releases",
     "url": "https://www.opec.org/opec_web/en/press_room/24.htm"},
    {"group": "Energy Industry", "name": "OPEC — RSS",
     "url": "https://www.opec.org/opec_web/RSS/pressreleases.rss"},
    {"group": "Energy Industry", "name": "Baker Hughes — Rig Count (weekly)",
     "url": "https://rigcount.bakerhughes.com/static-files/rss"},
    {"group": "Energy Industry", "name": "Baker Hughes — News RSS",
     "url": "https://investors.bakerhughes.com/rss/news-releases.xml"},
    {"group": "Energy Industry", "name": "Oil Price — News",
     "url": "https://oilprice.com/rss/main"},
    {"group": "Energy Industry", "name": "Reuters — Energy (commodity wire)",
     "url": "https://feeds.reuters.com/reuters/businessNews"},
    {"group": "Energy Industry", "name": "S&P Global — Commodity Insights",
     "url": "https://www.spglobal.com/commodityinsights/en/rss-feed"},
    {"group": "Energy Industry", "name": "Mining.com — Critical Minerals",
     "url": "https://www.mining.com/feed/"},
    {"group": "Energy Industry", "name": "SPE — Oil & Gas journal",
     "url": "https://www.spe.org/en/jpt/jpt-rss/"},

    # ── INNOVATION SIGNALS ────────────────────────────────────────────────────
    # Bottom-up signals: where builders and researchers are concentrating.
    {"group": "Innovation", "name": "Hacker News — Top Stories",
     "url": "https://news.ycombinator.com/rss"},
    {"group": "Innovation", "name": "Hacker News — Best (>= 100pts)",
     "url": "https://hnrss.org/best"},
    {"group": "Innovation", "name": "arXiv — AI (cs.AI)",
     "url": "https://arxiv.org/rss/cs.AI"},
    {"group": "Innovation", "name": "arXiv — Machine Learning (cs.LG)",
     "url": "https://arxiv.org/rss/cs.LG"},
    {"group": "Innovation", "name": "arXiv — Emerging Technologies (cs.ET)",
     "url": "https://arxiv.org/rss/cs.ET"},
    {"group": "Innovation", "name": "Y Combinator — Blog",
     "url": "https://www.ycombinator.com/blog.rss"},
    {"group": "Innovation", "name": "GitHub — Trending (unofficial RSS)",
     "url": "https://github-trending-api.wasmup.com/rss"},
    {"group": "Innovation", "name": "GitHub Trending (alt scrape-based)",
     "url": "https://mshibanami.github.io/GitHubTrendingRSS/daily/all.xml"},
    {"group": "Innovation", "name": "Product Hunt — Daily",
     "url": "https://www.producthunt.com/feed"},

    # ── EUROPE ────────────────────────────────────────────────────────────────
    {"group": "Europe", "name": "European Commission — Press Corner RSS",
     "url": "https://ec.europa.eu/commission/presscorner/api/rss/en"},
    {"group": "Europe", "name": "European Commission — Press Releases (alt)",
     "url": "https://europa.eu/rapid/rss-feed"},
    {"group": "Europe", "name": "ECB — Press Releases",
     "url": "https://www.ecb.europa.eu/press/pr/date/2026/html/rss.xml"},
    {"group": "Europe", "name": "ECB — All publications",
     "url": "https://www.ecb.europa.eu/rss/press.html"},
    {"group": "Europe", "name": "ECB — RSS feed (known working)",
     "url": "https://www.ecb.europa.eu/home/html/rss.en.html"},
    {"group": "Europe", "name": "NATO — Press Releases",
     "url": "https://www.nato.int/cps/en/natohq/news.htm?selectedLocale=en&type=31"},
    {"group": "Europe", "name": "NATO — RSS feed",
     "url": "https://www.nato.int/nato_static/assets/xml/rss/rss_news.xml"},
    {"group": "Europe", "name": "UK Government — News & Communications",
     "url": "https://www.gov.uk/search/news-and-communications.atom"},
    {"group": "Europe", "name": "UK Government — Foreign Policy",
     "url": "https://www.gov.uk/search/news-and-communications.atom?subtopic%5B%5D=foreign-policy"},
    {"group": "Europe", "name": "European Parliament — News",
     "url": "https://www.europarl.europa.eu/rss/doc/top-stories/en.rss"},
    {"group": "Europe", "name": "Council of EU — Press releases",
     "url": "https://www.consilium.europa.eu/en/press/press-releases/?rss=true"},
    {"group": "Europe", "name": "OSCE — News",
     "url": "https://www.osce.org/news.xml"},

    # ── INTERNATIONAL INSTITUTIONS ─────────────────────────────────────────────
    {"group": "International", "name": "UN — All News",
     "url": "https://news.un.org/feed/subscribe/en/news/all/rss.xml"},
    {"group": "International", "name": "UN — Security Council",
     "url": "https://news.un.org/feed/subscribe/en/news/topic/security-council/rss.xml"},
    {"group": "International", "name": "WHO — News",
     "url": "https://www.who.int/rss-feeds/news-english.xml"},
    {"group": "International", "name": "IMF — News",
     "url": "https://www.imf.org/en/News/rss"},
    {"group": "International", "name": "World Bank — News",
     "url": "https://www.worldbank.org/en/news/all.rss"},
    {"group": "International", "name": "WTO — News",
     "url": "https://www.wto.org/english/news_e/news_e.rss"},
    {"group": "International", "name": "BIS (Basel) — Press releases",
     "url": "https://www.bis.org/press/index.htm"},
    {"group": "International", "name": "BIS (Basel) — RSS",
     "url": "https://www.bis.org/rss/press.htm"},
    {"group": "International", "name": "OECD — News",
     "url": "https://www.oecd.org/newsroom/news.xml"},
    {"group": "International", "name": "G20 — News",
     "url": "https://www.g20.org/en/news.xml"},

    # ── MIDDLE EAST ───────────────────────────────────────────────────────────
    {"group": "Middle East", "name": "Al Jazeera — World",
     "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"group": "Middle East", "name": "Saudi Press Agency (SPA) — English",
     "url": "https://www.spa.gov.sa/servefeed.php?lang=en&url=https://www.spa.gov.sa/feeds.rss"},
    {"group": "Middle East", "name": "Saudi Press Agency — alt RSS",
     "url": "https://www.spa.gov.sa/en/rss"},
    {"group": "Middle East", "name": "Israel MFA — All Publications",
     "url": "https://www.gov.il/en/api/dynamicCollector?OfficeId=1&Status=0&Skip=0&Limit=20&ServiceName=pressService&Format=rss"},
    {"group": "Middle East", "name": "Israel MFA — RSS (old)",
     "url": "https://mfa.gov.il/MFADocuments/PressReleases/2026/rss.xml"},
    {"group": "Middle East", "name": "UAE — WAM News Agency",
     "url": "https://wam.ae/en/rss"},
    {"group": "Middle East", "name": "UAE — WAM alt",
     "url": "https://www.wam.ae/en/page-33619"},
    {"group": "Middle East", "name": "Turkey — Anadolu Agency",
     "url": "https://www.aa.com.tr/en/rss/default?cat=politics"},
    {"group": "Middle East", "name": "Arab League — News",
     "url": "https://www.lasportal.org/ar/news/Pages/News.aspx"},

    # ── ASIA (non-China) ──────────────────────────────────────────────────────
    {"group": "Asia", "name": "Japan MFA — Press Releases",
     "url": "https://www.mofa.go.jp/press/release/press_rss.xml"},
    {"group": "Asia", "name": "Japan Cabinet Office",
     "url": "https://www.kantei.go.jp/foreign/headline/rss.xml"},
    {"group": "Asia", "name": "Bank of Japan — Press releases",
     "url": "https://www.boj.or.jp/en/announcements/release_2026/rss.xml"},
    {"group": "Asia", "name": "Bank of Japan — RSS",
     "url": "https://www.boj.or.jp/en/rss/news.xml"},
    {"group": "Asia", "name": "South Korea MFA — News",
     "url": "https://www.mofa.go.kr/eng/brd/m_5674/list.do?id=4"},
    {"group": "Asia", "name": "South Korea MFA — RSS",
     "url": "https://www.mofa.go.kr/eng/brd/m_5674/rss.do"},
    {"group": "Asia", "name": "Taiwan MFA — English",
     "url": "https://www.mofa.gov.tw/en/rss.aspx"},
    {"group": "Asia", "name": "Singapore PM Office — News",
     "url": "https://www.pmo.gov.sg/Newsroom/rss"},
    {"group": "Asia", "name": "MAS Singapore — Press releases",
     "url": "https://www.mas.gov.sg/news.rss"},
    {"group": "Asia", "name": "ASEAN — News",
     "url": "https://asean.org/news/feed/"},

    # ── CHINA ─────────────────────────────────────────────────────────────────
    {"group": "China", "name": "Xinhua — English wire",
     "url": "http://www.xinhuanet.com/english/rss/worldrss.xml"},
    {"group": "China", "name": "Xinhua — World (https)",
     "url": "https://english.news.cn/rss/world.xml"},
    {"group": "China", "name": "Xinhua — China (https)",
     "url": "https://english.news.cn/rss/china.xml"},
    {"group": "China", "name": "People's Daily — English",
     "url": "http://en.people.cn/rss/90777.xml"},
    {"group": "China", "name": "Global Times — RSS",
     "url": "https://www.globaltimes.cn/rss/outbrain.xml"},
    {"group": "China", "name": "MFA China — English (RSS check)",
     "url": "https://www.fmprc.gov.cn/eng/rss/"},
    {"group": "China", "name": "CGTN — World",
     "url": "https://www.cgtn.com/subscribe/rss/section/world.do"},
    {"group": "China", "name": "State Council — English news",
     "url": "http://english.www.gov.cn/rss/news.xml"},

    # ── RUSSIA ────────────────────────────────────────────────────────────────
    {"group": "Russia", "name": "Kremlin — English news",
     "url": "http://kremlin.ru/events/all/feed"},
    {"group": "Russia", "name": "Kremlin — English (https)",
     "url": "https://kremlin.ru/events/all/feed"},
    {"group": "Russia", "name": "MFA Russia — English",
     "url": "https://mid.ru/en/press_service/minister_speeches/rss/"},
    {"group": "Russia", "name": "MFA Russia — Press releases",
     "url": "https://mid.ru/en/press_service/official_statement/rss/"},
    {"group": "Russia", "name": "TASS — World news",
     "url": "https://tass.com/rss/v2.xml"},
    {"group": "Russia", "name": "TASS — Politics",
     "url": "https://tass.com/rss/politics.xml"},
    {"group": "Russia", "name": "RT — English",
     "url": "https://www.rt.com/rss/news/"},

    # ── INDIA ─────────────────────────────────────────────────────────────────
    {"group": "India", "name": "PIB India — All releases",
     "url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"},
    {"group": "India", "name": "MEA India — Press releases",
     "url": "https://www.mea.gov.in/rss/press-releases.xml"},
    {"group": "India", "name": "Reserve Bank of India — Press releases",
     "url": "https://rbi.org.in/Scripts/RSSFeedsRoot.aspx?Id=PressRelease"},
    {"group": "India", "name": "RBI — Monetary Policy",
     "url": "https://rbi.org.in/Scripts/RSSFeedsRoot.aspx?Id=MonetaryPolicy"},

    # ── SOUTH AMERICA ─────────────────────────────────────────────────────────
    {"group": "South America", "name": "Agência Brasil — English",
     "url": "https://agenciabrasil.ebc.com.br/en/rss/ultimasnoticias/feed"},
    {"group": "South America", "name": "ECLAC/CEPAL — News",
     "url": "https://www.cepal.org/en/rss.xml"},
    {"group": "South America", "name": "OAS — News",
     "url": "https://www.oas.org/en/media_center/press_releases.asp?sCodigo=rss"},
    {"group": "South America", "name": "OAS — RSS",
     "url": "https://www.oas.org/rss/oas_news.xml"},

    # ── AFRICA ────────────────────────────────────────────────────────────────
    {"group": "Africa", "name": "African Union — News",
     "url": "https://au.int/en/rss.xml"},
    {"group": "Africa", "name": "African Development Bank — News",
     "url": "https://www.afdb.org/en/rss.xml"},
    {"group": "Africa", "name": "South Africa Gov — News",
     "url": "https://www.gov.za/rss.xml"},
    {"group": "Africa", "name": "AllAfrica — Top Stories",
     "url": "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf"},
]

GROUPS_ORDER = [
    "Energy Industry", "Innovation",
    "Europe", "International", "Middle East", "Asia",
    "China", "Russia", "India", "South America", "Africa",
]


# ─────────────────────────────────────────────────────────────────────────────
# Probe
# ─────────────────────────────────────────────────────────────────────────────

def probe(candidate: dict) -> dict:
    url = candidate["url"]
    r = {
        "name": candidate["name"],
        "group": candidate["group"],
        "url": url,
        "ok": False,
        "entries": 0,
        "latest": None,
        "sample": None,
        "error": None,
        "http_status": None,
        "content_type": None,
    }
    try:
        resp = httpx.get(url, headers=HEADERS, follow_redirects=True,
                         timeout=TIMEOUT, verify=False)
        r["http_status"] = resp.status_code
        r["content_type"] = resp.headers.get("content-type", "")[:60]

        if resp.status_code >= 400:
            r["error"] = f"HTTP {resp.status_code}"
            r["sample"] = resp.text[:120]
            return r

        # Try feedparser on raw content
        feed = feedparser.parse(resp.content)
        if feed.entries:
            r["ok"] = True
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
        else:
            # Possibly XML/JSON with no RSS entries — report raw snippet
            r["error"] = f"0 RSS entries (bozo={feed.bozo})"
            r["sample"] = resp.text[:120].replace("\n", " ").strip()

    except Exception as e:
        r["error"] = str(e)[:120]
    return r


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run():
    W = 74
    print(f"\n{'═' * W}")
    print("  INTERNATIONAL SOURCE PROBE")
    print(f"{'═' * W}\n")

    results = []
    for c in CANDIDATES:
        print(f"  [{c['group']:12}] {c['name']} …", flush=True)
        results.append(probe(c))
        time.sleep(0.4)

    # ── Print by group ────────────────────────────────────────────────────────
    print(f"\n{'═' * W}")
    print("  RESULTS BY REGION")

    for group in GROUPS_ORDER:
        items = [r for r in results if r["group"] == group]
        if not items:
            continue
        ok = [r for r in items if r["ok"]]
        print(f"\n  {'─' * 70}")
        print(f"  {group.upper()}  ({len(ok)}/{len(items)} working)")
        print(f"  {'─' * 70}")
        for r in items:
            status = "✓" if r["ok"] else "✗"
            print(f"  {status}  {r['name']}")
            if r["ok"]:
                print(f"       entries={r['entries']}  latest={r['latest']}")
                print(f"       sample : {r['sample']!r}")
            else:
                detail = r.get("error", "?")
                if r.get("http_status"):
                    detail = f"HTTP {r['http_status']} — {detail}"
                print(f"       error  : {detail}")
                if r.get("sample") and not r.get("ok"):
                    snippet = r["sample"][:80].replace("\n", " ")
                    if snippet.strip():
                        print(f"       body   : {snippet!r}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'═' * W}")
    print("  SUMMARY — WORKING FEEDS")
    print(f"{'═' * W}")

    all_ok = [r for r in results if r["ok"]]
    all_bad = [r for r in results if not r["ok"]]

    for group in GROUPS_ORDER:
        items = [r for r in all_ok if r["group"] == group]
        if items:
            print(f"\n  {group}:")
            for r in items:
                print(f"    ✓  {r['name']}")
                print(f"       {r['entries']} entries, latest {r['latest']}")

    if all_bad:
        print(f"\n  Failed ({len(all_bad)}):")
        for r in all_bad:
            print(f"    ✗  [{r['group']}] {r['name']}  — {r.get('error','?')[:60]}")

    print(f"\n  Total: {len(all_ok)}/{len(results)} accessible\n")
    print(f"{'═' * W}\n")


if __name__ == "__main__":
    run()
