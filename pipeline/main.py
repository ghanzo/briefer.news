"""
main.py — Scrape orchestrator.

Discovers + extracts government-source articles into PostgreSQL. Three scrape
modes, each driven by daily.sh as a separate parallel job:

  --scrape-only   RSS / web sources       (config/sources.yaml)
  --akamai-only   Akamai-protected gov     (config/akamai_sources.yaml)
  --china-only    Chinese-government        (config/china_sources.yaml)

The brief itself is produced downstream by the synth scripts (synthesize.sh /
synthesize_china.sh) reading from this article store — NOT here.

  python main.py --scrape-only             # RSS/web scrape
  python main.py --scrape-only --limit 20  # cap at 20 (testing)
  python main.py --akamai-only --dry-run   # discover only, no DB writes

The legacy Stage-2 "process" path (per-article Grok/Gemini/Claude summarizers +
the Jinja build_site) was removed 2026-06-01 — it was never invoked in
production. Archived at archive/pipeline/ if ever needed.
"""

import argparse
import logging
import os
import sys
from datetime import date, datetime

import yaml
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

try:
    from langdetect import detect as _langdetect_detect, DetectorFactory
    DetectorFactory.seed = 0   # make detection deterministic
    _LANGDETECT_AVAILABLE = True
except ImportError:
    _LANGDETECT_AVAILABLE = False


def detect_language(text: str) -> str | None:
    """Return ISO 639-1 language code for text, or None if detection fails."""
    if not _LANGDETECT_AVAILABLE or not text:
        return None
    try:
        return _langdetect_detect(text[:500])
    except Exception:
        return None

# ── Logging setup (logs dir must exist before basicConfig) ───────────────────
os.makedirs("logs", exist_ok=True)
os.makedirs("output", exist_ok=True)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/pipeline.log", mode="a"),
    ],
)
logger = logging.getLogger("main")

# ── Imports that need logging set up first ───────────────────────────────────
from db.models import (
    get_engine, get_session,
    Source, Article, ArticleSummary, DailyBriefing, CategorySummary,
    ScrapeRun, RejectedUrlHash, BriefingOutput,
)
from scraper.discovery import discover_articles
from scraper.extractor import extract_article
from processor.filter import create_groq_client, is_filter_enabled, filter_stub, _load_filter_criteria

TOP_ARTICLES_COUNT = int(os.getenv("TOP_ARTICLES_COUNT", "5"))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_sources_config() -> list[dict]:
    config_path = os.path.join(os.path.dirname(__file__), "config", "sources.yaml")
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("sources", [])


def sync_sources(session, sources_config: list[dict]) -> dict[str, int]:
    """Upsert sources from YAML into DB. Returns name → db_id mapping."""
    name_to_id: dict[str, int] = {}
    for cfg in sources_config:
        source = session.query(Source).filter_by(name=cfg["name"]).first()
        if not source:
            source = Source(
                name=cfg["name"],
                type=cfg["type"],
                url=cfg.get("url"),
                category=cfg["category"],
                tier=cfg.get("tier", 2),
                extractor=cfg.get("extractor", "trafilatura"),
                active=cfg.get("active", True),
            )
            session.add(source)
            session.flush()
            logger.info(f"New source added: {source.name}")
        name_to_id[cfg["name"]] = source.id
    session.commit()
    return name_to_id


def save_article_stub(session, stub: dict) -> Article | None:
    """Insert article stub. Returns None if URL already in DB."""
    if session.query(Article).filter_by(url_hash=stub["url_hash"]).first():
        return None
    article = Article(
        source_id=stub.get("source_id"),
        title=stub["title"],
        url=stub["url"],
        url_hash=stub["url_hash"],
        title_hash=stub.get("title_hash"),
        meta_description=stub.get("meta_description", ""),
        publish_date=stub.get("publish_date"),
        language=stub.get("language"),   # known from source config; may be filled by langdetect later
        raw_metadata={},
    )
    try:
        session.add(article)
        session.commit()
        return article
    except IntegrityError:
        session.rollback()
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — Scrape
# ─────────────────────────────────────────────────────────────────────────────

def run_scrape(limit: int = 0) -> list[Article]:
    """
    Discover + filter + extract articles from all active sources.
    Stores results in PostgreSQL. Returns list of newly extracted Article objects.
    No API key required for scraping. GROQ_API_KEY needed for Stage 1 filter.

    limit: if > 0, stop extracting after this many new articles (useful for testing)
    """
    logger.info("═" * 60)
    logger.info(f"STAGE 1 — SCRAPE — {datetime.utcnow().isoformat()}")

    engine  = get_engine()
    session = get_session(engine)

    run = ScrapeRun()
    session.add(run)
    session.commit()

    # Set up Groq filter if enabled
    groq_client    = create_groq_client()
    filter_enabled = is_filter_enabled()
    filter_active  = groq_client is not None and filter_enabled
    filter_criteria = _load_filter_criteria() if filter_active else None

    if filter_active:
        logger.info("Groq Stage 1 filter: ACTIVE")
    elif groq_client and not filter_enabled:
        logger.info("Groq Stage 1 filter: shadow mode (GROQ_FILTER_ENABLED=false — logging only)")
    else:
        logger.info("Groq Stage 1 filter: disabled (no GROQ_API_KEY)")

    new_articles: list[Article] = []

    try:
        sources_config = load_sources_config()
        name_to_id     = sync_sources(session, sources_config)

        active_sources = [
            {**cfg, "db_id": name_to_id.get(cfg["name"])}
            for cfg in sources_config
            if cfg.get("active", True)
        ]

        logger.info(f"Discovering from {len(active_sources)} active sources…")
        stubs = discover_articles(active_sources)
        run.articles_discovered = len(stubs)
        session.commit()
        logger.info(f"Discovered {len(stubs)} article stubs")

        for stub in stubs:
            if limit > 0 and len(new_articles) >= limit:
                logger.info(f"Reached extraction limit of {limit} — stopping early")
                break

            url_hash = stub["url_hash"]

            # Skip if already in rejected_url_hashes
            if session.query(RejectedUrlHash).filter_by(url_hash=url_hash).first():
                continue

            # Run Groq filter (on title + meta_description, before any HTTP fetch)
            if groq_client:
                filter_result = filter_stub(groq_client, stub, criteria=filter_criteria)
                if not filter_result["keep"]:
                    reason = filter_result["reason"]
                    logger.info(f"Filter REJECT: '{stub['title'][:60]}' — {reason}")
                    if filter_active:
                        # Active mode: save to DB and skip
                        rejected = RejectedUrlHash(
                            url_hash=url_hash,
                            title=stub.get("title", "")[:500],
                            reason=reason,
                            source_name=stub.get("source_name", ""),
                        )
                        try:
                            session.add(rejected)
                            session.commit()
                        except Exception:
                            session.rollback()
                        run.articles_filtered += 1
                        continue
                    # Shadow mode: log but don't block

            article = save_article_stub(session, stub)
            if article is None:
                continue  # already in DB

            # If discovery already extracted content (e.g. RSS content:encoded), skip URL fetch
            if stub.get("full_text"):
                article.full_text         = stub["full_text"]
                article.extraction_method = stub.get("extraction_method", "rss_content")
                article.extraction_failed = False
            else:
                extractor = stub.get("extractor", "trafilatura")
                text, method = extract_article(stub["url"], extractor=extractor)
                article.full_text         = text
                article.extraction_method = method
                article.extraction_failed = (text is None)

            # Detect language if not already known from source config
            if article.language is None and article.full_text:
                article.language = detect_language(article.full_text)

            if article.full_text:
                new_articles.append(article)
                run.articles_extracted += 1
            else:
                run.articles_failed += 1

            session.commit()

        run.completed_at = datetime.utcnow()
        run.status = "completed"
        session.commit()

        logger.info(
            f"Scrape complete — {run.articles_extracted} extracted, "
            f"{run.articles_filtered} filtered, "
            f"{run.articles_failed} failed, {run.articles_discovered} total discovered"
        )

    except Exception as e:
        logger.exception(f"Scrape stage failed: {e}")
        run.status = "failed"
        run.error_message = str(e)
        run.completed_at = datetime.utcnow()
        session.commit()
        raise

    finally:
        session.close()
        from scraper.browser import browser_manager
        browser_manager.close()

    return new_articles


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Briefer scrape pipeline")
    parser.add_argument("--scrape-only", action="store_true", help="Run the RSS/web scrape stage")
    parser.add_argument("--akamai-only", action="store_true",
                        help="Run akamai-protected sources scrape only (use after --scrape-only)")
    parser.add_argument("--china-only", action="store_true",
                        help="Run China-government sources scrape only (use after --scrape-only)")
    parser.add_argument("--source",      type=str, default=None,
                        help="Limit akamai scrape to a single source by domain (e.g. war.gov)")
    parser.add_argument("--dry-run",     action="store_true",
                        help="Discover and extract but do not write to DB (akamai-only)")
    parser.add_argument("--limit",       type=int, default=0,
                        help="Cap article extraction at N (0 = unlimited)")
    args = parser.parse_args()

    if args.akamai_only:
        from scraper.akamai_scrape import run_akamai_scrape
        logger.info(f"--akamai-only flag set (source={args.source}, dry_run={args.dry_run}, limit={args.limit})")
        run_akamai_scrape(only_domain=args.source, dry_run=args.dry_run, limit=args.limit)
        sys.exit(0)

    if args.china_only:
        from scraper.china_scrape import run_china_scrape
        logger.info(f"--china-only flag set (source={args.source}, dry_run={args.dry_run}, limit={args.limit})")
        run_china_scrape(only_domain=args.source, dry_run=args.dry_run, limit=args.limit)
        sys.exit(0)

    if args.scrape_only:
        logger.info(f"--scrape-only flag set (limit={args.limit})")
        run_scrape(limit=args.limit)
        sys.exit(0)

    # No scrape mode given. The legacy full-pipeline + scheduler modes were
    # removed 2026-06-01 (the synth scripts produce the brief, not this file).
    parser.error("specify a scrape mode: --scrape-only | --akamai-only | --china-only")
