"""briefer config — manage API keys and settings."""

import click
from rich.console import Console
from rich.table import Table

from briefer.config.settings import get_all_settings, set_key, KNOWN_KEYS

console = Console()


def run_config(ctx_obj: dict, set_key_pair: tuple | None, show: bool) -> None:
    if set_key_pair:
        key, value = set_key_pair
        key = key.upper()
        if key not in KNOWN_KEYS:
            console.print(f"[yellow]Warning: '{key}' is not a recognized key. Setting it anyway.[/yellow]")
        set_key(key, value)
        console.print(f"[green]Set {key}[/green]")
        return

    # Default: show config
    settings = get_all_settings()
    table = Table(title="Briefer Configuration")
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_column("Source", style="dim")

    for key, info in sorted(settings.items()):
        val = info["value"] or "[dim]not set[/dim]"
        table.add_row(key, str(val), info["source"])

    console.print(table)
    console.print(f"\n  [dim]Config file: ~/.briefer/config.yaml[/dim]")
    console.print(f"  [dim]Use: briefer config --set KEY VALUE[/dim]\n")
