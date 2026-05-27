#!/usr/bin/env python3
"""
cloudflare_analytics.py — Pull Cloudflare Web Analytics (RUM) for briefer.news.

Real-browser traffic data via Cloudflare's GraphQL Analytics API. Captures
the cookieless JS-beacon-driven session data:
  - page loads + unique visit sessions
  - per-path breakdown
  - per-country breakdown
  - referrer hosts
  - device + browser splits

Complementary to scripts/traffic_report.py (which reads CloudFront logs
and captures EVERYTHING including bots). RUM = humans only.

Auth: CLOUDFLARE_API_TOKEN from .env (account token scoped to Analytics:Read).

Usage:
  python3 scripts/cloudflare_analytics.py                # 7-day window, stdout markdown
  python3 scripts/cloudflare_analytics.py --days 30      # custom window
  python3 scripts/cloudflare_analytics.py --json         # raw json instead of markdown
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.request
import urllib.error
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
SITE_TAG = "ac4470eaa68d4ed2adc6bf8d289ab14d"  # Cloudflare-internal site_tag for briefer.news


def load_env() -> dict[str, str]:
    env = {}
    f = REPO / ".env"
    if not f.exists():
        return env
    for line in f.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def query_rum(token: str, account: str, days: int) -> dict:
    end_dt = dt.datetime.utcnow()
    start_dt = end_dt - dt.timedelta(days=days)
    end = end_dt.isoformat() + "Z"
    start = start_dt.isoformat() + "Z"

    # Cloudflare's `rumPageloadEventsAdaptiveGroups` returns aggregated browser
    # page-load events (the JS beacon fires on every full page load). Fields:
    #   count = total page loads matching the dimensions
    #   visits = unique visit sessions (correlated to a single browser
    #            within ~30 min idle window per Cloudflare's RUM session logic)
    #   dimensions = the slicing axes we care about
    q = """
    query ($account: String!, $start: Time!, $end: Time!, $site: String!) {
      viewer {
        accounts(filter: {accountTag: $account}) {
          rumPageloadEventsAdaptiveGroups(
            limit: 1000
            filter: {datetime_geq: $start, datetime_leq: $end, siteTag: $site}
            orderBy: [count_DESC]
          ) {
            count
            dimensions {
              requestPath
              countryName
              refererHost
              deviceType
              userAgentBrowser
            }
          }
        }
      }
    }
    """
    body = json.dumps({
        "query": q,
        "variables": {"account": account, "start": start, "end": end, "site": SITE_TAG},
    }).encode()
    req = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/graphql",
        data=body, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    if data.get("errors"):
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    rows = data["data"]["viewer"]["accounts"][0]["rumPageloadEventsAdaptiveGroups"]
    return {
        "start": start, "end": end, "days": days,
        "rows": rows,
    }


def aggregate(rows: list[dict]) -> dict:
    """Aggregate raw group-by rows into per-dimension counters."""
    total = sum(r["count"] for r in rows)
    paths, countries, refs, devices, browsers = (Counter() for _ in range(5))
    for row in rows:
        d = row["dimensions"]
        c = row["count"]
        paths[d.get("requestPath") or "(none)"] += c
        countries[d.get("countryName") or "??"] += c
        host = d.get("refererHost") or ""
        if host and host != "briefer.news":  # skip internal nav
            refs[host] += c
        devices[d.get("deviceType") or "?"] += c
        browsers[d.get("userAgentBrowser") or "?"] += c
    return {
        "total_page_loads": total,
        "paths": paths,
        "countries": countries,
        "referrers": refs,
        "devices": devices,
        "browsers": browsers,
    }


def render_markdown(rum: dict, agg: dict) -> str:
    out = []
    out.append(f"# briefer.news — Cloudflare Web Analytics (humans only)")
    out.append(f"")
    out.append(f"Window: last {rum['days']} days ({rum['start'][:10]} → {rum['end'][:10]})")
    out.append(f"Source: Cloudflare RUM (JS beacon — bots excluded). Cross-reference")
    out.append(f"with CloudFront logs (traffic_report.py) for the bots+humans picture.")
    out.append(f"")
    out.append(f"**{agg['total_page_loads']} real-browser page load(s)** across {len(rum['rows'])} dimension groups.")
    out.append(f"")
    if agg["total_page_loads"] == 0:
        out.append("> No human page loads in this window. Either the beacon isn't firing")
        out.append("> (check the deployed JS), traffic is bot-only, or the audience is")
        out.append("> ad-blocking. Re-check after a few days of organic growth.")
        return "\n".join(out)

    out.append("## Top paths")
    out.append("| Path | Page loads |")
    out.append("|---|---:|")
    for p, n in agg["paths"].most_common(10):
        out.append(f"| `{p}` | {n} |")
    out.append("")

    out.append("## Countries")
    out.append("| Country | Page loads |")
    out.append("|---|---:|")
    for c, n in agg["countries"].most_common(10):
        out.append(f"| {c} | {n} |")
    out.append("")

    if agg["referrers"]:
        out.append("## Top external referrers")
        out.append("| Host | Page loads |")
        out.append("|---|---:|")
        for r, n in agg["referrers"].most_common(10):
            out.append(f"| {r} | {n} |")
        out.append("")
    else:
        out.append("## Top external referrers")
        out.append("(none in this window — all traffic is direct or internal)")
        out.append("")

    out.append(f"## Devices")
    out.append(f"  " + " · ".join(f"{d}={n}" for d, n in agg["devices"].most_common()))
    out.append(f"")
    out.append(f"## Browsers")
    out.append(f"  " + " · ".join(f"{b}={n}" for b, n in agg["browsers"].most_common(5)))
    return "\n".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--json", action="store_true", help="Emit raw JSON instead of markdown")
    args = ap.parse_args(argv)

    env = load_env()
    token = env.get("CLOUDFLARE_API_TOKEN")
    account = env.get("CLOUDFLARE_ACCOUNT_ID")
    if not token or not account:
        print("ERROR: CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID required in .env",
              file=sys.stderr)
        return 1

    try:
        rum = query_rum(token, account, args.days)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()[:300]}", file=sys.stderr)
        return 1

    agg = aggregate(rum["rows"])

    if args.json:
        # Convert Counters to plain dicts for JSON serialization
        agg_json = {
            "total_page_loads": agg["total_page_loads"],
            "paths": dict(agg["paths"].most_common()),
            "countries": dict(agg["countries"].most_common()),
            "referrers": dict(agg["referrers"].most_common()),
            "devices": dict(agg["devices"].most_common()),
            "browsers": dict(agg["browsers"].most_common()),
        }
        print(json.dumps({"window": rum, "aggregated": agg_json}, indent=2, default=str))
    else:
        print(render_markdown(rum, agg))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
