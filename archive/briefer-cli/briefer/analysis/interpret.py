"""Claude interpretation layer — reads numbers, writes analysis."""

import json
import logging
import time

import anthropic

from briefer.analysis.prompts import SERIES_INTERPRETATION_PROMPT, DIGEST_PROMPT
from briefer.config.settings import get_key
from briefer.display.formatters import format_number

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"


def _get_client() -> anthropic.Anthropic | None:
    key = get_key("ANTHROPIC_API_KEY")
    if not key or key == "your_anthropic_api_key_here":
        return None
    return anthropic.Anthropic(api_key=key)


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])
    return json.loads(text)


def _format_history_table(observations: list[dict], units: str | None, limit: int = 15) -> str:
    lines = []
    for obs in observations[:limit]:
        lines.append(f"  {obs['date']}  {format_number(obs['value'], units)}")
    return "\n".join(lines)


def interpret_series(
    meta: dict,
    delta: dict,
    observations: list[dict],
    retries: int = 1,
) -> str | None:
    """Ask Claude to interpret a single series' movement."""
    client = _get_client()
    if not client:
        return None

    history = _format_history_table(observations, meta.get("units"))

    prompt = SERIES_INTERPRETATION_PROMPT.format(
        name=meta.get("name", meta.get("series_id", "")),
        source=meta.get("source", ""),
        units=meta.get("units", ""),
        frequency=meta.get("frequency", ""),
        latest_value=format_number(delta.get("latest_value"), meta.get("units")),
        latest_date=delta.get("latest_date", "—"),
        prior_value=format_number(delta.get("prior_value"), meta.get("units")),
        prior_date=delta.get("prior_date", "—"),
        absolute_change=f"{delta.get('absolute_change', 0):+,.2f}" if delta.get("absolute_change") is not None else "—",
        percent_change=f"{delta.get('percent_change', 0):+.1f}" if delta.get("percent_change") is not None else "—",
        direction=delta.get("direction", "flat"),
        z_score=f"{delta.get('z_score', 0):+.2f}" if delta.get("z_score") is not None else "N/A",
        min_52w=format_number(delta.get("min_52w"), meta.get("units")),
        max_52w=format_number(delta.get("max_52w"), meta.get("units")),
        percentile_52w=f"{delta.get('percentile_52w', 0):.0%}" if delta.get("percentile_52w") is not None else "N/A",
        trend=delta.get("trend", "flat"),
        history_table=history,
    )

    for attempt in range(retries + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except anthropic.RateLimitError:
            wait = 2 ** attempt
            logger.warning(f"Rate limit — waiting {wait}s")
            time.sleep(wait)
        except Exception as e:
            logger.error(f"Claude interpretation error: {e}")
            if attempt < retries:
                time.sleep(1)

    return None


def interpret_digest(
    movers: list[dict],
    digest_date: str,
    retries: int = 1,
) -> dict | None:
    """Ask Claude to write a full daily digest."""
    client = _get_client()
    if not client:
        return None

    movers_text = []
    for m in movers[:15]:
        line = (
            f"- {m.get('name', m.get('series_id', ''))}: "
            f"{format_number(m.get('latest_value'), m.get('units'))} "
            f"({m.get('absolute_change', 0):+,.2f}, {m.get('percent_change', 0):+.1f}%)"
        )
        z = m.get("z_score")
        if z and abs(z) > 1:
            line += f" [z={z:+.1f}]"
        movers_text.append(line)

    prompt = DIGEST_PROMPT.format(
        date=digest_date,
        movers_summary="\n".join(movers_text),
    )

    for attempt in range(retries + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )
            return _parse_json_response(response.content[0].text)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Digest JSON parse error (attempt {attempt + 1}): {e}")
        except anthropic.RateLimitError:
            wait = 2 ** attempt
            logger.warning(f"Rate limit — waiting {wait}s")
            time.sleep(wait)
        except Exception as e:
            logger.error(f"Claude digest error: {e}")
            if attempt < retries:
                time.sleep(1)

    return None
