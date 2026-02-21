"""
main.py — Pipeline orchestrator.

Runs the full pipeline:
  1. Load sources from config/sources.yaml
  2. Discover article URLs (RSS + Google News)
  3. Extract full text (trafilatura → BS4 fallback)
  4. Store articles in PostgreSQL
  5. Summarize new articles with Claude Haiku
  6. Select top articles by importance score
  7. Generate category summaries + meta story with Claude Sonnet
  8. Build static HTML site
  9. Log the run

Usage:
  python main.py             # starts the scheduler (runs daily at SCHEDULE_TIME)
  python main.py --run-now   # run the pipeline immediately, then start scheduler
"""

import argparse
import logging
import os
import sys
import time
from datetime import date, datetime

import anthropic
import yaml
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

from db.models import (
    get_engine, get_session,
    Source, Article, ArticleSummary, DailyBriefing, CategorySummary, ScrapeRun,
)
from scraper.discovery import discover_articles
from scraper.extractor import extract_article
from processor.claude import summarize_article, generate_category_summaries, generate_meta_story
from builder.site import build_site
from scheduler import start_scheduler

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

TOP_ARTICLES_COUNT = int(os.getenv("TOP_ARTICLES_COUNT", "5"))


# ─────────────────────────────────────────────────────────────────────────────
# Config loader
# ─────────────────────────────────────────────────────────────────────────────

def load_sources_config() -> list[dict]:
    config_path = os.path.join(os.path.dirname(__file__), "config", "sources.yaml")
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("sources", [])


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────

def sync_sources(session, sources_config: list[dict]) -> dict[str, int]:
    """
    Ensure all sources in sources.yaml exist in the DB.
    Returns a mapping of source name → db id.
    """
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
    """Insert an article stub, skip if URL already exists."""
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
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline() -> None:
    logger.info("═" * 60)
    logger.info(f"Pipeline started — {datetime.utcnow().isoformat()}")

    engine  = get_engine()
    session = get_session(engine)
    today   = str(date.today())

    # ── Start audit run ────────────────────────────────────────────────────
    run = ScrapeRun()
    session.add(run)
    session.commit()

    try:
        # ── 1. Load + sync sources ─────────────────────────────────────────
        sources_config = load_sources_config()
        name_to_id = sync_sources(session, sources_config)

        # Enrich configs with DB ids
        active_sources = [
            {**cfg, "db_id": name_to_id.get(cfg["name"])}
            for cfg in sources_config
            if cfg.get("active", True)
        ]

        # ── 2. Discovery ───────────────────────────────────────────────────
        logger.info(f"Discovering articles from {len(active_sources)} sources…")
        stubs = discover_articles(active_sources)
        run.articles_discovered = len(stubs)
        session.commit()

        # ── 3. Save stubs + extract full text ─────────────────────────────
        new_articles: list[Article] = []
        failed = 0

        for stub in stubs:
            article = save_article_stub(session, stub)
            if article is None:
                continue   # already in DB

            text, method = extract_article(stub["url"])
            article.full_text         = text
            article.extraction_method = method
            article.extraction_failed = (text is None)

            if text:
                new_articles.append(article)
                run.articles_extracted += 1
            else:
                failed += 1
                run.articles_failed += 1

            session.commit()

        logger.info(
            f"Extraction complete: {len(new_articles)} extracted, {failed} failed"
        )

        if not new_articles:
            logger.warning("No new articles extracted — skipping AI processing")
            run.status = "completed"
            session.commit()
            return

        # ── 4. Claude: per-article summarization ──────────────────────────
        claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        summaries_created = 0

        for article in new_articles:
            if not article.full_text:
                continue

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

        # ── 5. Select top articles for today's briefing ────────────────────
        # Pull all articles from today with summaries, sorted by importance
        today_summaries = (
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

        # Group by category
        articles_by_category: dict[str, list[dict]] = {}
        for summ, art, src in today_summaries:
            cat = summ.category or "general"
            entry = {
                "id":              art.id,
                "title":           art.title,
                "url":             art.url,
                "headline":        summ.headline or art.title,
                "summary":         summ.summary or "",
                "importance_score": summ.importance_score,
                "category":        cat,
                "source_name":     src.name if src else "Unknown",
                "publish_date":    str(art.publish_date) if art.publish_date else None,
            }
            articles_by_category.setdefault(cat, []).append(entry)

        # Global top N by importance
        all_sorted = sorted(
            [e for cat_list in articles_by_category.values() for e in cat_list],
            key=lambda x: x["importance_score"],
            reverse=True,
        )
        top_articles = all_sorted[:TOP_ARTICLES_COUNT]

        # ── 6. Category summaries ──────────────────────────────────────────
        cat_summaries = generate_category_summaries(claude, articles_by_category, today)

        # ── 7. Meta story ──────────────────────────────────────────────────
        meta = generate_meta_story(claude, top_articles, cat_summaries, today)

        # ── 8. Save briefing ───────────────────────────────────────────────
        briefing = DailyBriefing(
            briefing_date=date.today(),
            meta_headline=meta.get("meta_headline"),
            meta_story=meta.get("meta_story"),
            top_article_ids=[a["id"] for a in top_articles],
            total_articles_scraped=run.articles_discovered,
            total_articles_processed=summaries_created,
        )
        session.add(briefing)
        session.flush()

        for cat, data in cat_summaries.items():
            cat_art_ids = [a["id"] for a in articles_by_category.get(cat, [])]
            cs = CategorySummary(
                briefing_id=briefing.id,
                category=cat,
                headline=data.get("headline"),
                summary=data.get("summary"),
                article_ids=cat_art_ids,
            )
            session.add(cs)

        session.commit()

        # ── 9. Build static site ───────────────────────────────────────────
        cat_summary_dicts = [
            {
                "category":  cat,
                "headline":  data.get("headline"),
                "summary":   data.get("summary"),
                "articles":  articles_by_category.get(cat, []),
            }
            for cat, data in cat_summaries.items()
        ]

        build_site(
            briefing={
                "briefing_date": str(briefing.briefing_date),
                "meta_headline": briefing.meta_headline,
                "meta_story":    briefing.meta_story,
            },
            category_summaries=cat_summary_dicts,
            top_articles=top_articles,
        )

        # ── 10. Finalize run ───────────────────────────────────────────────
        run.completed_at = datetime.utcnow()
        run.status = "completed"
        session.commit()

        logger.info(f"Pipeline complete — briefing for {today} saved and site built.")

    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        run.status = "failed"
        run.error_message = str(e)
        run.completed_at = datetime.utcnow()
        session.commit()
        raise

    finally:
        session.close()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)

    parser = argparse.ArgumentParser(description="Briefer pipeline")
    parser.add_argument("--run-now", action="store_true", help="Run pipeline immediately")
    args = parser.parse_args()

    if args.run_now:
        logger.info("--run-now flag set: running pipeline immediately")
        run_pipeline()

    logger.info("Starting scheduler…")
    start_scheduler(run_pipeline)
