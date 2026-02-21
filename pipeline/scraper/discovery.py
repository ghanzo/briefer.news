"""
discovery.py — Layer 1 of scraping.

Fetches RSS feeds and Google News RSS → returns article stubs (URL, title, date).
Does NOT fetch full article text — that is extractor.py's job.
"""

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Generator

import feedparser
import httpx
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

def fetch_rss(source: dict, delay: float = 0.5) -> Generator[dict, None, None]:
    """
    Fetch one RSS feed and yield article stubs.
    source: a dict from sources.yaml (with id, name, url, category, tier, etc.)
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

        yield {
            "title":            raw_title,
            "url":              raw_url,
            "url_hash":         url_hash(raw_url),
            "title_hash":       title_hash(raw_title),
            "meta_description": entry.get("summary", "").strip(),
            "publish_date":     pub_date,
            "source_id":        source.get("db_id"),   # set after DB lookup
            "category":         source.get("category"),
            "tier":             source.get("tier", 2),
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
        else:
            logger.warning(f"Unknown source type '{src_type}' for {source['name']} — skipping")

        time.sleep(delay)

    logger.info(f"Discovery complete: {len(stubs)} unique article stubs from {len(sources)} sources")
    return stubs
