"""
test_gov_reach.py — Playwright reachability probe for JS-rendered gov sites.

For each candidate site, renders the listing page and reports:
  - Whether the page loaded
  - Page title (helps detect Cloudflare/captcha walls)
  - Number of same-domain links matching the link_pattern
  - First 3 matching links

Usage:
  python test_gov_reach.py
"""

import logging
import sys
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("test_gov_reach")

CANDIDATES = [
    {
        "name":         "White House — Briefing Room",
        "url":          "https://www.whitehouse.gov/briefing-room/",
        "link_pattern": "/briefing-room/",
        "note":         "Trump admin dropped RSS entirely",
    },
    {
        "name":         "U.S. Treasury — Press Releases",
        "url":          "https://home.treasury.gov/news/press-releases",
        "link_pattern": "/news/press-releases/",
        "note":         "RSS entry exists but flagged email-only; verify",
    },
    {
        "name":         "FBI — Press Releases",
        "url":          "https://www.fbi.gov/news/press-releases",
        "link_pattern": "/news/press-releases/",
        "note":         "RSS removed",
    },
    {
        "name":         "FTC — Press Releases",
        "url":          "https://www.ftc.gov/news-events/news/press-releases",
        "link_pattern": "/news-events/news/press-releases/",
        "note":         "404 on all known RSS patterns",
    },
    {
        "name":         "ODNI — Press Releases",
        "url":          "https://www.dni.gov/index.php/newsroom/press-releases",
        "link_pattern": "/newsroom/press-releases/",
        "note":         "No public RSS",
    },
    {
        "name":         "ARPA-E — News",
        "url":          "https://arpa-e.energy.gov/news-and-media/press-releases",
        "link_pattern": "/news-and-media/",
        "note":         "Publishes via energy.gov CMS; may overlap",
    },
    {
        "name":         "FCC — Press Releases",
        "url":          "https://www.fcc.gov/news-events/press-releases",
        "link_pattern": "/news-events/press-releases/",
        "note":         "Connection refused previously; may be Cloudflare",
    },
]


def probe(candidate: dict, browser) -> dict:
    url          = candidate["url"]
    link_pattern = candidate["link_pattern"]
    base_domain  = urlparse(url).netloc
    result = {
        "name":    candidate["name"],
        "url":     url,
        "note":    candidate["note"],
        "ok":      False,
        "title":   None,
        "n_links": 0,
        "samples": [],
        "error":   None,
    }

    try:
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        html  = page.content()
        title = page.title()
        page.close()

        result["title"] = title

        soup = BeautifulSoup(html, "lxml")
        found = []
        seen  = set()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            abs_url = urljoin(url, href)
            parsed  = urlparse(abs_url)
            if parsed.netloc != base_domain:
                continue
            if link_pattern and link_pattern not in parsed.path:
                continue
            canonical = abs_url.split("#")[0]
            if canonical in seen or canonical == url:
                continue
            seen.add(canonical)
            found.append(canonical)

        result["ok"]      = True
        result["n_links"] = len(found)
        result["samples"] = found[:3]

    except Exception as e:
        result["error"] = str(e)

    return result


def run() -> None:
    from playwright.sync_api import sync_playwright
    from scraper.browser import browser_manager

    try:
        browser = browser_manager.get_browser()

        print("\n" + "═" * 70)
        print("  GOV SITE PLAYWRIGHT REACHABILITY PROBE")
        print("═" * 70 + "\n")

        results = []
        for candidate in CANDIDATES:
            print(f"  Probing: {candidate['name']} …", flush=True)
            r = probe(candidate, browser)
            results.append(r)

        print("\n" + "═" * 70)
        for r in results:
            status = "✓ OK" if r["ok"] else "✗ FAIL"
            print(f"\n{status}  {r['name']}")
            print(f"       url  : {r['url']}")
            print(f"       note : {r['note']}")
            if r["title"]:
                print(f"       title: {r['title'][:80]}")
            if r["ok"]:
                print(f"       links: {r['n_links']} matching")
                for s in r["samples"]:
                    print(f"              {s}")
            else:
                print(f"       error: {r['error']}")

        print("\n" + "═" * 70)
        viable   = [r for r in results if r["ok"] and r["n_links"] > 0]
        blocked  = [r for r in results if r["ok"] and r["n_links"] == 0]
        failed   = [r for r in results if not r["ok"]]
        print(f"\n  SUMMARY: {len(viable)} viable, {len(blocked)} loaded but 0 links, {len(failed)} failed/blocked\n")
        if viable:
            print("  Ready to add as web_scrape:")
            for r in viable:
                print(f"    • {r['name']}  ({r['n_links']} links)")
        if blocked:
            print("  Loaded but no matching links (check link_pattern):")
            for r in blocked:
                print(f"    • {r['name']}  title={r['title']!r}")
        if failed:
            print("  Failed (Cloudflare / timeout / refused):")
            for r in failed:
                print(f"    • {r['name']}  error={r['error'][:80]!r}")

    finally:
        browser_manager.close()


if __name__ == "__main__":
    run()
