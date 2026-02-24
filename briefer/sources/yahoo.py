"""Yahoo Finance source adapter — indices, commodities, forex, ETFs."""

import logging
from datetime import date, timedelta

from briefer.sources.base import BaseSource, Observation, SeriesMeta

logger = logging.getLogger(__name__)


class YahooSource(BaseSource):
    name = "yahoo"
    display_name = "Yahoo Finance"
    requires_key = False
    env_key_name = ""

    def validate_config(self) -> bool:
        try:
            import yfinance  # noqa: F401
            return True
        except ImportError:
            logger.warning("yfinance not installed — run: pip install yfinance")
            return False

    def fetch_series_meta(self, source_key: str) -> SeriesMeta | None:
        try:
            import yfinance as yf
            ticker = yf.Ticker(source_key)
            info = ticker.info or {}
            name = info.get("longName") or info.get("shortName") or source_key
            return SeriesMeta(
                source_key=source_key,
                name=name,
                frequency="daily",
                units=info.get("currency", "USD"),
                seasonal_adj=None,
            )
        except Exception as e:
            logger.error(f"Yahoo metadata error for {source_key}: {e}")
            return None

    def fetch_observations(
        self,
        source_key: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Observation]:
        try:
            import yfinance as yf
            ticker = yf.Ticker(source_key)
            start = start_date or (date.today() - timedelta(days=730))
            end = end_date or date.today()
            df = ticker.history(start=start.isoformat(), end=end.isoformat())
            if df.empty:
                return []
            results = []
            for idx, row in df.iterrows():
                try:
                    d = idx.date() if hasattr(idx, 'date') else date.fromisoformat(str(idx)[:10])
                    val = float(row.get("Close", row.get("Adj Close", 0)))
                    if val > 0:
                        results.append(Observation(date=d, value=val))
                except (ValueError, TypeError):
                    continue
            return results
        except Exception as e:
            logger.error(f"Yahoo fetch error for {source_key}: {e}")
            return []

    def search(self, query: str, limit: int = 20) -> list[SeriesMeta]:
        # yfinance doesn't have a good search API
        # Return empty — users should use the catalog
        return []
