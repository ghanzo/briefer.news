"""
main.py — Pipeline orchestrator.

Two independent stages:

  STAGE 1 — scrape   (no API key needed)
    - Load sources from config/sources.yaml
    - Discover article URLs via RSS + Google News
    - Extract full text with trafilatura → BS4 fallback
    - Store everything in PostgreSQL

  STAGE 2 — process  (requires ANTHROPIC_API_KEY)
    - Summarize articles with Claude Haiku
    - Generate category summaries + meta story with Claude Sonnet
    - Build static HTML site

Usage:
  python main.py                        # scheduler mode — full pipeline daily at SCHEDULE_TIME
  python main.py --scrape-only          # run scrape stage now, skip AI
  python main.py --scrape-only --limit 20  # scrape only, cap at 20 articles (for testing)
  python main.py --run-now              # run full pipeline now (scrape + process)
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
from builder.site import build_site
from scheduler import start_scheduler
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
# Stage 2 + 3 — Process (Gemini Flash for articles, Claude Sonnet for synthesis)
# ─────────────────────────────────────────────────────────────────────────────

def run_process() -> None:
    """
    Stage 2: Summarize unprocessed articles.
    Stage 3: Generate world brief (PDB-style).
    Builds static HTML site.

    Provider priority: Grok (XAI_API_KEY) > Gemini (GEMINI_API_KEY) > Claude (ANTHROPIC_API_KEY)
    """
    from processor.grok import create_grok_client
    from processor.gemini import create_gemini_client, summarize_articles_parallel as gemini_summarize

    grok_client = create_grok_client()
    use_gemini = create_gemini_client() if not grok_client else False
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    has_anthropic = anthropic_key and anthropic_key != "your_anthropic_api_key_here"

    if not grok_client and not use_gemini and not has_anthropic:
        logger.warning("No AI API key set (XAI_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY) -- skipping process stage")
        return

    logger.info("=" * 60)
    logger.info(f"STAGE 2 + 3 -- PROCESS -- {datetime.utcnow().isoformat()}")

    if grok_client:
        logger.info("Provider: Grok (xAI) -- all stages")
    elif use_gemini:
        logger.info("Stage 2: Gemini Flash | Stage 3: Claude Sonnet")
    else:
        logger.info("Provider: Claude -- all stages")

    engine  = get_engine()
    session = get_session(engine)
    today   = str(date.today())

    try:
        # Find articles without summaries
        unprocessed = (
            session.query(Article)
            .outerjoin(ArticleSummary, Article.id == ArticleSummary.article_id)
            .filter(
                ArticleSummary.id.is_(None),
                Article.extraction_failed == False,
                Article.full_text.isnot(None),
            )
            .all()
        )

        logger.info(f"Processing {len(unprocessed)} articles...")
        summaries_created = 0

        if grok_client and unprocessed:
            from processor.grok import summarize_articles_parallel as grok_summarize
            article_dicts = [
                {"id": a.id, "title": a.title, "full_text": a.full_text}
                for a in unprocessed
            ]
            batch_results = grok_summarize(grok_client, article_dicts)

            for article in unprocessed:
                result = batch_results.get(article.id, {})
                summary = ArticleSummary(
                    article_id=article.id,
                    summary=result.get("summary"),
                    headline=result.get("headline"),
                    importance_score=result.get("importance_score", 0.5),
                    category=result.get("category"),
                    subcategory=result.get("subcategory"),
                    tags=result.get("tags", []),
                    entities=result.get("entities", []),
                    time_sensitivity=result.get("time_sensitivity"),
                    model_used=result.get("model_used"),
                    failed=result.get("failed", False),
                )
                session.add(summary)
                summaries_created += 1
            session.commit()

        elif use_gemini and unprocessed:
            article_dicts = [
                {"id": a.id, "title": a.title, "full_text": a.full_text}
                for a in unprocessed
            ]
            batch_results = gemini_summarize(article_dicts)

            for article in unprocessed:
                result = batch_results.get(article.id, {})
                summary = ArticleSummary(
                    article_id=article.id,
                    summary=result.get("summary"),
                    headline=result.get("headline"),
                    importance_score=result.get("importance_score", 0.5),
                    category=result.get("category"),
                    subcategory=result.get("subcategory"),
                    tags=result.get("tags", []),
                    entities=result.get("entities", []),
                    time_sensitivity=result.get("time_sensitivity"),
                    model_used=result.get("model_used"),
                    failed=result.get("failed", False),
                )
                session.add(summary)
                summaries_created += 1
            session.commit()

        elif has_anthropic and unprocessed:
            import anthropic
            from processor.claude import summarize_article
            claude = anthropic.Anthropic(api_key=anthropic_key)
            for article in unprocessed:
                result = summarize_article(claude, article.title, article.full_text)
                summary = ArticleSummary(
                    article_id=article.id,
                    summary=result.get("summary"),
                    headline=result.get("headline"),
                    importance_score=result.get("importance_score", 0.5),
                    category=result.get("category"),
                    tags=result.get("tags", []),
                    model_used=result.get("model_used"),
                    failed=result.get("failed", False),
                )
                session.add(summary)
                session.commit()
                summaries_created += 1

        logger.info(f"Summaries created: {summaries_created}")

        # Pull all scored articles, sorted by importance
        scored = (
            session.query(ArticleSummary, Article, Source)
            .join(Article, ArticleSummary.article_id == Article.id)
            .outerjoin(Source, Article.source_id == Source.id)
            .filter(
                ArticleSummary.failed == False,
                ArticleSummary.importance_score.isnot(None),
            )
            .order_by(ArticleSummary.importance_score.desc())
            .limit(100)
            .all()
        )

        all_articles = []
        for summ, art, src in scored:
            all_articles.append({
                "id":               art.id,
                "title":            art.title,
                "url":              art.url,
                "headline":         summ.headline or art.title,
                "summary":          summ.summary or "",
                "importance_score": summ.importance_score,
                "category":         summ.category or "general",
                "region":           getattr(summ, "subcategory", None) or "global",
                "source_name":      src.name if src else "Unknown",
                "publish_date":     str(art.publish_date) if art.publish_date else None,
            })

        # Count unique sources
        source_count = session.query(Source).filter(Source.active == True).count()

        # Stage 3: Generate world brief
        if grok_client:
            from processor.grok import generate_world_brief
            brief = generate_world_brief(grok_client, all_articles, today, source_count)
        else:
            # Fallback: build a simple brief from the scored articles
            brief = {
                "date": today,
                "headline": f"World Brief -- {today}",
                "items": [
                    {"bullet": a["headline"] + ": " + a["summary"], "region": a.get("region", "global"), "severity": "high" if a["importance_score"] >= 0.7 else "medium"}
                    for a in all_articles[:10]
                ],
                "watch": "AI synthesis unavailable -- showing top articles by importance score.",
            }

        # Save to DB
        import json as _json
        briefing = DailyBriefing(
            briefing_date=date.today(),
            meta_headline=brief.get("headline"),
            meta_story=_json.dumps(brief),
            top_article_ids=[a["id"] for a in all_articles[:TOP_ARTICLES_COUNT]],
            total_articles_scraped=len(all_articles),
            total_articles_processed=summaries_created,
        )
        session.add(briefing)
        session.commit()

        build_site(
            brief=brief,
            top_articles=all_articles[:50],
        )

        logger.info(f"Process stage complete -- world brief for {today} built.")

    except Exception as e:
        logger.exception(f"Process stage failed: {e}")
        raise

    finally:
        session.close()


# ─────────────────────────────────────────────────────────────────────────────
# Full pipeline (scrape + process)
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline() -> None:
    run_scrape()
    run_process()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Briefer pipeline")
    parser.add_argument("--run-now",     action="store_true", help="Run full pipeline now")
    parser.add_argument("--scrape-only", action="store_true", help="Run scrape stage only (no AI)")
    parser.add_argument("--limit",       type=int, default=0, help="Cap article extraction at N (0 = unlimited)")
    args = parser.parse_args()

    if args.scrape_only:
        logger.info(f"--scrape-only flag set (limit={args.limit})")
        run_scrape(limit=args.limit)
        sys.exit(0)

    if args.run_now:
        logger.info("--run-now flag set: running full pipeline")
        run_pipeline()

    logger.info("Starting scheduler…")
    start_scheduler(run_pipeline)
