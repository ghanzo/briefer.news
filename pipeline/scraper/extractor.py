"""
extractor.py — Layer 2 of scraping.

Given a URL, fetch the full article text.
Tries extractors in order: trafilatura → beautifulsoup fallback → give up.
"""

import logging
from typing import Optional

import httpx
import trafilatura
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

MIN_TEXT_LENGTH = 200  # characters — below this we consider extraction failed


# ─────────────────────────────────────────────────────────────────────────────
# HTTP fetch
# ─────────────────────────────────────────────────────────────────────────────

def fetch_html(url: str, timeout: int = 15) -> Optional[str]:
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            headers=HEADERS,
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.text
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP {e.response.status_code} for {url}")
        return None
    except Exception as e:
        logger.warning(f"Fetch failed for {url}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Extractor 1 — trafilatura (best for most sites)
# ─────────────────────────────────────────────────────────────────────────────

def _try_trafilatura(html: str, url: str) -> Optional[str]:
    try:
        text = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
            favor_precision=True,
            deduplicate=True,
        )
        return text if text and len(text) >= MIN_TEXT_LENGTH else None
    except Exception as e:
        logger.debug(f"trafilatura failed for {url}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Extractor 2 — BeautifulSoup fallback (strips tags, grabs body text)
# ─────────────────────────────────────────────────────────────────────────────

def _try_beautifulsoup(html: str, url: str) -> Optional[str]:
    try:
        soup = BeautifulSoup(html, "lxml")

        # Remove noise
        for tag in soup(["script", "style", "nav", "header", "footer",
                          "aside", "form", "iframe", "noscript"]):
            tag.decompose()

        # Prefer <article> if present, else <main>, else <body>
        container = (
            soup.find("article")
            or soup.find("main")
            or soup.find("body")
        )
        if not container:
            return None

        text = container.get_text(separator="\n", strip=True)
        # Collapse excessive blank lines
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        text = "\n".join(lines)
        return text if len(text) >= MIN_TEXT_LENGTH else None
    except Exception as e:
        logger.debug(f"BeautifulSoup fallback failed for {url}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def extract_article(url: str, extractor: str = "trafilatura") -> tuple[Optional[str], str]:
    """
    Attempt to extract full article text from a URL.

    Args:
        url:       Article URL to fetch and extract.
        extractor: 'trafilatura' (default) or 'playwright'.
                   playwright renders JS then runs the same trafilatura→BS4 chain.

    Returns:
        (text, method)  where method is one of:
            'trafilatura' | 'beautifulsoup' |
            'playwright_trafilatura' | 'playwright_beautifulsoup' |
            'fetch_failed' | 'extraction_failed'
    """
    if extractor == "playwright":
        from scraper.browser import playwright_fetch
        html = playwright_fetch(url)
        if not html:
            return None, "fetch_failed"
        text = _try_trafilatura(html, url)
        if text:
            return text, "playwright_trafilatura"
        text = _try_beautifulsoup(html, url)
        if text:
            return text, "playwright_beautifulsoup"
        logger.warning(f"All extractors failed (playwright) for {url}")
        return None, "extraction_failed"

    # Default: httpx fetch → trafilatura → BS4
    html = fetch_html(url)
    if not html:
        return None, "fetch_failed"

    text = _try_trafilatura(html, url)
    if text:
        return text, "trafilatura"

    text = _try_beautifulsoup(html, url)
    if text:
        return text, "beautifulsoup"

    logger.warning(f"All extractors failed for {url}")
    return None, "extraction_failed"
