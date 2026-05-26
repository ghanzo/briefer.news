"""
test_statedept.py — Quick test: scrape State Dept RSS feeds only.

Fetches a handful of State Dept feeds, extracts article text,
stores in PostgreSQL. No AI, no Google News, no redirects.

Usage:
  python test_statedept.py           # scrape all State Dept feeds, up to 20 articles
  python test_statedept.py --limit 5 # stop after 5 articles
"""

import argparse
import hashlib
import logging
import os
import sys
from datetime import datetime, timezone

import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

os.makedirs("logs", exist_ok=True)
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("test_statedept")

from db.models import get_engine, get_session, Source, Article

# ── State Dept feeds only ─────────────────────────────────────────────────────
STATE_DEPT_FEEDS = [
    ("State Dept — Press Releases",        "https://www.state.gov/rss-feed/press-releases/feed/"),
    ("State Dept — Secretary's Remarks",   "https://www.state.gov/rss-feed/secretarys-remarks/feed/"),
    ("State Dept — East Asia & Pacific",   "https://www.state.gov/rss-feed/east-asia-and-the-pacific/feed/"),
    ("State Dept — Near East",             "https://www.state.gov/rss-feed/near-east/feed/"),
    ("State Dept — Europe & Eurasia",      "https://www.state.gov/rss-feed/europe-and-eurasia/feed/"),
    ("State Dept — Press Briefings",       "https://www.state.gov/rss-feed/department-press-briefings/feed/"),
    ("State Dept — Arms Control",          "https://www.state.gov/rss-feed/arms-control-and-international-security/feed/"),
    ("State Dept — Western Hemisphere",    "https://www.state.gov/rss-feed/western-hemisphere/feed/"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BrieferBot/1.0; +https://briefer.news)"
}


def url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().encode()).hexdigest()


def parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def extract_text_from_entry(entry) -> tuple[str | None, str]:
    """
    Extract article text from an RSS entry.
    State Dept embeds full HTML content in the RSS entry itself —
    no need to fetch the article page.
    """
    # feedparser stores content:encoded in entry.content[0].value
    raw_html = None
    if hasattr(entry, "content") and entry.content:
        raw_html = entry.content[0].get("value", "")
    if not raw_html:
        raw_html = entry.get("summary", "")

    if not raw_html:
        return None, "no_rss_content"

    # Clean HTML with BeautifulSoup
    try:
        soup = BeautifulSoup(raw_html, "lxml")
        for tag in soup(["script", "style", "nav", "header", "footer",
                         "input", "form", "iframe", "noscript"]):
            tag.decompose()
        lines = [l.strip() for l in soup.get_text("\n").splitlines() if l.strip()]
        text = "\n".join(lines)
        if len(text) > 100:
            return text, "rss_content"
    except Exception as e:
        logger.warning(f"RSS content extraction failed: {e}")

    return None, "extraction_failed"


def get_or_create_source(session, name: str, url: str) -> Source:
    source = session.query(Source).filter_by(name=name).first()
    if not source:
        source = Source(
            name=name, type="rss", url=url,
            category="geopolitics", tier=1, active=True,
        )
        session.add(source)
        session.commit()
        logger.info(f"Created source: {name}")
    return source


def run(limit: int = 20) -> None:
    engine  = get_engine()
    session = get_session(engine)
    saved   = 0

    for feed_name, feed_url in STATE_DEPT_FEEDS:
        if saved >= limit:
            break

        logger.info(f"Fetching: {feed_name}")
        source = get_or_create_source(session, feed_name, feed_url)

        try:
            feed = feedparser.parse(feed_url, request_headers=HEADERS)
        except Exception as e:
            logger.error(f"feedparser error on {feed_url}: {e}")
            continue

        if not feed.entries:
            logger.warning(f"No entries in feed: {feed_url}")
            continue

        for entry in feed.entries:
            if saved >= limit:
                break

            art_url = entry.get("link", "").strip()
            title   = entry.get("title", "").strip()
            if not art_url or not title:
                continue

            uhash = url_hash(art_url)

            # Skip if already in DB
            if session.query(Article).filter_by(url_hash=uhash).first():
                logger.debug(f"Already in DB, skipping: {title[:60]}")
                continue

            logger.info(f"Extracting [{saved+1}/{limit}]: {title[:70]}")
            text, method = extract_text_from_entry(entry)

            article = Article(
                source_id=source.id,
                title=title,
                url=art_url,
                url_hash=uhash,
                title_hash=hashlib.sha256(title.lower().encode()).hexdigest(),
                meta_description=entry.get("summary", "")[:500],
                publish_date=parse_date(entry.get("published")),
                full_text=text,
                extraction_method=method,
                extraction_failed=(text is None),
                raw_metadata={},
                image_urls=[],
                keywords=[],
            )

            try:
                session.add(article)
                session.commit()
                saved += 1
                status = f"✓ {method}" if text else "✗ extraction failed"
                logger.info(f"  Saved — {status} — {len(text) if text else 0} chars")
            except IntegrityError:
                session.rollback()

    session.close()
    logger.info(f"Done — {saved} articles saved to DB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    run(limit=args.limit)
