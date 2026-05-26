"""Debug ARPA-E lazy-load page. Try scroll-to-bottom + extended wait.

If article URLs appear after scrolling, the fix is to extend playwright_fetch().
If not, the page genuinely requires interaction we can't simulate.
"""
import sys
from pathlib import Path
from urllib.parse import urlparse
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

URL = "https://arpa-e.energy.gov/news-and-events/news-and-insights"

print(f"Loading {URL}")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL, wait_until="networkidle", timeout=60000)
    print("Initial networkidle reached")

    # Capture initial state
    initial_html = page.content()
    initial_links = len(BeautifulSoup(initial_html, "lxml").find_all("a", href=True))
    print(f"Initial: {initial_links} <a> tags, {len(initial_html)} chars")

    # Scroll to bottom progressively
    print("\nScrolling to bottom (5x in steps)...")
    for i in range(5):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)  # 2s per scroll step
        h = page.evaluate("document.body.scrollHeight")
        n_links = page.evaluate("document.querySelectorAll('a').length")
        print(f"  step {i+1}: scrollHeight={h}, total <a>={n_links}")

    # Try clicking any "Load more" / "View more" button
    for label in ["Load more", "View more", "Show more", "More"]:
        try:
            btn = page.get_by_text(label, exact=False).first
            if btn.is_visible(timeout=1000):
                print(f"\nFound '{label}' button — clicking 3 times")
                for _ in range(3):
                    btn.click(timeout=3000)
                    page.wait_for_timeout(1500)
                break
        except Exception:
            pass

    # Final HTML
    final_html = page.content()
    soup = BeautifulSoup(final_html, "lxml")
    all_anchors = soup.find_all("a", href=True)
    print(f"\nFinal: {len(all_anchors)} <a> tags, {len(final_html)} chars")

    # Bucket all links
    buckets = Counter()
    examples = {}
    for a in all_anchors:
        href = a["href"]
        if href.startswith("/") or "arpa-e.energy.gov" in href:
            path = urlparse(href).path if href.startswith("http") else href.split("?")[0].split("#")[0]
            segs = [s for s in path.split("/") if s]
            prefix = "/" + "/".join(segs[:3]) if segs else "/"
            buckets[prefix] += 1
            examples.setdefault(prefix, path)

    print("\nLink path buckets (top 30 by count):")
    for prefix, count in buckets.most_common(30):
        print(f"  {count:>3}  {prefix:<60}  e.g. {examples[prefix]}")

    # Save full HTML
    out = Path(__file__).parent / "arpae_debug.html"
    out.write_text(final_html, encoding="utf-8")
    print(f"\nFull HTML saved to: {out}")

    browser.close()
