"""
site.py — Generates the static HTML site from a DailyBriefing + its related data.
Output goes to /app/output/ which is served by nginx.
"""

import logging
import shutil
from datetime import date, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
OUTPUT_DIR    = Path("/app/output")   # Docker volume, served by nginx


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def build_site(briefing: dict, category_summaries: list[dict], top_articles: list[dict]) -> None:
    """
    Render the full static site for one daily briefing.

    briefing: dict with keys from DailyBriefing model
    category_summaries: list of dicts with {category, headline, summary, articles: [...]}
    top_articles: list of dicts with {title, url, headline, summary, category, importance_score, source_name}
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    env = _get_jinja_env()

    ctx = {
        "briefing":            briefing,
        "category_summaries":  category_summaries,
        "top_articles":        top_articles,
        "build_time":          datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "today":               briefing.get("briefing_date", str(date.today())),
    }

    # ── index.html ────────────────────────────────────────────────────────────
    template = env.get_template("index.html")
    html = template.render(**ctx)
    output_path = OUTPUT_DIR / "index.html"
    output_path.write_text(html, encoding="utf-8")
    logger.info(f"Site built → {output_path}")

    # ── archive entry ─────────────────────────────────────────────────────────
    archive_dir = OUTPUT_DIR / "archive"
    archive_dir.mkdir(exist_ok=True)
    archive_path = archive_dir / f"{ctx['today']}.html"
    archive_path.write_text(html, encoding="utf-8")
    logger.info(f"Archive saved → {archive_path}")
