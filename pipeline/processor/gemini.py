"""
gemini.py — Stage 2: Gemini Flash article summarization.

Runs on full article text (after extraction).
Produces structured summaries for all kept articles.

Model: Gemini 2.0 Flash (google-generativeai SDK)
Cost: ~$0.04/day at 200 articles, ~$0.20/day at 1,000 articles
Parallel: ThreadPoolExecutor(max_workers=10)

Controlled by:
  - GEMINI_API_KEY env var
  - pipeline/processor/summarizer_instructions.md — field definitions, scoring rubric
"""

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_GEMINI_MODEL = "gemini-2.0-flash"
_MAX_WORKERS  = 10     # Gemini Flash has generous rate limits
_TEXT_CAP     = 6000   # chars; caps token cost per article


def _load_summarizer_instructions() -> str:
    candidates = [
        Path("/app/pipeline/processor/summarizer_instructions.md"),
        Path(__file__).parent / "summarizer_instructions.md",
    ]
    for p in candidates:
        if p.exists():
            return p.read_text(encoding="utf-8")
    logger.warning("summarizer_instructions.md not found — using built-in defaults")
    return ""


def _build_prompt(title: str, text: str, instructions: str) -> str:
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
  "headline":         "8-12 word rewritten headline, specific and informative",
  "summary":          "100-150 word factual summary of what happened, who did it, why it matters",
  "importance_score": 0.0,
  "category":         "geopolitics",
  "subcategory":      "sanctions",
  "tags":             ["tag1", "tag2", "tag3"],
  "entities":         ["Entity 1", "Entity 2"],
  "time_sensitivity": "breaking"
}}
"""


def summarize_one(
    model,
    title: str,
    text: str,
    instructions: str,
    retries: int = 2,
) -> dict[str, Any]:
    """Summarize a single article with Gemini Flash."""
    prompt = _build_prompt(title, text, instructions)

    for attempt in range(retries + 1):
        try:
            response = model.generate_content(prompt)
            raw = response.text.strip()
            if raw.startswith("```"):
                lines = raw.splitlines()
                raw = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])
            result = json.loads(raw)
            result["model_used"] = _GEMINI_MODEL
            result["failed"]     = False
            result["importance_score"] = max(0.0, min(1.0, float(result.get("importance_score", 0.5))))
            # Ensure list fields are lists
            for field in ("tags", "entities"):
                if not isinstance(result.get(field), list):
                    result[field] = []
            return result

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Gemini JSON parse error (attempt {attempt+1}): {e}")
        except Exception as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code == 429:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Gemini rate limit — waiting {wait}s")
                time.sleep(wait)
            else:
                logger.error(f"Gemini summarization error (attempt {attempt+1}): {e}")
                if attempt < retries:
                    time.sleep(1)

    return {
        "headline":         None,
        "summary":          None,
        "importance_score": 0.5,
        "category":         None,
        "subcategory":      None,
        "tags":             [],
        "entities":         [],
        "time_sensitivity": None,
        "model_used":       _GEMINI_MODEL,
        "failed":           True,
    }


def summarize_articles_parallel(
    articles: list[dict],   # each: {"id": int, "title": str, "full_text": str}
    instructions: str | None = None,
) -> dict[int, dict]:
    """
    Summarize a list of articles in parallel using ThreadPoolExecutor.

    Returns a mapping of article_id → summary result dict.
    """
    if instructions is None:
        instructions = _load_summarizer_instructions()

    try:
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        # Each thread gets its own model instance to avoid shared state issues
    except ImportError:
        logger.error("google-generativeai not installed")
        return {}
    except KeyError:
        logger.error("GEMINI_API_KEY not set")
        return {}

    results: dict[int, dict] = {}

    def _worker(article: dict) -> tuple[int, dict]:
        import google.generativeai as genai
        model = genai.GenerativeModel(_GEMINI_MODEL)
        result = summarize_one(model, article["title"], article["full_text"], instructions)
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
                    "headline": None, "summary": None,
                    "importance_score": 0.5, "category": None, "subcategory": None,
                    "tags": [], "entities": [], "time_sensitivity": None,
                    "model_used": _GEMINI_MODEL, "failed": True,
                }

    logger.info(f"Gemini summarization complete: {len(results)} articles processed")
    return results


def create_gemini_client() -> bool:
    """Returns True if Gemini is available (key set + package installed)."""
    if not os.getenv("GEMINI_API_KEY", "").strip():
        return False
    try:
        import google.generativeai  # noqa: F401
        return True
    except ImportError:
        return False
