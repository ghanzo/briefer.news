"""CLI entry point — all Click commands."""

import click

from briefer import __version__


@click.group()
@click.version_option(__version__, prog_name="briefer")
@click.option("--db", envvar="BRIEFER_DB_PATH", default=None, help="Path to DuckDB file")
@click.pass_context
def cli(ctx, db):
    """Briefer — economic data ingestion and AI analysis."""
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db


@cli.command()
@click.argument("source", required=False)
@click.option("--all", "pull_all", is_flag=True, help="Pull from all configured sources")
@click.option("--series", multiple=True, help="Specific series to pull (e.g. GDP, CPIAUCSL)")
@click.pass_context
def pull(ctx, source, pull_all, series):
    """Pull latest data from a source.

    Examples:
        briefer pull fred
        briefer pull fred --series GDP --series CPIAUCSL
        briefer pull --all
    """
    from briefer.commands.pull import run_pull
    run_pull(ctx.obj, source, pull_all, series)


@cli.command()
@click.argument("series_id")
@click.option("--periods", "-n", default=20, help="Number of recent observations to show")
@click.pass_context
def watch(ctx, series_id, periods):
    """Show a series with history, sparkline, and delta.

    Example:
        briefer watch fred/GDP
    """
    from briefer.commands.watch import run_watch
    run_watch(ctx.obj, series_id, periods)


@cli.command()
@click.option("--no-pull", is_flag=True, help="Skip data pull, analyze existing data only")
@click.pass_context
def digest(ctx, no_pull):
    """Run full pull + analysis. Show what moved today."""
    from briefer.commands.digest import run_digest
    run_digest(ctx.obj, no_pull)


@cli.command()
@click.argument("query")
@click.option("--source", "-s", default=None, help="Limit search to a specific source")
@click.option("--limit", "-n", default=20)
@click.pass_context
def search(ctx, query, source, limit):
    """Search available series across sources.

    Example:
        briefer search "oil production"
        briefer search "unemployment" --source fred
    """
    from briefer.commands.search import run_search
    run_search(ctx.obj, query, source, limit)


@cli.command()
@click.argument("target")
@click.option("--periods", "-n", default=20)
@click.pass_context
def analyze(ctx, target, periods):
    """Get AI interpretation of specific data.

    Example:
        briefer analyze fred/GDP
        briefer analyze energy
    """
    from briefer.commands.analyze import run_analyze
    run_analyze(ctx.obj, target, periods)


@cli.command()
@click.pass_context
def sources(ctx):
    """List configured sources and their status."""
    from briefer.commands.sources import run_sources
    run_sources(ctx.obj)


@cli.command()
@click.option("--no-open", is_flag=True, help="Generate dashboard without opening browser")
@click.pass_context
def dashboard(ctx, no_open):
    """Open a visual dashboard in your browser."""
    import webbrowser
    from rich.console import Console
    from briefer.display.dashboard import build_dashboard
    console = Console()
    with console.status("[bold]Building dashboard...[/bold]"):
        path = build_dashboard(ctx.obj.get("db_path"))
    console.print(f"Dashboard saved to {path}")
    if not no_open:
        webbrowser.open(path.as_uri())


@cli.command("export")
@click.argument("fmt", type=click.Choice(["markdown", "csv", "parquet"]))
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--series", multiple=True, help="Limit export to specific series")
@click.pass_context
def export_cmd(ctx, fmt, output, series):
    """Export data or analyses to markdown, CSV, or Parquet."""
    from briefer.commands.export import run_export
    run_export(ctx.obj, fmt, output, series)


@cli.command()
@click.option("--set", "set_key", nargs=2, metavar="KEY VALUE", help="Set a config value")
@click.option("--show", is_flag=True, help="Show current configuration")
@click.pass_context
def config(ctx, set_key, show):
    """Manage API keys and settings.

    Examples:
        briefer config --show
        briefer config --set FRED_API_KEY abc123
    """
    from briefer.commands.config import run_config
    run_config(ctx.obj, set_key, show)
