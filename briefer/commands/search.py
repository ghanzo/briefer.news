"""briefer search — search available series."""

from rich.console import Console

from briefer.display.tables import render_search_results
from briefer.sources.registry import get_source, get_all_sources

console = Console()


def run_search(ctx_obj: dict, query: str, source: str | None, limit: int) -> None:
    if source:
        try:
            src = get_source(source)
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            return

        if not src.validate_config():
            console.print(f"[yellow]{src.display_name}: API key not set[/yellow]")
            return

        results = src.search(query, limit=limit)
        render_search_results(results, source_name=src.display_name)
    else:
        # Search all sources that have keys configured
        for name, src in get_all_sources().items():
            if src.validate_config():
                results = src.search(query, limit=limit)
                if results:
                    render_search_results(results, source_name=src.display_name)
