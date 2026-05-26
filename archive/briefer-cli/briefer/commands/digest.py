"""briefer digest — full pull + analysis of what moved."""

from datetime import date

from rich.console import Console

from briefer.analysis.deltas import compute_series_delta, rank_movers
from briefer.analysis.interpret import interpret_digest
from briefer.commands.pull import run_pull
from briefer.db.connection import get_connection
from briefer.db.queries import get_all_series, get_observations
from briefer.display.tables import render_digest

console = Console()


def run_digest(ctx_obj: dict, no_pull: bool) -> None:
    if not no_pull:
        console.print("[bold]Step 1: Pulling latest data…[/bold]\n")
        run_pull(ctx_obj, source=None, pull_all=True, series=())

    console.print("[bold]Step 2: Computing deltas…[/bold]\n")
    conn = get_connection(ctx_obj.get("db_path"))
    all_series = get_all_series(conn)

    if not all_series:
        console.print("[yellow]No data in DB. Run 'briefer pull' first.[/yellow]")
        conn.close()
        return

    # Compute deltas for every tracked series
    series_deltas = []
    for s in all_series:
        observations = get_observations(conn, s["series_id"], limit=260)
        if len(observations) < 2:
            continue
        delta = compute_series_delta(observations)
        delta["series_id"] = s["series_id"]
        delta["name"] = s["name"]
        delta["units"] = s.get("units")
        delta["category"] = s.get("category")
        series_deltas.append(delta)

    conn.close()

    if not series_deltas:
        console.print("[yellow]Not enough data for digest. Need at least 2 observations per series.[/yellow]")
        return

    movers = rank_movers(series_deltas)

    console.print(f"[bold]Step 3: AI interpretation…[/bold]\n")
    today = str(date.today())

    with console.status("[bold]Claude is reading the numbers…[/bold]"):
        result = interpret_digest(movers, today)

    if result:
        render_digest(
            headline=result.get("headline", f"Data Digest — {today}"),
            body=result.get("body", ""),
            movers=movers,
        )
    else:
        # Fall back to just showing movers without AI
        render_digest(
            headline=f"Data Digest — {today}",
            body="AI interpretation unavailable. Set ANTHROPIC_API_KEY for analysis.",
            movers=movers,
        )
