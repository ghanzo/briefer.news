"""Verify stealth works for GAO with REAL URLs from their RSS feed."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from bs4 import BeautifulSoup

REAL_URLS = [
    ("DoD War.gov", "https://www.war.gov/News/News-Stories/Article/Article/4477864/project-freedom-aims-to-get-thousands-of-commercial-ships-safely-through-strait/"),
    ("GAO real #1", "https://www.gao.gov/products/gao-26-107572"),
    ("GAO real #2", "https://www.gao.gov/products/gao-26-107957"),  # Nuclear Waste Cleanup — lens-relevant!
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    page = ctx.new_page()
    stealth_sync(page)

    for label, url in REAL_URLS:
        print(f"\n{label}: {url}")
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            status = resp.status
            html = page.content()
            soup = BeautifulSoup(html, "lxml")
            text = soup.get_text(" ", strip=True)
            blocked = "Access Denied" in text and "errors.edgesuite.net" in text
            title = page.title()[:80]
            print(f"  HTTP {status} | title: '{title}' | body: {len(text)} chars | blocked: {blocked}")
            if not blocked:
                # Get the article content area if possible
                main = soup.find("main") or soup.find("article") or soup
                clean = main.get_text(" ", strip=True)
                print(f"  First 400 chars: {clean[:400]}")
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")

    browser.close()
