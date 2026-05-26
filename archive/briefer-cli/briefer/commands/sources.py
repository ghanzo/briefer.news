"""briefer sources — list configured sources."""

from briefer.db.connection import get_connection
from briefer.db.queries import get_all_series
from briefer.display.tables import render_sources
from briefer.sources.registry import get_all_sources


def run_sources(ctx_obj: dict) -> None:
    conn = get_connection(ctx_obj.get("db_path"))
    all_series = get_all_series(conn)
    conn.close()

    sources = get_all_sources()
    status_list = []

    for name, src in sources.items():
        series_count = sum(1 for s in all_series if s["source"] == name)
        status_list.append({
            "name": name,
            "display_name": src.display_name,
            "has_key": src.validate_config(),
            "series_count": series_count,
        })

    render_sources(status_list)
