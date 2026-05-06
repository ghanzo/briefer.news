"""
Quick batch test of 5 DOE national labs that 403'd in earlier probes.
Test their HTML news landing pages with Playwright (not the RSS endpoints).

Labs: ORNL, ANL, INL, PNNL, AMES (the 5 still-403 after browser-UA retry)
Plus: LANL (was 404 in our probe — try the discover subdomain)

Goal: identify which can be scraped and which are truly blocked.
"""
import sys
from pathlib import Path
from urllib.parse import urlparse
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import logging
logging.basicConfig(level=logging.WARNING)

from scraper.browser import playwright_fetch, browser_manager
from bs4 import BeautifulSoup

CANDIDATES = [
    ("ORNL — Oak Ridge",      "https://www.ornl.gov/news"),
    ("ANL — Argonne",         "https://www.anl.gov/article-list"),
    ("INL — Idaho",           "https://inl.gov/news/"),
    ("PNNL — Pacific Northwest","https://www.pnnl.gov/news-center"),
    ("LANL — Los Alamos",     "https://discover.lanl.gov/news/"),
]

print(f"{'Lab':<32} {'Status':<10} {'Anchors':<10} {'Article-like paths':<10}")
print("-" * 80)

for name, url in CANDIDATES:
    try:
        html = playwright_fetch(url)
        if not html:
            print(f"{name:<32} {'NO HTML':<10}")
            continue
        soup = BeautifulSoup(html, "lxml")
        anchors = soup.find_all("a", href=True)
        # Count anchors that look like article slugs (contain a year or "/news/<something>")
        article_like = []
        for a in anchors:
            h = a["href"]
            path = urlparse(h).path if h.startswith("http") else h
            # heuristic: path with multiple segments that aren't nav
            segs = [s for s in path.split("/") if s]
            if len(segs) >= 2 and any(seg.startswith(("2024", "2025", "2026")) or len(seg) > 30 for seg in segs):
                article_like.append(path)
        title = soup.find("title")
        title_text = title.get_text(strip=True)[:50] if title else "(no title)"
        print(f"{name:<32} {'OK':<10} {len(anchors):<10} {len(article_like):<10} title={title_text}")
        # Show 3 example article-like URLs
        for p in article_like[:3]:
            print(f"    e.g. {p}")
    except Exception as e:
        print(f"{name:<32} {'ERROR':<10} {type(e).__name__}: {str(e)[:60]}")

browser_manager.close()
