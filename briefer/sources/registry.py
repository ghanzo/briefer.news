"""Source registry — maps names to adapter classes."""

from briefer.sources.base import BaseSource
from briefer.sources.fred import FREDSource
from briefer.sources.yahoo import YahooSource

SOURCES: dict[str, type[BaseSource]] = {
    "fred": FREDSource,
    "yahoo": YahooSource,
}


def get_source(name: str) -> BaseSource:
    cls = SOURCES.get(name)
    if cls is None:
        available = ", ".join(SOURCES.keys())
        raise ValueError(f"Unknown source: {name}. Available: {available}")
    return cls()


def get_all_sources() -> dict[str, BaseSource]:
    return {name: cls() for name, cls in SOURCES.items()}
