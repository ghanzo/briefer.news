"""Base source adapter interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class SeriesMeta:
    """Metadata about a data series from a source."""
    source_key: str
    name: str
    frequency: str | None = None
    units: str | None = None
    seasonal_adj: str | None = None
    category: str | None = None


@dataclass
class Observation:
    """A single time-series data point."""
    date: date
    value: float | None


class BaseSource(ABC):
    """Interface that all source adapters must implement."""

    name: str = ""
    display_name: str = ""
    requires_key: bool = True
    env_key_name: str = ""

    @abstractmethod
    def validate_config(self) -> bool:
        """Check that API key is set and valid. Return True if ready."""
        ...

    @abstractmethod
    def fetch_series_meta(self, source_key: str) -> SeriesMeta | None:
        """Fetch metadata about a specific series from the API."""
        ...

    @abstractmethod
    def fetch_observations(
        self,
        source_key: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Observation]:
        """Fetch time-series observations for a series."""
        ...

    @abstractmethod
    def search(self, query: str, limit: int = 20) -> list[SeriesMeta]:
        """Search available series by keyword."""
        ...

    def make_series_id(self, source_key: str) -> str:
        return f"{self.name}/{source_key}"
