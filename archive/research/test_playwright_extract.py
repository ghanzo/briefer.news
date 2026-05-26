"""Test if Playwright can extract from war.gov (DoD) and gao.gov — both 403 to httpx."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import logging
logging.basicConfig(level=logging.WARNING)

from scraper.extractor import extract_article
from scraper.browser import browser_manager

URLS = [
    ("DoD War.gov", "https://www.war.gov/News/News-Stories/Article/Article/4477864/project-freedom-aims-to-get-thousands-of-commercial-ships-safely-through-strait/"),
    ("DoD War.gov #2", "https://www.war.gov/News/News-Stories/Article/Article/4477804/82nd-airborne-division-ready-to-respond-support-project-freedom-caine-says/"),
    ("GAO", "https://www.gao.gov/products/gao-26-108275"),
]

for label, url in URLS:
    print(f"\n=== {label}: {url[:90]} ===")
    text, method = extract_article(url, extractor="playwright")
    if text:
        print(f"  OK ({method}) — {len(text)} chars")
        print(f"  First 300 chars: {text[:300]}")
    else:
        print(f"  FAILED ({method})")

browser_manager.close()
