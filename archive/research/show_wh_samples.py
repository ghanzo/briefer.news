"""Pull a handful of real WH articles and write them to research/wh_samples/ for inspection."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import logging
logging.basicConfig(level=logging.WARNING)  # quiet

from scraper.discovery import discover_web_scrape
from scraper.extractor import extract_article
from scraper.browser import browser_manager

SOURCE = {
    "name": "White House — Presidential Actions",
    "type": "web_scrape",
    "url": "https://www.whitehouse.gov/presidential-actions/",
    "category": "geopolitics",
    "tier": 1,
    "extractor": "playwright",
    "link_pattern": "/presidential-actions/2",
}

OUT_DIR = Path(__file__).parent / "wh_samples"
OUT_DIR.mkdir(exist_ok=True)

print("Discovering article URLs...")
stubs = list(discover_web_scrape(SOURCE, delay=0.5))
print(f"Found {len(stubs)} stubs")

# Take the first 5 article-shaped URLs
articles = stubs[:5]

for i, stub in enumerate(articles, 1):
    print(f"\n[{i}/{len(articles)}] Extracting: {stub['title'][:80]}")
    text, method = extract_article(stub["url"], extractor="playwright")
    if not text:
        print(f"  FAILED ({method})")
        continue
    print(f"  OK  ({method}) — {len(text)} chars")

    # Save full article to file
    safe_slug = stub["url"].rstrip("/").split("/")[-1][:80]
    out_file = OUT_DIR / f"{i:02d}_{safe_slug}.txt"
    out_file.write_text(
        f"URL:    {stub['url']}\n"
        f"TITLE:  {stub['title']}\n"
        f"METHOD: {method}\n"
        f"LENGTH: {len(text)} chars\n"
        f"{'=' * 80}\n\n{text}\n",
        encoding="utf-8",
    )
    print(f"  saved: {out_file.name}")

browser_manager.close()
print(f"\nAll samples written to {OUT_DIR}")
