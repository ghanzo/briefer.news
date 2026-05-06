"""
grok.py — xAI Grok API for article summarization and world brief generation.

Uses the OpenAI-compatible API at api.x.ai.

Stage 2: Per-article summarization (grok-3-mini-fast)
Stage 3: World brief generation (grok-3-mini-fast)

Controlled by:
  - XAI_API_KEY env var
"""

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from openai import OpenAI

from .prompts import ARTICLE_SUMMARY_PROMPT, WORLD_BRIEF_PROMPT

logger = logging.getLogger(__name__)

ARTICLE_MODEL = "grok-3-mini-fast"
SYNTHESIS_MODEL = "grok-3-mini-fast"
_MAX_WORKERS = 10
_TEXT_CAP = 6000


def create_grok_client() -> OpenAI | None:
    """Create xAI Grok client if API key is available."""
    api_key = os.getenv("XAI_API_KEY", "").strip()
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])
    return json.loads(text)


def _load_summarizer_instructions() -> str:
    candidates = [
        Path("/app/pipeline/processor/summarizer_instructions.md"),
        Path(__file__).parent / "summarizer_instructions.md",
    ]
    for p in candidates:
        if p.exists():
            return p.read_text(encoding="utf-8")
    return ""


def load_lens() -> str:
    candidates = [
        Path("/app/lens.md"),
        Path(__file__).parent.parent.parent / "lens.md",
    ]
    for p in candidates:
        if p.exists():
            return p.read_text(encoding="utf-8")
    logger.warning("lens.md not found")
    return ""


# ── Stage 2: Per-article summarization ────────────────────────────────────

def _build_article_prompt(title: str, text: str, instructions: str) -> str:
    return f"""\
{instructions}

---

## Article to summarize:

Title: {title}

Text:
{text[:_TEXT_CAP]}

---

Respond with ONLY this JSON (no markdown, no explanation):
{{
  "headline":         "6-10 word headline capturing the core fact",
  "summary":          "1-2 sentence factual summary: what happened, who did it, why it matters",
  "importance_score": 0.0,
  "category":         "geopolitics",
  "region":           "global",
  "subcategory":      "sanctions",
  "tags":             ["tag1", "tag2", "tag3"],
  "entities":         ["Entity 1", "Entity 2"],
  "time_sensitivity": "breaking"
}}

Scoring guide:
- 0.0-0.1 = routine regulatory/procedural noise
- 0.2-0.4 = notable but expected developments
- 0.5-0.6 = significant, affects many people
- 0.7-0.8 = major event with global implications
- 0.9-1.0 = historic, world-altering (use extremely rarely)
- Most articles should score 0.1-0.4. Be harsh.
"""


def summarize_one(
    client: OpenAI,
    title: str,
    text: str,
    instructions: str,
    retries: int = 2,
) -> dict[str, Any]:
    prompt = _build_article_prompt(title, text, instructions)

    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model=ARTICLE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.0,
            )
            result = _parse_json_response(response.choices[0].message.content)
            result["model_used"] = ARTICLE_MODEL
            result["failed"] = False
            result["importance_score"] = max(0.0, min(1.0, float(result.get("importance_score", 0.5))))
            for field in ("tags", "entities"):
                if not isinstance(result.get(field), list):
                    result[field] = []
            return result

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Grok JSON parse error (attempt {attempt+1}): {e}")
        except Exception as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status == 429:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Grok rate limit -- waiting {wait}s")
                time.sleep(wait)
            else:
                logger.error(f"Grok summarization error (attempt {attempt+1}): {e}")
                if attempt < retries:
                    time.sleep(1)

    return {
        "headline": None, "summary": None, "importance_score": 0.5,
        "category": None, "region": None, "subcategory": None,
        "tags": [], "entities": [], "time_sensitivity": None,
        "model_used": ARTICLE_MODEL, "failed": True,
    }


def summarize_articles_parallel(
    client: OpenAI,
    articles: list[dict],
    instructions: str | None = None,
) -> dict[int, dict]:
    if instructions is None:
        instructions = _load_summarizer_instructions()

    results: dict[int, dict] = {}

    def _worker(article: dict) -> tuple[int, dict]:
        result = summarize_one(client, article["title"], article["full_text"], instructions)
        return article["id"], result

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        futures = {executor.submit(_worker, art): art["id"] for art in articles}
        for future in as_completed(futures):
            try:
                article_id, result = future.result()
                results[article_id] = result
            except Exception as e:
                article_id = futures[future]
                logger.error(f"Worker failed for article {article_id}: {e}")
                results[article_id] = {
                    "headline": None, "summary": None, "importance_score": 0.5,
                    "category": None, "region": None, "subcategory": None,
                    "tags": [], "entities": [], "time_sensitivity": None,
                    "model_used": ARTICLE_MODEL, "failed": True,
                }

    logger.info(f"Grok summarization complete: {len(results)} articles processed")
    return results


# ── Stage 3: World Brief ──────────────────────────────────────────────────

def generate_world_brief(
    client: OpenAI,
    scored_articles: list[dict],
    briefing_date: str,
    source_count: int = 0,
    financial_context: str = "",
) -> dict:
    """
    Generate the world brief from scored/summarized articles.

    Returns: {date, headline, bullets: [{bullet, region, severity}], watch}
    """
    lens = load_lens()

    # Build articles text — top 50 by importance, with summaries
    articles_text = "\n".join(
        f"[{a.get('category', '?').upper()}] [{a.get('region', '?')}] "
        f"(score: {a.get('importance_score', 0):.2f}) "
        f"{a.get('headline', a.get('title', ''))}: {a.get('summary', '')}"
        for a in scored_articles[:50]
    )

    prompt = WORLD_BRIEF_PROMPT.format(
        date=briefing_date,
        lens=lens,
        article_count=len(scored_articles),
        source_count=source_count,
        articles_text=articles_text,
        financial_context=financial_context or "No financial data available for this run.",
    )

    try:
        response = client.chat.completions.create(
            model=SYNTHESIS_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.2,
        )
        result = _parse_json_response(response.choices[0].message.content)
        logger.info("World brief generated")
        return result

    except Exception as e:
        logger.error(f"World brief generation failed: {e}")
        return {
            "date": briefing_date,
            "headline": f"World Brief -- {briefing_date}",
            "bullets": [],
            "watch": "Brief generation failed.",
        }
