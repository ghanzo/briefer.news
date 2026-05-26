"""Delta detection, z-scores, trend analysis."""

from __future__ import annotations

import math
from datetime import date, timedelta


def compute_series_delta(observations: list[dict]) -> dict:
    """Compute change metrics from a list of observations (newest first).

    Returns dict with: latest_value, latest_date, prior_value, prior_date,
    absolute_change, percent_change, direction, z_score, trend,
    min_52w, max_52w, percentile_52w.
    """
    if not observations:
        return {}

    # Observations come newest-first from the DB query
    valid = [o for o in observations if o["value"] is not None]
    if not valid:
        return {}

    latest = valid[0]
    prior = valid[1] if len(valid) > 1 else None

    result = {
        "latest_value": latest["value"],
        "latest_date": latest["date"],
        "prior_value": prior["value"] if prior else None,
        "prior_date": prior["date"] if prior else None,
        "absolute_change": None,
        "percent_change": None,
        "direction": "flat",
        "z_score": None,
        "trend": "flat",
        "min_52w": None,
        "max_52w": None,
        "percentile_52w": None,
    }

    if prior:
        change = latest["value"] - prior["value"]
        result["absolute_change"] = change
        if prior["value"] != 0:
            result["percent_change"] = (change / abs(prior["value"])) * 100
        result["direction"] = "up" if change > 0 else "down" if change < 0 else "flat"

    # 52-week stats (approximate: use up to 260 daily or 52 weekly observations)
    values_52w = [o["value"] for o in valid[:260] if o["value"] is not None]
    if len(values_52w) >= 2:
        result["min_52w"] = min(values_52w)
        result["max_52w"] = max(values_52w)
        rng = result["max_52w"] - result["min_52w"]
        if rng > 0:
            result["percentile_52w"] = (latest["value"] - result["min_52w"]) / rng

    # Z-score relative to trailing history
    if len(values_52w) >= 10:
        mean = sum(values_52w) / len(values_52w)
        variance = sum((v - mean) ** 2 for v in values_52w) / len(values_52w)
        std = math.sqrt(variance)
        if std > 0:
            result["z_score"] = (latest["value"] - mean) / std

    # Trend detection (simple: compare first half mean to second half mean)
    if len(valid) >= 6:
        mid = len(valid) // 2
        recent_mean = sum(o["value"] for o in valid[:mid]) / mid
        older_mean = sum(o["value"] for o in valid[mid:mid * 2]) / mid
        diff = recent_mean - older_mean
        threshold = abs(older_mean) * 0.01 if older_mean != 0 else 0.01
        if diff > threshold:
            result["trend"] = "rising"
        elif diff < -threshold:
            result["trend"] = "falling"
        else:
            result["trend"] = "flat"

    return result


def rank_movers(series_deltas: list[dict]) -> list[dict]:
    """Rank series by magnitude of change (z-score first, then percent change)."""
    scored = []
    for d in series_deltas:
        z = abs(d.get("z_score") or 0)
        pct = abs(d.get("percent_change") or 0)
        score = z * 2 + pct  # weight z-score more heavily
        scored.append({**d, "_score": score})
    scored.sort(key=lambda x: x["_score"], reverse=True)
    return scored
