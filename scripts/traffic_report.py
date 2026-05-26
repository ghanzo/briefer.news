#!/usr/bin/env python3
"""
traffic_report.py — Daily traffic snapshot from CloudFront access logs.

Reads CloudFront standard logs from s3://briefer-news-cf-logs/cflogs/,
aggregates yesterday's requests, and writes a markdown report (totals,
edition split, top pages, top referrers, status codes, bot vs human).

Pure server-side — no client tracking, no cookies, no IPs stored
beyond an aggregate unique-bucket count.

Usage:
  python3 scripts/traffic_report.py                       # yesterday
  python3 scripts/traffic_report.py --date 2026-05-25     # specific day
  python3 scripts/traffic_report.py --out report.md       # also save to file
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import re
import subprocess
import sys
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path


AWS = "/Users/maxgoshay/.local/bin/aws"
BUCKET = "briefer-news-cf-logs"
PREFIX = "cflogs/"
DIST_ID = "EMV1VIFYTSI3U"

# CloudFront standard-log field order (matches "#Fields:" header)
FIELDS = [
    "date", "time", "x-edge-location", "sc-bytes", "c-ip", "cs-method",
    "cs-host", "cs-uri-stem", "sc-status", "cs-referer", "cs-user-agent",
    "cs-uri-query", "cs-cookie", "x-edge-result-type", "x-edge-request-id",
    "x-host-header", "cs-protocol", "cs-bytes", "time-taken",
    "x-forwarded-for", "ssl-protocol", "ssl-cipher",
    "x-edge-response-result-type", "cs-protocol-version", "fle-status",
    "fle-encrypted-fields", "c-port", "time-to-first-byte",
    "x-edge-detailed-result-type", "sc-content-type", "sc-content-len",
    "sc-range-start", "sc-range-end",
]

BOT_PATTERNS = re.compile(
    r"bot|crawler|spider|slurp|bingpreview|googlebot|baiduspider|"
    r"yandex|duckduckbot|facebot|ia_archiver|semrush|ahrefsbot|"
    r"mj12bot|dotbot|petalbot|seekport|gptbot|chatgpt|claudebot|"
    r"oai-searchbot|perplexitybot",
    re.IGNORECASE,
)


def list_log_files(date: dt.date) -> list[str]:
    """List all CloudFront log files for a given date (UTC).
    Filename pattern: cflogs/<DistID>.YYYY-MM-DD-HH.<id>.gz"""
    prefix = f"{PREFIX}{DIST_ID}.{date.isoformat()}-"
    out = subprocess.check_output(
        [AWS, "s3api", "list-objects-v2",
         "--bucket", BUCKET,
         "--prefix", prefix,
         "--query", "Contents[].Key",
         "--output", "text"],
        text=True,
    ).strip()
    if not out or out == "None":
        return []
    return out.split()


def fetch_and_parse(key: str) -> list[dict]:
    """Download a gzipped log file from S3 and parse rows into dicts."""
    raw = subprocess.check_output(
        [AWS, "s3", "cp", f"s3://{BUCKET}/{key}", "-"],
    )
    text = gzip.decompress(raw).decode("utf-8", errors="replace")
    rows = []
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < len(FIELDS):
            parts = parts + [""] * (len(FIELDS) - len(parts))
        rows.append(dict(zip(FIELDS, parts)))
    return rows


def ip_bucket(ip: str) -> str:
    """Reduce IP to a /24-ish bucket so we count unique visitors without
    storing exact addresses. IPv4: zero last octet. IPv6: keep first 4 hextets."""
    if ":" in ip:
        return ":".join(ip.split(":")[:4]) + "::"
    parts = ip.split(".")
    if len(parts) == 4:
        return ".".join(parts[:3]) + ".0"
    return ip


def aggregate(rows: list[dict]) -> dict:
    total_requests = len(rows)
    total_bytes = 0
    ip_buckets: set[str] = set()
    edition_counts: Counter = Counter()
    edition_ips: dict[str, set[str]] = defaultdict(set)
    uri_counts: Counter = Counter()
    uri_ips: dict[str, set[str]] = defaultdict(set)
    referrer_counts: Counter = Counter()
    status_counts: Counter = Counter()
    bot_count = 0
    human_count = 0

    for r in rows:
        try:
            total_bytes += int(r.get("sc-bytes", "0") or "0")
        except ValueError:
            pass
        ip = r.get("c-ip", "")
        bucket = ip_bucket(ip) if ip else ""
        if bucket:
            ip_buckets.add(bucket)

        uri = urllib.parse.unquote(r.get("cs-uri-stem", ""))
        if uri.startswith("/usa/"):
            edition = "/usa/"
        elif uri.startswith("/china/"):
            edition = "/china/"
        elif uri == "/" or uri == "/index.html":
            edition = "(root)"
        elif uri.startswith("/about"):
            edition = "/about/"
        elif uri.startswith("/sources"):
            edition = "/sources/"
        elif uri.startswith("/favicon"):
            edition = "(favicon)"
        elif uri.endswith((".xml", ".txt")):
            edition = "(robots/sitemap/feed)"
        else:
            edition = "(other)"

        edition_counts[edition] += 1
        if bucket:
            edition_ips[edition].add(bucket)

        # Aggregate URIs but strip the dated-archive path for grouping
        uri_grouped = re.sub(r"/archive/\d{4}-\d{2}-\d{2}\.html$", "/archive/<dated>", uri)
        uri_counts[uri_grouped] += 1
        if bucket:
            uri_ips[uri_grouped].add(bucket)

        ref = urllib.parse.unquote(r.get("cs-referer", ""))
        if ref and ref not in ("-", ""):
            # Reduce to host
            try:
                host = urllib.parse.urlparse(ref).netloc
                if host:
                    referrer_counts[host] += 1
            except ValueError:
                pass

        try:
            status_counts[int(r.get("sc-status", "0"))] += 1
        except ValueError:
            pass

        ua = r.get("cs-user-agent", "")
        if BOT_PATTERNS.search(ua):
            bot_count += 1
        else:
            human_count += 1

    return {
        "total_requests": total_requests,
        "total_bytes": total_bytes,
        "unique_buckets": len(ip_buckets),
        "edition_counts": edition_counts,
        "edition_ips": {k: len(v) for k, v in edition_ips.items()},
        "uri_counts": uri_counts,
        "uri_ips": {k: len(v) for k, v in uri_ips.items()},
        "referrer_counts": referrer_counts,
        "status_counts": status_counts,
        "bot_count": bot_count,
        "human_count": human_count,
    }


def render(date: dt.date, agg: dict, log_count: int) -> str:
    out = []
    out.append(f"# briefer.news — Traffic snapshot for {date.isoformat()}")
    out.append("")
    out.append(f"*From {log_count} CloudFront log files. Server-side only — no client tracking.*")
    out.append("")

    if agg["total_requests"] == 0:
        out.append("## No traffic recorded\n")
        out.append("_Likely first run after enabling logging, or no logs delivered yet for this date._\n")
        return "\n".join(out)

    mb = agg["total_bytes"] / 1024 / 1024
    out.append("## Totals")
    out.append("")
    out.append("| Requests | Unique visitor buckets | Bytes served | Humans / Bots |")
    out.append("|---|---|---|---|")
    out.append(f"| {agg['total_requests']:,} | {agg['unique_buckets']:,} | {mb:.1f} MB | {agg['human_count']:,} / {agg['bot_count']:,} |")
    out.append("")

    out.append("## By edition / surface")
    out.append("")
    out.append("| Surface | Requests | Unique visitors |")
    out.append("|---|---|---|")
    for ed, count in agg["edition_counts"].most_common():
        ips = agg["edition_ips"].get(ed, 0)
        out.append(f"| {ed} | {count:,} | {ips:,} |")
    out.append("")

    out.append("## Top 15 pages")
    out.append("")
    out.append("| Page | Requests | Unique visitors |")
    out.append("|---|---|---|")
    for uri, count in agg["uri_counts"].most_common(15):
        ips = agg["uri_ips"].get(uri, 0)
        out.append(f"| `{uri}` | {count:,} | {ips:,} |")
    out.append("")

    if agg["referrer_counts"]:
        out.append("## Top 10 referrers")
        out.append("")
        out.append("| Referrer | Count |")
        out.append("|---|---|")
        for ref, count in agg["referrer_counts"].most_common(10):
            out.append(f"| {ref} | {count:,} |")
        out.append("")
    else:
        out.append("## Referrers\n\n_No external referrers in this window._\n")

    out.append("## Status codes")
    out.append("")
    out.append("| Status | Count |")
    out.append("|---|---|")
    for status, count in sorted(agg["status_counts"].items()):
        out.append(f"| {status} | {count:,} |")
    out.append("")

    return "\n".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", type=str, default=None,
                    help="Date to report on (YYYY-MM-DD). Defaults to yesterday.")
    ap.add_argument("--out", type=str, default=None,
                    help="Also write the report to this path.")
    args = ap.parse_args(argv)

    if args.date:
        date = dt.date.fromisoformat(args.date)
    else:
        date = dt.date.today() - dt.timedelta(days=1)

    print(f"Listing CloudFront logs for {date.isoformat()}...", file=sys.stderr)
    keys = list_log_files(date)
    print(f"Found {len(keys)} log files", file=sys.stderr)

    all_rows = []
    for k in keys:
        rows = fetch_and_parse(k)
        all_rows.extend(rows)

    agg = aggregate(all_rows)
    md = render(date, agg, len(keys))
    print(md)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
