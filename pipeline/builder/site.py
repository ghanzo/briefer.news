"""
site.py — Generates the static HTML site from a world brief.
Output goes to /app/output/ which is served by nginx.
"""

import logging
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


def build_site(brief: dict, top_articles: list[dict]) -> None:
    """
    Render the static site for one daily brief.

    brief: dict with {date, headline, items: [{bullet, region, severity}], watch}
    top_articles: list of source articles for the expandable section
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    env = _get_jinja_env()

    today = brief.get("date", str(date.today()))

    ctx = {
        "brief":          brief,
        "top_articles":   top_articles,
        "build_time":     datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "today":          today,
    }

    # ── index.html ────────────────────────────────────────────────────────────
    template = env.get_template("index.html")
    html = template.render(**ctx)
    output_path = OUTPUT_DIR / "index.html"
    output_path.write_text(html, encoding="utf-8")
    logger.info(f"Site built -> {output_path}")

    # ── archive entry ─────────────────────────────────────────────────────────
    archive_dir = OUTPUT_DIR / "archive"
    archive_dir.mkdir(exist_ok=True)
    archive_path = archive_dir / f"{today}.html"
    archive_path.write_text(html, encoding="utf-8")
    logger.info(f"Archive saved -> {archive_path}")
