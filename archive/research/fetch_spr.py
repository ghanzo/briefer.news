"""One-off fetch of the SPR article we know about but didn't capture in pipeline."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from scraper.extractor import extract_article
from scraper.browser import browser_manager

URL = "https://www.energy.gov/hgeo/opr/articles/energy-department-issues-rfp-continue-swift-execution-president-trumps-172"

text, method = extract_article(URL, extractor="playwright")
if text:
    out = Path(__file__).parent / "spr_article.txt"
    out.write_text(f"URL: {URL}\nMETHOD: {method}\nLEN: {len(text)}\n\n{text}\n", encoding="utf-8")
    print(f"OK ({method}) — {len(text)} chars")
    print(f"Saved to {out}")
    print(f"\nFirst 800 chars:\n{text[:800]}")
else:
    print(f"FAILED ({method})")

browser_manager.close()
