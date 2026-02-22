"""
discovery.py — Layer 1 of scraping.

Fetches RSS feeds and Google News RSS → returns article stubs (URL, title, date).
Also supports web_scrape type: renders listing pages with Playwright and discovers links.
Does NOT fetch full article text — that is extractor.py's job.
"""

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Generator
from urllib.parse import urljoin, urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; BrieferBot/1.0; +https://briefer.news) "
        "Feedparser/6.0"
    )
}


# ─────────────────────────────────────────────────────────────────────────────
# Hashing helpers
# ─────────────────────────────────────────────────────────────────────────────

def url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().encode()).hexdigest()


def title_hash(title: str) -> str:
    normalized = " ".join(title.lower().split())
    return hashlib.sha256(normalized.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Google News redirect resolver
# ─────────────────────────────────────────────────────────────────────────────

def resolve_redirect(url: str, timeout: int = 10) -> str:
    """Follow redirects (e.g. Google News link shortener) to get the real URL."""
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout, headers=HEADERS) as client:
            resp = client.head(url)
            return str(resp.url)
    except Exception as e:
        logger.debug(f"Could not resolve redirect for {url}: {e}")
        return url


# ─────────────────────────────────────────────────────────────────────────────
# Date parsing
# ─────────────────────────────────────────────────────────────────────────────

def parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# RSS feed fetcher
# ─────────────────────────────────────────────────────────────────────────────

def _extract_text_from_html(html: str) -> str | None:
    """Strip HTML tags and return clean text (used for RSS content:encoded)."""
    try:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "header", "footer",
                         "input", "form", "iframe", "noscript"]):
            tag.decompose()
        lines = [ln.strip() for ln in soup.get_text("\n").splitlines() if ln.strip()]
        text = "\n".join(lines)
        return text if text else None
    except Exception as e:
        logger.debug(f"_extract_text_from_html failed: {e}")
        return None


def fetch_rss(source: dict, delay: float = 0.5) -> Generator[dict, None, None]:
    """
    Fetch one RSS feed and yield article stubs.
    source: a dict from sources.yaml (with id, name, url, category, tier, etc.)

    If the feed entry contains full HTML in content:encoded (e.g. state.gov),
    the text is extracted inline and stored in full_text so main.py can skip
    the URL fetch entirely.
    """
    url = source["url"]
    logger.info(f"Fetching RSS: {source['name']} ({url})")

    try:
        feed = feedparser.parse(url, request_headers=HEADERS)
    except Exception as e:
        logger.error(f"feedparser error for {url}: {e}")
        return

    if feed.bozo and not feed.entries:
        logger.warning(f"Bozo feed (malformed) with no entries: {url}")
        return

    for entry in feed.entries:
        raw_url = entry.get("link", "").strip()
        if not raw_url:
            continue

        # Resolve Google News redirects
        if "news.google.com" in raw_url:
            raw_url = resolve_redirect(raw_url)
            time.sleep(delay)

        raw_title = entry.get("title", "").strip()
        if not raw_title:
            continue

        pub_date = parse_date(
            entry.get("published") or entry.get("updated") or entry.get("dc_date")
        )

        # Check for full article HTML in content:encoded (common in gov RSS feeds like state.gov)
        full_text = None
        extraction_method = None
        if hasattr(entry, "content") and entry.content:
            raw_html = entry.content[0].get("value", "")
            if raw_html:
                text = _extract_text_from_html(raw_html)
                if text and len(text) >= 200:
                    full_text = text
                    extraction_method = "rss_content"

        yield {
            "title":             raw_title,
            "url":               raw_url,
            "url_hash":          url_hash(raw_url),
            "title_hash":        title_hash(raw_title),
            "meta_description":  entry.get("summary", "").strip(),
            "publish_date":      pub_date,
            "source_id":         source.get("db_id"),   # set after DB lookup
            "category":          source.get("category"),
            "tier":              source.get("tier", 2),
            "full_text":         full_text,
            "extraction_method": extraction_method,
            "extractor":         source.get("extractor", "trafilatura"),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Web scrape discovery (Playwright)
# ─────────────────────────────────────────────────────────────────────────────

def discover_web_scrape(source: dict, delay: float = 0.5) -> Generator[dict, None, None]:
    """
    Render source["url"] with Playwright, find all <a href> links on the same
    domain, filter by optional source["link_pattern"], and yield stubs.
    """
    from scraper.browser import playwright_fetch

    listing_url = source["url"]
    link_pattern = source.get("link_pattern", "")
    base_domain = urlparse(listing_url).netloc

    logger.info(f"Web-scrape discovery: {source['name']} ({listing_url})")

    html = playwright_fetch(listing_url)
    if not html:
        logger.warning(f"Playwright returned no HTML for {listing_url}")
        return

    soup = BeautifulSoup(html, "lxml")
    seen_hrefs: set[str] = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:"):
            continue

        # Resolve relative URLs
        abs_url = urljoin(listing_url, href)
        parsed = urlparse(abs_url)

        # Same domain only
        if parsed.netloc != base_domain:
            continue

        # Apply link_pattern filter if specified
        if link_pattern and link_pattern not in parsed.path:
            continue

        # Normalise (drop fragment/query for dedup purposes)
        canonical = abs_url.split("#")[0]
        if canonical in seen_hrefs:
            continue
        seen_hrefs.add(canonical)

        link_text = a_tag.get_text(strip=True) or canonical

        yield {
            "title":             link_text[:500],
            "url":               canonical,
            "url_hash":          url_hash(canonical),
            "title_hash":        title_hash(link_text),
            "meta_description":  "",
            "publish_date":      None,
            "source_id":         source.get("db_id"),
            "category":          source.get("category"),
            "tier":              source.get("tier", 2),
            "full_text":         None,
            "extraction_method": None,
            "extractor":         source.get("extractor", "playwright"),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Main discovery entry point
# ─────────────────────────────────────────────────────────────────────────────

def discover_articles(sources: list[dict], delay: float = 1.0) -> list[dict]:
    """
    Given a list of source configs (from sources.yaml, enriched with db_id),
    fetch all feeds and return deduplicated article stubs.
    """
    seen_url_hashes: set[str] = set()
    stubs: list[dict] = []

    for source in sources:
        if not source.get("active", True):
            continue

        src_type = source.get("type", "rss")

        if src_type in ("rss", "google_news"):
            for stub in fetch_rss(source, delay=delay):
                if stub["url_hash"] not in seen_url_hashes:
                    seen_url_hashes.add(stub["url_hash"])
                    stubs.append(stub)
        elif src_type == "web_scrape":
            for stub in discover_web_scrape(source, delay=delay):
                if stub["url_hash"] not in seen_url_hashes:
                    seen_url_hashes.add(stub["url_hash"])
                    stubs.append(stub)
        else:
            logger.warning(f"Unknown source type '{src_type}' for {source['name']} — skipping")

        time.sleep(delay)

    logger.info(f"Discovery complete: {len(stubs)} unique article stubs from {len(sources)} sources")
    return stubs
