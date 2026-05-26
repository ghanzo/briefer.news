"""briefer watch — show a series with history and delta."""

from rich.console import Console

from briefer.analysis.deltas import compute_series_delta
from briefer.db.connection import get_connection
from briefer.db.queries import get_series_meta, get_observations
from briefer.display.tables import render_watch

console = Console()


def run_watch(ctx_obj: dict, series_id: str, periods: int) -> None:
    conn = get_connection(ctx_obj.get("db_path"))

    meta = get_series_meta(conn, series_id)
    if not meta:
        console.print(f"[red]Series '{series_id}' not found. Run 'briefer pull' first.[/red]")
        conn.close()
        return

    observations = get_observations(conn, series_id, limit=max(periods, 260))
    conn.close()

    if not observations:
        console.print(f"[yellow]No observations for {series_id}.[/yellow]")
        return

    delta = compute_series_delta(observations)
    render_watch(meta, observations[:periods], delta)
