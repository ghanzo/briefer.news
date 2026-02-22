"""
test_gov_deep.py — Deep link inspection for White House, FTC, ARPA-E.

For each site:
  - Renders the page with Playwright
  - Dumps all unique same-domain path prefixes (so we can pick the right link_pattern)
  - Shows the 10 most common path prefixes + sample URLs under each
  - Also tries wait_until="load" as fallback if networkidle returns nothing

Usage:
  python test_gov_deep.py
"""

import logging
import sys
from collections import Counter
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("test_gov_deep")

CANDIDATES = [
    {
        "name": "White House — Briefing Room",
        "url":  "https://www.whitehouse.gov/briefing-room/",
    },
    {
        "name": "FTC — Press Releases",
        "url":  "https://www.ftc.gov/news-events/news/press-releases",
    },
    {
        "name": "ARPA-E — Press Releases",
        "url":  "https://arpa-e.energy.gov/news-and-media/press-releases",
    },
]


def get_html(page, url: str, wait_until: str = "networkidle", timeout: int = 30000) -> tuple[str, str]:
    """Returns (html, page_title)."""
    page.goto(url, wait_until=wait_until, timeout=timeout)
    return page.content(), page.title()


def inspect_links(html: str, base_url: str) -> dict:
    """
    Return all unique same-domain hrefs, grouped by first two path segments.
    """
    base_domain = urlparse(base_url).netloc
    soup = BeautifulSoup(html, "lxml")

    all_links: list[str] = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:"):
            continue
        abs_url = urljoin(base_url, href)
        parsed  = urlparse(abs_url)
        if parsed.netloc != base_domain:
            continue
        canonical = abs_url.split("#")[0].rstrip("/")
        if canonical in seen or canonical == base_url.rstrip("/"):
            continue
        seen.add(canonical)
        all_links.append(canonical)

    # Group by first two path segments as prefix
    prefix_map: dict[str, list[str]] = {}
    for link in all_links:
        path   = urlparse(link).path
        parts  = [p for p in path.split("/") if p]
        prefix = "/" + "/".join(parts[:2]) + "/" if len(parts) >= 2 else ("/" + parts[0] + "/" if parts else "/")
        prefix_map.setdefault(prefix, []).append(link)

    return {
        "total":      len(all_links),
        "prefix_map": prefix_map,
        "all_links":  all_links,
    }


def probe_site(candidate: dict, browser) -> None:
    name = candidate["name"]
    url  = candidate["url"]

    print(f"\n{'═' * 70}")
    print(f"  {name}")
    print(f"  {url}")
    print(f"{'═' * 70}")

    page = browser.new_page()
    try:
        # Try networkidle first
        html, title = get_html(page, url, wait_until="networkidle", timeout=30000)
        strategy = "networkidle"
    except Exception as e:
        print(f"  networkidle failed: {e!s:.100}")
        try:
            page.goto(url, wait_until="load", timeout=30000)
            html  = page.content()
            title = page.title()
            strategy = "load"
        except Exception as e2:
            print(f"  load also failed: {e2!s:.120}")
            page.close()
            return

    print(f"  strategy : {strategy}")
    print(f"  title    : {title[:80]!r}")

    info = inspect_links(html, url)
    print(f"  total same-domain links: {info['total']}")

    if info["total"] == 0:
        print("  ⚠  No links found — page may be client-side rendered beyond what Playwright captured")
        # Dump a snippet of the raw HTML to help diagnose
        soup  = BeautifulSoup(html, "lxml")
        body  = soup.find("body")
        snip  = body.get_text(" ", strip=True)[:400] if body else html[:400]
        print(f"\n  Body text preview:\n  {snip!r}\n")
        page.close()
        return

    # Show prefix breakdown
    print(f"\n  Path prefix breakdown (top 12):")
    sorted_prefixes = sorted(info["prefix_map"].items(), key=lambda x: len(x[1]), reverse=True)
    for prefix, links in sorted_prefixes[:12]:
        print(f"    {len(links):3d} links  {prefix}")
        for l in links[:2]:
            print(f"             {l}")

    # Best candidate prefixes (>=3 links, not nav/utility paths)
    skip = {"/wp-", "/cdn-", "/static/", "/assets/", "/search/", "/tag/",
            "/category/", "/author/", "/page/", "/feed/"}
    candidates = [
        (prefix, links) for prefix, links in sorted_prefixes
        if len(links) >= 3 and not any(s in prefix for s in skip)
    ]
    if candidates:
        print(f"\n  Recommended link_pattern candidates:")
        for prefix, links in candidates[:4]:
            print(f"    '{prefix}'  ({len(links)} links)")

    page.close()


def run() -> None:
    from scraper.browser import browser_manager
    try:
        browser = browser_manager.get_browser()
        for candidate in CANDIDATES:
            probe_site(candidate, browser)
        print(f"\n{'═' * 70}\n  Done\n{'═' * 70}\n")
    finally:
        browser_manager.close()


if __name__ == "__main__":
    run()
