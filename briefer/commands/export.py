"""briefer export — export data to markdown, CSV, or Parquet."""

from rich.console import Console

console = Console()


def run_export(ctx_obj: dict, fmt: str, output: str | None, series: tuple) -> None:
    console.print(f"[dim]Export to {fmt} — coming in Phase 2[/dim]")
