"""briefer pull — fetch data from sources."""

import click
from rich.console import Console

from briefer.config.catalog import get_catalog_series
from briefer.db.connection import get_connection
from briefer.db.queries import upsert_series, upsert_observations, log_pull_start, log_pull_end
from briefer.display.tables import render_pull_summary
from briefer.sources.registry import get_source, get_all_sources

console = Console()


def run_pull(ctx_obj: dict, source: str | None, pull_all: bool, series: tuple) -> None:
    if not source and not pull_all:
        console.print("[red]Specify a source (e.g. briefer pull fred) or use --all[/red]")
        return

    conn = get_connection(ctx_obj.get("db_path"))

    if pull_all:
        sources_to_pull = get_all_sources()
    else:
        try:
            sources_to_pull = {source: get_source(source)}
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            return

    for src_name, src in sources_to_pull.items():
        if not src.validate_config():
            console.print(f"[yellow]{src.display_name}: API key not set "
                          f"(briefer config --set {src.env_key_name} <key>)[/yellow]")
            continue

        _pull_source(conn, src, src_name, series)

    conn.close()


def _pull_source(conn, src, src_name: str, series_filter: tuple) -> None:
    pull_id = log_pull_start(conn, src_name)
    catalog = get_catalog_series(src_name)

    # If specific series requested, filter catalog
    if series_filter:
        keys = {s.upper() for s in series_filter}
        catalog = {k: v for k, v in catalog.items() if k.upper() in keys}
        if not catalog:
            console.print(f"[yellow]No matching series in {src_name} catalog for: "
                          f"{', '.join(series_filter)}[/yellow]")
            return

    results = []
    total_obs = 0

    with console.status(f"[bold]Pulling {src.display_name}…[/bold]") as status:
        for source_key, cat_info in catalog.items():
            series_id = src.make_series_id(source_key)
            status.update(f"[bold]Pulling {series_id}…[/bold]")

            # Fetch metadata
            meta = src.fetch_series_meta(source_key)
            if meta is None:
                console.print(f"  [yellow]Could not fetch metadata for {source_key}[/yellow]")
                continue

            upsert_series(conn, {
                "series_id": series_id,
                "source": src_name,
                "source_key": source_key,
                "name": meta.name,
                "frequency": meta.frequency,
                "units": meta.units,
                "seasonal_adj": meta.seasonal_adj,
                "category": cat_info.get("category"),
                "metadata": None,
            })

            # Fetch observations
            observations = src.fetch_observations(source_key)
            obs_count = upsert_observations(conn, series_id, [
                {"date": o.date, "value": o.value} for o in observations
            ])
            total_obs += obs_count

            # Get latest for display
            latest = observations[-1] if observations else None
            results.append({
                "series_id": series_id,
                "name": meta.name,
                "obs_count": obs_count,
                "latest_date": latest.date if latest else None,
                "latest_value": latest.value if latest else None,
                "units": meta.units,
            })

    log_pull_end(conn, pull_id, len(results), total_obs)
    render_pull_summary(src.display_name, results)
