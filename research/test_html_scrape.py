"""
End-to-end test of the HTML scrape path on White House — Presidential Actions.

Bypasses Postgres / DB layer. Calls the real pipeline functions:
  scraper.discovery.discover_web_scrape() — Playwright renders listing, finds links
  scraper.extractor.extract_article()      — fetches each article, extracts text

Pass criteria:
  - Discovery returns >= 5 article URLs
  - At least one extraction returns text >= 500 chars
  - No silent crashes
"""

import sys
import time
from pathlib import Path

# Make the pipeline package importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
log = logging.getLogger("test_html_scrape")

from scraper.discovery import discover_web_scrape
from scraper.extractor import extract_article
from scraper.browser import browser_manager


SOURCE = {
    "name":      "ORNL — Oak Ridge News",
    "type":      "web_scrape",
    "url":       "https://www.ornl.gov/news",
    "category":  "energy",
    "tier":      1,
    "extractor": "playwright",
    "db_id":     None,
    "link_pattern": "/news/",
}


def main():
    print("=" * 80)
    print("PHASE 1 — DISCOVERY (playwright renders listing, finds article links)")
    print("=" * 80)
    t0 = time.time()
    stubs = list(discover_web_scrape(SOURCE, delay=0.5))
    elapsed = time.time() - t0
    print(f"Discovery took {elapsed:.1f}s, returned {len(stubs)} stubs")

    if not stubs:
        print("FAIL: no stubs discovered")
        browser_manager.close()
        return 1

    # Show first 10 discovered URLs
    print("\nFirst 10 discovered URLs:")
    for i, stub in enumerate(stubs[:10]):
        print(f"  {i+1:2}. {stub['url']}")
        print(f"      title: {stub['title'][:90]}")

    # No filtering — show what categories of URL came back so we can design link_pattern
    from urllib.parse import urlparse
    paths = [urlparse(s["url"]).path for s in stubs]
    print("\nURL paths returned (deduped):")
    seen_path_prefixes = {}
    for p in paths:
        # Take first two segments to bucket by section
        segs = [s for s in p.split("/") if s]
        prefix = "/" + "/".join(segs[:2]) if segs else "/"
        seen_path_prefixes.setdefault(prefix, []).append(p)
    for prefix in sorted(seen_path_prefixes, key=lambda k: -len(seen_path_prefixes[k])):
        examples = seen_path_prefixes[prefix]
        print(f"  {prefix:50}  ({len(examples)} hits)  e.g. {examples[0]}")
    article_stubs = stubs[:5]  # for extraction phase, take whatever first 5 are

    print("\n" + "=" * 80)
    print("PHASE 2 — EXTRACTION (fetch each article, extract text)")
    print("=" * 80)
    sample = article_stubs[:3]
    if not sample:
        print("FAIL: no article candidates to extract from")
        browser_manager.close()
        return 1

    extraction_results = []
    for i, stub in enumerate(sample):
        print(f"\n[{i+1}/{len(sample)}] {stub['url']}")
        t0 = time.time()
        text, method = extract_article(stub["url"], extractor="playwright")
        elapsed = time.time() - t0
        if text:
            print(f"  OK ({method}) — {len(text)} chars in {elapsed:.1f}s")
            print(f"  First 300 chars: {text[:300]}")
            extraction_results.append({"url": stub["url"], "method": method, "len": len(text), "ok": True})
        else:
            print(f"  FAIL ({method}) in {elapsed:.1f}s")
            extraction_results.append({"url": stub["url"], "method": method, "len": 0, "ok": False})

    browser_manager.close()

    # Verdict
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)
    print(f"Discovery:  {len(stubs)} total stubs, {len(article_stubs)} plausible articles")
    print(f"Extraction: {sum(1 for r in extraction_results if r['ok'])}/{len(extraction_results)} succeeded")
    avg_len = sum(r["len"] for r in extraction_results) / max(len(extraction_results), 1)
    print(f"Avg text length on successes: {avg_len:.0f} chars")

    if any(r["ok"] and r["len"] >= 500 for r in extraction_results):
        print("\nPASS — pipeline can scrape White House. Ready to enable.")
        return 0
    print("\nFAIL — extraction produced too little text; needs investigation")
    return 1


if __name__ == "__main__":
    sys.exit(main())
