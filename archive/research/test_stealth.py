"""
Akamai bypass experiment.

Tests multiple Playwright configurations against war.gov + gao.gov:
  A) plain Playwright (headless) — baseline (we know this fails)
  B) Playwright + tf-playwright-stealth (headless)
  C) Playwright + stealth (non-headless / windowed)
  D) Playwright + stealth + warm-up navigation (visit root first to get cookies)

For each, report HTTP status / page title / first 200 chars of body text.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync, StealthConfig
from bs4 import BeautifulSoup

URLS = [
    ("DoD War.gov / Project Freedom",
     "https://www.war.gov/News/News-Stories/Article/Article/4477864/project-freedom-aims-to-get-thousands-of-commercial-ships-safely-through-strait/"),
    ("GAO product",
     "https://www.gao.gov/products/gao-26-108275"),
]


def fetch_and_summarize(page, url: str, label: str):
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        status = resp.status if resp else "?"
        title = page.title()[:80]
        html = page.content()
        soup = BeautifulSoup(html, "lxml")
        body_text = soup.get_text(" ", strip=True)
        access_denied = "Access Denied" in body_text or "errors.edgesuite.net" in body_text
        first_text = body_text[:200].replace("\n", " ")
        verdict = "BLOCKED" if access_denied else f"OK ({len(body_text)} chars body)"
        print(f"  [{label}] HTTP {status}  title='{title}'  → {verdict}")
        if not access_denied and body_text:
            print(f"           sample: {first_text}")
    except Exception as e:
        print(f"  [{label}] ERROR: {type(e).__name__}: {str(e)[:100]}")


def main():
    print("=" * 100)
    print("A) PLAIN PLAYWRIGHT (headless) — baseline")
    print("=" * 100)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        page = ctx.new_page()
        for label, url in URLS:
            fetch_and_summarize(page, url, label)
        browser.close()

    print("\n" + "=" * 100)
    print("B) PLAYWRIGHT + STEALTH (headless)")
    print("=" * 100)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        page = ctx.new_page()
        stealth_sync(page)
        for label, url in URLS:
            fetch_and_summarize(page, url, label)
        browser.close()

    print("\n" + "=" * 100)
    print("C) PLAYWRIGHT + STEALTH (NON-HEADLESS — window will appear briefly)")
    print("=" * 100)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        page = ctx.new_page()
        stealth_sync(page)
        for label, url in URLS:
            fetch_and_summarize(page, url, label)
        browser.close()

    print("\n" + "=" * 100)
    print("D) PLAYWRIGHT + STEALTH (NON-HEADLESS) + WARM-UP NAVIGATION")
    print("=" * 100)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        page = ctx.new_page()
        stealth_sync(page)
        # warm-up: visit root first to get session cookies
        for warm_url in ["https://www.war.gov/", "https://www.gao.gov/"]:
            try:
                print(f"  warmup: {warm_url}")
                page.goto(warm_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)
            except Exception as e:
                print(f"  warmup failed: {e}")
        for label, url in URLS:
            fetch_and_summarize(page, url, label)
        browser.close()


if __name__ == "__main__":
    main()
