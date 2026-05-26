"""briefer analyze — AI interpretation of data."""

from rich.console import Console
from rich.panel import Panel

from briefer.analysis.deltas import compute_series_delta
from briefer.analysis.interpret import interpret_series
from briefer.db.connection import get_connection
from briefer.db.queries import get_series_meta, get_observations, get_all_series
from briefer.display.tables import render_watch

console = Console()


def run_analyze(ctx_obj: dict, target: str, periods: int) -> None:
    conn = get_connection(ctx_obj.get("db_path"))

    # Check if target is a series_id (contains /) or a category
    if "/" in target:
        _analyze_series(conn, target, periods)
    else:
        _analyze_category(conn, target, periods)

    conn.close()


def _analyze_series(conn, series_id: str, periods: int) -> None:
    meta = get_series_meta(conn, series_id)
    if not meta:
        console.print(f"[red]Series '{series_id}' not found. Run 'briefer pull' first.[/red]")
        return

    observations = get_observations(conn, series_id, limit=max(periods, 260))
    if not observations:
        console.print(f"[yellow]No observations for {series_id}.[/yellow]")
        return

    delta = compute_series_delta(observations)
    render_watch(meta, observations[:periods], delta)

    with console.status("[bold]Asking Claude for interpretation…[/bold]"):
        analysis = interpret_series(meta, delta, observations[:periods])

    if analysis:
        console.print(Panel(analysis, title="AI Analysis", border_style="green"))
    else:
        console.print("[yellow]AI analysis unavailable (check ANTHROPIC_API_KEY)[/yellow]")


def _analyze_category(conn, category: str, periods: int) -> None:
    all_series = get_all_series(conn)
    matching = [s for s in all_series if s.get("category") == category]

    if not matching:
        console.print(f"[red]No series found in category '{category}'.[/red]")
        console.print("[dim]Available categories:[/dim]")
        cats = sorted(set(s.get("category", "") for s in all_series if s.get("category")))
        for c in cats:
            console.print(f"  {c}")
        return

    console.print(f"\n[bold]Category: {category}[/bold] ({len(matching)} series)\n")

    for s in matching:
        observations = get_observations(conn, s["series_id"], limit=max(periods, 260))
        if observations:
            delta = compute_series_delta(observations)
            render_watch(s, observations[:periods], delta)
