"""Rich table renderers for CLI output."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from briefer.display.formatters import format_delta, format_number, sparkline

console = Console()


def render_pull_summary(source_name: str, results: list[dict]) -> None:
    """Show summary of a data pull."""
    table = Table(title=f"Pull: {source_name}", show_lines=False)
    table.add_column("Series", style="bold")
    table.add_column("Name")
    table.add_column("Observations", justify="right")
    table.add_column("Latest Date", justify="right")
    table.add_column("Latest Value", justify="right")

    total_obs = 0
    for r in results:
        table.add_row(
            r["series_id"],
            r.get("name", ""),
            str(r.get("obs_count", 0)),
            str(r.get("latest_date", "—")),
            format_number(r.get("latest_value"), r.get("units")),
        )
        total_obs += r.get("obs_count", 0)

    console.print(table)
    console.print(f"\n  [dim]{len(results)} series, {total_obs} observations stored[/dim]\n")


def render_watch(meta: dict, observations: list[dict], delta: dict) -> None:
    """Render a detailed view of a single series."""
    # Header
    console.print()
    console.print(Panel(
        f"[bold]{meta['name']}[/bold]  [dim]({meta['series_id']})[/dim]\n"
        f"[dim]{meta.get('units', '')} · {meta.get('frequency', '')} · "
        f"{meta.get('seasonal_adj', '')}[/dim]",
        border_style="blue",
    ))

    # Sparkline
    if observations:
        values = [o["value"] for o in reversed(observations) if o["value"] is not None]
        if values:
            spark = sparkline(values, width=40)
            console.print(f"  {spark}  [dim]({len(values)} periods)[/dim]")

    # Key stats
    if delta:
        console.print()
        stats = Table(show_header=False, box=None, padding=(0, 2))
        stats.add_column("label", style="dim")
        stats.add_column("value", style="bold")
        stats.add_row("Latest", format_number(delta.get("latest_value"), meta.get("units")))
        stats.add_row("Date", str(delta.get("latest_date", "—")))
        stats.add_row("Change", format_delta(delta.get("absolute_change"), delta.get("percent_change")))
        stats.add_row("Direction", _direction_text(delta.get("direction", "flat")))
        if delta.get("z_score") is not None:
            z = delta["z_score"]
            z_style = "bold red" if abs(z) > 2 else "bold yellow" if abs(z) > 1 else "dim"
            stats.add_row("Z-score", Text(f"{z:+.2f}", style=z_style))
        if delta.get("min_52w") is not None:
            stats.add_row("52-wk range",
                          f"{format_number(delta['min_52w'], meta.get('units'))} — "
                          f"{format_number(delta['max_52w'], meta.get('units'))}")
        console.print(stats)

    # Recent observations table
    if observations:
        console.print()
        obs_table = Table(title="Recent Observations", show_lines=False)
        obs_table.add_column("Date", justify="right")
        obs_table.add_column("Value", justify="right")
        for obs in observations[:15]:
            obs_table.add_row(str(obs["date"]), format_number(obs["value"], meta.get("units")))
        console.print(obs_table)

    console.print()


def render_sources(sources_status: list[dict]) -> None:
    """List configured sources with status."""
    table = Table(title="Configured Sources")
    table.add_column("Source", style="bold")
    table.add_column("Name")
    table.add_column("API Key", justify="center")
    table.add_column("Series Tracked", justify="right")

    for s in sources_status:
        key_status = "[green]OK[/green]" if s["has_key"] else "[red]missing[/red]"
        table.add_row(s["name"], s["display_name"], key_status, str(s["series_count"]))

    console.print(table)
    console.print()


def render_search_results(results: list, source_name: str = "") -> None:
    """Display search results."""
    if not results:
        console.print("[dim]No results found.[/dim]")
        return

    table = Table(title=f"Search Results{f' ({source_name})' if source_name else ''}")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Frequency")
    table.add_column("Units")
    table.add_column("Seasonal Adj")

    for r in results:
        table.add_row(
            r.source_key,
            r.name,
            r.frequency or "—",
            (r.units or "—")[:40],
            r.seasonal_adj or "—",
        )

    console.print(table)
    console.print()


def render_digest(headline: str, body: str, movers: list[dict]) -> None:
    """Render the daily digest."""
    console.print()
    console.print(Panel(
        f"[bold]{headline}[/bold]",
        border_style="blue",
        title="Daily Digest",
    ))
    console.print()

    if movers:
        table = Table(title="Top Movers", show_lines=False)
        table.add_column("Series", style="bold")
        table.add_column("Value", justify="right")
        table.add_column("Change", justify="right")
        table.add_column("Z-score", justify="right")
        for m in movers[:10]:
            z = m.get("z_score")
            z_style = "bold red" if z and abs(z) > 2 else "bold yellow" if z and abs(z) > 1 else "dim"
            table.add_row(
                m.get("name", m.get("series_id", "")),
                format_number(m.get("latest_value"), m.get("units")),
                format_delta(m.get("absolute_change"), m.get("percent_change")),
                Text(f"{z:+.2f}" if z else "—", style=z_style),
            )
        console.print(table)

    console.print()
    for para in body.split("\n\n"):
        if para.strip():
            console.print(f"  {para.strip()}\n")
    console.print()


def _direction_text(direction: str) -> Text:
    styles = {"up": "green", "down": "red", "flat": "dim"}
    return Text(direction, style=styles.get(direction, ""))
