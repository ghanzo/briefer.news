#!/usr/bin/env python3
"""
search_report.py — Pull a Search Console performance snapshot for
briefer.news. Authenticates via Application Default Credentials
(set up via `gcloud auth application-default login --scopes=
https://www.googleapis.com/auth/webmasters,https://www.googleapis.com/
auth/cloud-platform`). Queries last-N-days impressions / clicks / top
queries / top pages and writes a markdown report to stdout.

The Domain property is keyed as "sc-domain:briefer.news" in the API.
Raw HTTP calls require an `X-Goog-User-Project` header to pin the
request to the correct GCP project (skillful-coast-288311) where the
Search Console API is enabled.

Usage:
  python3 scripts/search_report.py                  # 7 days, stdout
  python3 scripts/search_report.py --days 30        # custom window
  python3 scripts/search_report.py --out report.md  # also save to file
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import requests
import google.auth
from google.auth.transport.requests import Request


REPO = Path(__file__).resolve().parent.parent
SITE = "sc-domain:briefer.news"
API = "https://searchconsole.googleapis.com/webmasters/v3"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def get_credentials() -> tuple[str, str]:
    """Use Application Default Credentials — set by
    `gcloud auth application-default login`. Returns (access_token, quota_project).
    The quota_project is required by Search Console API on raw HTTP calls
    so the request is billed/quota'd against the right GCP project."""
    creds, project = google.auth.default(scopes=SCOPES)
    creds.refresh(Request())
    quota = creds.quota_project_id or project or "skillful-coast-288311"
    return creds.token, quota


def query(token: str, quota_project: str, body: dict) -> dict:
    """POST /sites/{siteUrl}/searchAnalytics/query."""
    site_enc = requests.utils.quote(SITE, safe="")
    url = f"{API}/sites/{site_enc}/searchAnalytics/query"
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json",
                 "X-Goog-User-Project": quota_project},
        json=body,
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(
            f"HTTP {r.status_code} from Search Console API:\n{r.text}"
        )
    return r.json()


def fmt_row(label: str, imp: float, clicks: float, ctr: float, pos: float) -> str:
    return f"| {label} | {int(imp):,} | {int(clicks):,} | {ctr*100:.2f}% | {pos:.1f} |"


def report(days: int) -> str:
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    token, quota_project = get_credentials()

    out = []
    out.append(f"# briefer.news — Search Console snapshot")
    out.append(f"")
    out.append(f"**Window:** {start.isoformat()} to {end.isoformat()} ({days} days)")
    out.append(f"**Property:** `{SITE}`")
    out.append(f"")

    # 1) Totals
    totals = query(token, quota_project, {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "rowLimit": 1,
    })
    rows = totals.get("rows", [])
    if not rows:
        out.append("## Totals\n\n_No data yet for this window. Google typically begins reporting Search Console metrics 2-3 days after first crawl, with full coverage building over 1-2 weeks._")
    else:
        r = rows[0]
        out.append("## Totals")
        out.append("")
        out.append("| Impressions | Clicks | CTR | Avg position |")
        out.append("|---|---|---|---|")
        out.append(f"| {int(r['impressions']):,} | {int(r['clicks']):,} | {r['ctr']*100:.2f}% | {r['position']:.1f} |")
    out.append("")

    # 2) Daily breakdown
    daily = query(token, quota_project, {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": ["date"],
        "rowLimit": days + 1,
    })
    daily_rows = daily.get("rows", [])
    if daily_rows:
        out.append("## Daily breakdown")
        out.append("")
        out.append("| Date | Impressions | Clicks | CTR | Avg pos |")
        out.append("|---|---|---|---|---|")
        for r in daily_rows:
            out.append(fmt_row(r["keys"][0], r["impressions"], r["clicks"], r["ctr"], r["position"]))
        out.append("")

    # 3) Top queries
    queries = query(token, quota_project, {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": ["query"],
        "rowLimit": 25,
    })
    q_rows = queries.get("rows", [])
    if q_rows:
        out.append("## Top queries (by impressions)")
        out.append("")
        out.append("| Query | Impressions | Clicks | CTR | Avg pos |")
        out.append("|---|---|---|---|---|")
        for r in q_rows:
            out.append(fmt_row(r["keys"][0], r["impressions"], r["clicks"], r["ctr"], r["position"]))
        out.append("")

    # 4) Top pages
    pages = query(token, quota_project, {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": ["page"],
        "rowLimit": 25,
    })
    p_rows = pages.get("rows", [])
    if p_rows:
        out.append("## Top pages")
        out.append("")
        out.append("| Page | Impressions | Clicks | CTR | Avg pos |")
        out.append("|---|---|---|---|---|")
        for r in p_rows:
            out.append(fmt_row(r["keys"][0], r["impressions"], r["clicks"], r["ctr"], r["position"]))
        out.append("")

    return "\n".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7, help="lookback window in days (default 7)")
    ap.add_argument("--out", type=str, help="also write the report to this path")
    args = ap.parse_args(argv)

    md = report(args.days)
    print(md)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
