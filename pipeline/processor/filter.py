"""
filter.py — Stage 1: Groq Llama filter.

Runs on article stubs (title + meta_description) before any HTTP fetch.
Rejects routine noise and saves the decision to rejected_url_hashes.

Model: Llama 3.3-70B on Groq (fast, free tier: 500K tokens/day).
Cost: $0 until volume exceeds free tier.

Controlled by:
  - GROQ_API_KEY env var
  - GROQ_FILTER_ENABLED=true env var (default: false — shadow mode)
  - pipeline/processor/filter_criteria.md — the actual filter logic
"""

import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_GROQ_MODEL = "llama-3.3-70b-versatile"


def _load_filter_criteria() -> str:
    candidates = [
        Path("/app/pipeline/processor/filter_criteria.md"),   # Docker
        Path(__file__).parent / "filter_criteria.md",          # local dev
    ]
    for p in candidates:
        if p.exists():
            return p.read_text(encoding="utf-8")
    logger.warning("filter_criteria.md not found — filter will use built-in defaults only")
    return ""


def _build_prompt(title: str, meta_description: str, criteria: str) -> str:
    meta_clean = (meta_description or "").strip()[:300]
    return f"""\
You are a filter for an intelligence briefing pipeline. Your job is to decide whether
an article stub represents real signal or routine noise.

## Filter criteria (authoritative — follow these exactly):
{criteria}

## Article stub to evaluate:
Title: {title}
Meta description: {meta_clean}

## Your response:
Respond with ONLY this JSON (no markdown, no explanation):
{{"keep": true, "reason": "one-sentence reason for keep or reject"}}

- Set "keep": true if the article should be fetched and processed
- Set "keep": false if it is clearly routine noise per the criteria above
- When in doubt, set "keep": true — false negatives are costly
"""


def filter_stub(
    groq_client,
    stub: dict,
    criteria: str | None = None,
    retries: int = 1,
) -> dict:
    """
    Run Groq filter on a single article stub.

    Returns:
        {
            "keep": bool,
            "reason": str,
            "filtered": True,         # always True — means the filter ran
            "filter_failed": bool,    # True if the API call failed
        }
    """
    if criteria is None:
        criteria = _load_filter_criteria()

    title = stub.get("title", "").strip()
    meta  = stub.get("meta_description", "").strip()

    prompt = _build_prompt(title, meta, criteria)

    for attempt in range(retries + 1):
        try:
            response = groq_client.chat.completions.create(
                model=_GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.0,
            )
            raw = response.choices[0].message.content.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                lines = raw.splitlines()
                raw = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])
            result = json.loads(raw)
            return {
                "keep":          bool(result.get("keep", True)),
                "reason":        str(result.get("reason", ""))[:500],
                "filtered":      True,
                "filter_failed": False,
            }
        except json.JSONDecodeError as e:
            logger.warning(f"Filter JSON parse error (attempt {attempt+1}): {e} — raw: {raw!r}")
        except Exception as e:
            if attempt < retries:
                time.sleep(1)
            logger.warning(f"Groq filter error (attempt {attempt+1}): {e}")

    # If all attempts failed, default to KEEP (safe fallback)
    logger.warning(f"Groq filter failed for '{title[:60]}' — defaulting to keep")
    return {
        "keep":          True,
        "reason":        "filter_failed — defaulting to keep",
        "filtered":      True,
        "filter_failed": True,
    }


def create_groq_client():
    """Create Groq client if API key is available. Returns None otherwise."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from groq import Groq
        return Groq(api_key=api_key)
    except ImportError:
        logger.warning("groq package not installed — Stage 1 filter unavailable")
        return None


def is_filter_enabled() -> bool:
    return os.getenv("GROQ_FILTER_ENABLED", "false").lower() == "true"
