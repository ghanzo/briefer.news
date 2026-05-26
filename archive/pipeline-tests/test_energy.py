"""
test_energy.py — Standalone test for energy.gov web_scrape + playwright extraction.

Tests two things:
  1. discover_web_scrape() — renders energy.gov/newsroom, finds article links
  2. extract_article(..., extractor="playwright") — fetches + extracts one article

Usage:
  python test_energy.py
  python test_energy.py --limit 3   # extract text from up to 3 articles
"""

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

os.makedirs("logs", exist_ok=True)
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("test_energy")

SOURCE = {
    "name": "Department of Energy — Newsroom",
    "type": "web_scrape",
    "url": "https://www.energy.gov/newsroom",
    "link_pattern": "/articles/",
    "category": "energy",
    "tier": 1,
    "extractor": "playwright",
    "db_id": None,
    "active": True,
}


def run(limit: int = 2) -> None:
    from scraper.discovery import discover_web_scrape
    from scraper.extractor import extract_article
    from scraper.browser import browser_manager

    try:
        # ── Step 1: Discovery ─────────────────────────────────────────────────
        logger.info("=" * 60)
        logger.info("STEP 1 — discover_web_scrape(energy.gov/newsroom)")
        stubs = list(discover_web_scrape(SOURCE))

        if not stubs:
            logger.error("No links discovered — check Playwright install and energy.gov connectivity")
            return

        logger.info(f"Found {len(stubs)} article links")
        for i, s in enumerate(stubs[:5]):
            logger.info(f"  [{i+1}] {s['url']}")
        if len(stubs) > 5:
            logger.info(f"  ... and {len(stubs) - 5} more")

        # ── Step 2: Extraction ────────────────────────────────────────────────
        logger.info("=" * 60)
        logger.info(f"STEP 2 — extract_article() via playwright (limit={limit})")

        successes = 0
        failures = 0
        for stub in stubs[:limit]:
            logger.info(f"\nExtracting: {stub['url']}")
            text, method = extract_article(stub["url"], extractor="playwright")
            if text:
                successes += 1
                logger.info(f"  ✓  method={method}  chars={len(text)}")
                logger.info(f"  preview: {text[:200].replace(chr(10), ' ')!r}")
            else:
                failures += 1
                logger.warning(f"  ✗  method={method}")

        logger.info("=" * 60)
        logger.info(f"Done — {successes} extracted, {failures} failed out of {limit} attempted")

    finally:
        browser_manager.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=2, help="Number of articles to extract (default 2)")
    args = parser.parse_args()
    run(limit=args.limit)
