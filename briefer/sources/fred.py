"""FRED (Federal Reserve Economic Data) source adapter."""

import logging
import time
from datetime import date

import httpx

from briefer.config.settings import get_key
from briefer.sources.base import BaseSource, Observation, SeriesMeta

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.stlouisfed.org/fred"


class FREDSource(BaseSource):
    name = "fred"
    display_name = "Federal Reserve (FRED)"
    requires_key = True
    env_key_name = "FRED_API_KEY"

    def __init__(self):
        self._api_key = get_key("FRED_API_KEY")

    def validate_config(self) -> bool:
        return bool(self._api_key)

    def _get(self, endpoint: str, params: dict | None = None) -> dict | None:
        if not self._api_key:
            return None
        url = f"{_BASE_URL}/{endpoint}"
        p = {"api_key": self._api_key, "file_type": "json"}
        if params:
            p.update(params)
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(url, params=p)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("FRED rate limit hit — waiting 2s")
                time.sleep(2)
                return self._get(endpoint, params)
            logger.error(f"FRED API error {e.response.status_code}: {endpoint}")
            return None
        except Exception as e:
            logger.error(f"FRED request failed: {e}")
            return None

    def fetch_series_meta(self, source_key: str) -> SeriesMeta | None:
        data = self._get("series", {"series_id": source_key})
        if not data or "seriess" not in data or not data["seriess"]:
            return None
        s = data["seriess"][0]
        return SeriesMeta(
            source_key=source_key,
            name=s.get("title", source_key),
            frequency=_map_frequency(s.get("frequency_short", "")),
            units=s.get("units", ""),
            seasonal_adj=s.get("seasonal_adjustment_short", ""),
        )

    def fetch_observations(
        self,
        source_key: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Observation]:
        params: dict = {"series_id": source_key}
        if start_date:
            params["observation_start"] = start_date.isoformat()
        if end_date:
            params["observation_end"] = end_date.isoformat()

        data = self._get("series/observations", params)
        if not data or "observations" not in data:
            return []

        results = []
        for obs in data["observations"]:
            val_str = obs.get("value", ".")
            if val_str == "." or val_str is None:
                continue
            try:
                results.append(Observation(
                    date=date.fromisoformat(obs["date"]),
                    value=float(val_str),
                ))
            except (ValueError, KeyError):
                continue
        return results

    def search(self, query: str, limit: int = 20) -> list[SeriesMeta]:
        data = self._get("series/search", {
            "search_text": query,
            "limit": limit,
            "order_by": "popularity",
            "sort_order": "desc",
        })
        if not data or "seriess" not in data:
            return []
        results = []
        for s in data["seriess"][:limit]:
            results.append(SeriesMeta(
                source_key=s.get("id", ""),
                name=s.get("title", ""),
                frequency=_map_frequency(s.get("frequency_short", "")),
                units=s.get("units", ""),
                seasonal_adj=s.get("seasonal_adjustment_short", ""),
            ))
        return results


def _map_frequency(freq_short: str) -> str:
    return {
        "D": "daily", "W": "weekly", "BW": "biweekly",
        "M": "monthly", "Q": "quarterly", "SA": "semiannual",
        "A": "annual",
    }.get(freq_short, freq_short.lower() if freq_short else "unknown")
