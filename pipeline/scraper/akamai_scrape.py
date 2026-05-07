"""
Akamai-protected source scraper.

Runs AFTER the main pipeline scrape. Reads from
pipeline/config/akamai_sources.yaml. For each active source:

  1. Discover article URLs via type-specific method (dnn_articlecs, rss_curl_cffi, html_curl_cffi)
  2. For each new URL (not already in DB), extract body via akamai_bypass.akamai_extract
  3. Save to articles table using the same SQLAlchemy models as the main pipeline
  4. On block detection, abort that source and move on to the next

Usage:
    python -m scraper.akamai_scrape                    # all active sources
    python -m scraper.akamai_scrape --source war.gov   # single source by domain
    python -m scraper.akamai_scrape --dry-run          # discover + extract but don't save
    python -m scraper.akamai_scrape --limit 5          # cap articles per source

Or via main.py:
    python main.py --akamai-only
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import yaml
import feedparser
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError

# Ensure pipeline package importable when run as -m or as script
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from db.models import (  # noqa: E402
    get_engine,
    get_session,
    Source,
    Article,
    ScrapeRun,
)
from scraper.akamai_bypass import (  # noqa: E402
    akamai_fetch,
    akamai_extract,
    akamai_discover_links,
    akamai_discover_via_dnn_api,
)

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _load_sources_config() -> list[dict]:
    config_path = _HERE.parent / "config" / "akamai_sources.yaml"
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("sources", [])


def _is_block_signal(reason: str) -> bool:
    """True if the failure looks like an Akamai block (vs transient error)."""
    s = reason.lower()
    return any(k in s for k in ["403", "access denied", "blocked", "reference #"])


def _ensure_source_row(session, cfg: dict) -> Optional[int]:
    """Upsert source row, return its DB id."""
    source = session.query(Source).filter_by(name=cfg["name"]).first()
    if source:
        return source.id
    source = Source(
        name=cfg["name"],
        type="web_scrape",
        url=cfg.get("api_url") or cfg.get("rss_url") or cfg.get("listing_url"),
        category=cfg.get("category", "defense"),
        tier=cfg.get("tier", 2),
        extractor="akamai",
        active=cfg.get("active", True),
    )
    session.add(source)
    session.flush()
    logger.info(f"Created source row: {source.name} (id={source.id})")
    return source.id


# ── Discovery dispatchers ────────────────────────────────────────────────────

def _discover_dnn_articlecs(cfg: dict) -> list[dict]:
    api_url = cfg.get("api_url")
    if not api_url or "TBD" in api_url:
        logger.info(f"  skipping {cfg['name']}: api_url has placeholder 'TBD' — moduleID not yet discovered")
        return []
    cards = akamai_discover_via_dnn_api(api_url)
    logger.info(f"  DNN ArticleCS discovery returned {len(cards)} cards")
    return cards


def _discover_rss_curl_cffi(cfg: dict) -> list[dict]:
    rss_url = cfg["rss_url"]
    body = akamai_fetch(rss_url)
    if not body:
        return []
    feed = feedparser.parse(body)
    cards = []
    for entry in feed.entries[:30]:
        url = entry.get("link")
        if not url:
            continue
        cards.append({
            "url": url,
            "title": entry.get("title", "").strip(),
            "publish_date": entry.get("published") or entry.get("updated"),
            "image_url": None,
        })
    logger.info(f"  RSS discovery returned {len(cards)} entries")
    return cards


def _discover_html_curl_cffi(cfg: dict) -> list[dict]:
    listing_url = cfg["listing_url"]
    pattern = cfg.get("link_pattern", "")
    urls = akamai_discover_links(listing_url, pattern)
    cards = [{"url": u, "title": "", "publish_date": None, "image_url": None} for u in urls]
    logger.info(f"  HTML discovery returned {len(cards)} candidate URLs")
    return cards


_DISCOVERY = {
    "dnn_articlecs": _discover_dnn_articlecs,
    "rss_curl_cffi": _discover_rss_curl_cffi,
    "html_curl_cffi": _discover_html_curl_cffi,
}


# ── Per-source scrape ────────────────────────────────────────────────────────

def scrape_one_source(cfg: dict, session, run: ScrapeRun, dry_run: bool, limit: int = 0) -> dict:
    """
    Scrape a single Akamai source. Returns stats dict.

    Aborts on consecutive block signals (likely IP/session flag triggered).
    """
    stats = {
        "name": cfg["name"],
        "discovered": 0,
        "extracted": 0,
        "skipped_existing": 0,
        "failed": 0,
        "blocked": False,
    }

    if not cfg.get("active", True):
        logger.info(f"[skip] {cfg['name']}: not active")
        return stats

    logger.info(f"[start] {cfg['name']} ({cfg.get('discovery_type', 'unknown')})")

    discover_fn = _DISCOVERY.get(cfg.get("discovery_type"))
    if not discover_fn:
        logger.warning(f"  unknown discovery_type for {cfg['name']}: {cfg.get('discovery_type')}")
        return stats

    try:
        cards = discover_fn(cfg)
    except Exception as e:
        logger.warning(f"  discovery error: {e}")
        stats["blocked"] = True
        return stats

    stats["discovered"] = len(cards)
    if not cards:
        return stats

    source_id = _ensure_source_row(session, cfg)
    session.commit()

    consecutive_blocks = 0
    for i, card in enumerate(cards):
        if limit > 0 and stats["extracted"] >= limit:
            logger.info(f"  hit per-source limit of {limit}; stopping")
            break

        url = card["url"]
        url_h = _url_hash(url)

        # Skip if already in DB
        if session.query(Article).filter_by(url_hash=url_h).first():
            stats["skipped_existing"] += 1
            continue

        # Extract
        text, method = akamai_extract(url)
        if not text:
            stats["failed"] += 1
            consecutive_blocks += 1
            logger.warning(f"  failed to extract {url} (method={method})")
            if consecutive_blocks >= 3:
                logger.warning(f"  3 consecutive failures — aborting source {cfg['name']} (likely flagged)")
                stats["blocked"] = True
                break
            continue

        consecutive_blocks = 0  # reset on success

        if dry_run:
            logger.info(f"  [dry-run] would save: {card.get('title', '')[:80]} ({len(text)} chars)")
            stats["extracted"] += 1
            continue

        # Persist
        publish_date = None
        raw_pd = card.get("publish_date")
        if raw_pd:
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%a, %d %b %Y %H:%M:%S %Z"):
                try:
                    publish_date = datetime.strptime(raw_pd, fmt)
                    break
                except (ValueError, TypeError):
                    continue

        article = Article(
            source_id=source_id,
            title=card.get("title", "")[:500] or url[:500],
            url=url,
            url_hash=url_h,
            full_text=text,
            extraction_method=method,
            extraction_failed=False,
            publish_date=publish_date,
            language="en",
            raw_metadata={
                "image_url": card.get("image_url"),
                "discovery_type": cfg.get("discovery_type"),
            },
        )
        try:
            session.add(article)
            session.commit()
            stats["extracted"] += 1
            run.articles_extracted += 1
            session.commit()
            logger.info(f"  [{stats['extracted']}] saved: {card.get('title', url)[:80]} ({len(text)} chars, {method})")
        except IntegrityError:
            session.rollback()
            stats["skipped_existing"] += 1

    logger.info(
        f"[done]  {cfg['name']} — "
        f"discovered={stats['discovered']}, extracted={stats['extracted']}, "
        f"existing={stats['skipped_existing']}, failed={stats['failed']}, "
        f"blocked={stats['blocked']}"
    )
    return stats


# ── Top-level orchestrator ───────────────────────────────────────────────────

def run_akamai_scrape(only_domain: Optional[str] = None, dry_run: bool = False, limit: int = 0) -> list[dict]:
    """Run akamai-protected scrape across all active sources. Returns per-source stats."""
    logger.info("═" * 60)
    logger.info(f"AKAMAI SCRAPE — {datetime.utcnow().isoformat()}")

    sources = _load_sources_config()
    if only_domain:
        sources = [s for s in sources if s.get("domain") == only_domain]
        if not sources:
            logger.warning(f"No source with domain={only_domain}")
            return []

    engine = get_engine()
    session = get_session(engine)

    run = ScrapeRun()
    session.add(run)
    session.commit()

    all_stats = []
    try:
        for cfg in sources:
            stats = scrape_one_source(cfg, session, run, dry_run=dry_run, limit=limit)
            all_stats.append(stats)
            run.articles_discovered = (run.articles_discovered or 0) + stats["discovered"]
            session.commit()

        run.completed_at = datetime.utcnow()
        run.status = "completed"
        session.commit()
    except Exception as e:
        logger.exception(f"akamai scrape failed: {e}")
        run.status = "failed"
        run.error_message = str(e)
        run.completed_at = datetime.utcnow()
        session.commit()
        raise
    finally:
        session.close()

    # Final summary
    logger.info("═" * 60)
    logger.info("AKAMAI SCRAPE SUMMARY")
    for s in all_stats:
        flag = "BLOCKED" if s["blocked"] else "ok"
        logger.info(
            f"  {s['name']:42s}  d={s['discovered']:>3}  ext={s['extracted']:>3}  "
            f"existing={s['skipped_existing']:>3}  failed={s['failed']:>3}  [{flag}]"
        )
    return all_stats


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    parser = argparse.ArgumentParser(description="Akamai-protected source scraper")
    parser.add_argument("--source", type=str, default=None,
                        help="Limit to a single source by domain (e.g. war.gov)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Discover and extract but do not write to DB")
    parser.add_argument("--limit", type=int, default=0,
                        help="Cap articles per source (0 = unlimited)")
    args = parser.parse_args()

    run_akamai_scrape(only_domain=args.source, dry_run=args.dry_run, limit=args.limit)
