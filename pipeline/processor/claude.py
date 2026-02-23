"""
claude.py — All Claude API calls.

Three functions:
  1. summarize_article()         — per-article: summary, headline, importance, tags
  2. generate_category_summaries() — per-category synthesis for a day
  3. generate_meta_story()       — the daily meta story using lens.md
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

import anthropic

from .prompts import ARTICLE_SUMMARY_PROMPT, CATEGORY_SUMMARY_PROMPT, META_STORY_PROMPT

logger = logging.getLogger(__name__)

# Haiku for high-volume per-article work (cheap + fast)
ARTICLE_MODEL  = "claude-haiku-4-5-20251001"
# Sonnet for synthesis and meta story (smarter, richer output)
SYNTHESIS_MODEL = "claude-sonnet-4-6"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_json_response(text: str) -> dict:
    """Strip any markdown fences and parse JSON from a Claude response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])
    return json.loads(text)


def load_lens() -> str:
    """Load lens.md from the project root (mounted at /app/lens.md in Docker)."""
    candidates = [
        Path("/app/lens.md"),
        Path(__file__).parent.parent.parent / "lens.md",
    ]
    for p in candidates:
        if p.exists():
            return p.read_text(encoding="utf-8")
    logger.warning("lens.md not found — meta story will have no interpretive framework")
    return ""


def load_site_voice() -> str:
    """Load site_voice.md from the processor directory."""
    candidates = [
        Path("/app/pipeline/processor/site_voice.md"),
        Path(__file__).parent / "site_voice.md",
    ]
    for p in candidates:
        if p.exists():
            return p.read_text(encoding="utf-8")
    logger.warning("site_voice.md not found — Stage 3 will use default voice")
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# 1. Per-article summarization
# ─────────────────────────────────────────────────────────────────────────────

def summarize_article(
    client: anthropic.Anthropic,
    title: str,
    text: str,
    retries: int = 2,
) -> dict[str, Any]:
    """
    Send one article to Claude Haiku for summarization.
    Returns a dict with: summary, headline, importance_score, category, tags, model_used, failed
    """
    prompt = ARTICLE_SUMMARY_PROMPT.format(
        title=title,
        text=text[:5000],   # cap to avoid huge token bills on one article
    )

    for attempt in range(retries + 1):
        try:
            response = client.messages.create(
                model=ARTICLE_MODEL,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            result = _parse_json_response(response.content[0].text)
            result["model_used"] = ARTICLE_MODEL
            result["failed"]     = False
            # Clamp importance score
            result["importance_score"] = max(0.0, min(1.0, float(result.get("importance_score", 0.5))))
            return result

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"JSON parse error on article summary (attempt {attempt+1}): {e}")
        except anthropic.RateLimitError:
            wait = 2 ** attempt
            logger.warning(f"Rate limit hit — waiting {wait}s")
            time.sleep(wait)
        except Exception as e:
            logger.error(f"Claude summarization error (attempt {attempt+1}): {e}")

    return {
        "summary":          None,
        "headline":         None,
        "importance_score": 0.5,
        "category":         None,
        "tags":             [],
        "model_used":       ARTICLE_MODEL,
        "failed":           True,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Category-level synthesis
# ─────────────────────────────────────────────────────────────────────────────

def generate_category_summaries(
    client: anthropic.Anthropic,
    articles_by_category: dict[str, list[dict]],
    briefing_date: str,
) -> dict[str, dict]:
    """
    For each category, synthesize the top articles into a category summary.

    articles_by_category: { "technology": [{"headline": ..., "summary": ...}, ...], ... }
    Returns: { "technology": {"headline": ..., "summary": ...}, ... }
    """
    results: dict[str, dict] = {}

    for category, articles in articles_by_category.items():
        if not articles:
            continue

        articles_text = "\n\n".join(
            f"- {a['headline']}\n  {a['summary']}"
            for a in articles[:10]  # top 10 per category is plenty
        )

        prompt = CATEGORY_SUMMARY_PROMPT.format(
            category=category,
            date=briefing_date,
            articles_text=articles_text,
        )

        try:
            response = client.messages.create(
                model=SYNTHESIS_MODEL,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            result = _parse_json_response(response.content[0].text)
            results[category] = result
            logger.info(f"Category summary generated for: {category}")

        except Exception as e:
            logger.error(f"Category summary failed for {category}: {e}")
            results[category] = {
                "headline": f"{category.title()} — {briefing_date}",
                "summary":  "Summary generation failed.",
            }

    return results


# ─────────────────────────────────────────────────────────────────────────────
# 3. Daily meta story
# ─────────────────────────────────────────────────────────────────────────────

def generate_meta_story(
    client: anthropic.Anthropic,
    top_articles: list[dict],
    category_summaries: dict[str, dict],
    briefing_date: str,
) -> dict[str, str]:
    """
    Generate the daily meta story using Sonnet + the lens.md framework.

    top_articles: list of dicts with at least {headline, summary, category}
    category_summaries: output of generate_category_summaries()
    """
    lens       = load_lens()
    site_voice = load_site_voice()

    top_articles_text = "\n\n".join(
        f"[{a.get('category', 'unknown').upper()}] {a['headline']}\n{a['summary']}"
        for a in top_articles
    )

    category_summaries_text = "\n\n".join(
        f"### {cat.upper()}\n{data.get('headline', '')}\n{data.get('summary', '')}"
        for cat, data in category_summaries.items()
    )

    prompt = META_STORY_PROMPT.format(
        date=briefing_date,
        lens=lens,
        site_voice=site_voice,
        top_count=len(top_articles),
        top_articles=top_articles_text,
        category_summaries=category_summaries_text,
    )

    try:
        response = client.messages.create(
            model=SYNTHESIS_MODEL,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        result = _parse_json_response(response.content[0].text)
        logger.info("Meta story generated")
        return result

    except Exception as e:
        logger.error(f"Meta story generation failed: {e}")
        return {
            "meta_headline": f"World Briefing — {briefing_date}",
            "meta_story":    "Meta story generation failed.",
        }
