"""
Probe every source in pipeline/config/sources.yaml against the live feed.

For each RSS source: fetch with httpx (strict timeout), parse with feedparser,
record entry count, freshness (any entry < FRESH_HOURS old), newest entry date,
HTTP status, errors, elapsed time.

Playwright-required sources are skipped with a note (probed separately later).

Output:
    research/probe_<YYYY-MM-DD>.json   structured machine-readable
    (this script does NOT write the markdown — that comes in a follow-up step)
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import httpx
import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCES_YAML = ROOT / "pipeline" / "config" / "sources.yaml"
TODAY = datetime.now(timezone.utc).date().isoformat()
OUT_JSON = ROOT / "research" / f"probe_{TODAY}.json"

TIMEOUT = 20
FRESH_HOURS = 72
MAX_WORKERS = 10

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; BrieferBot/1.0; +https://briefer.news) "
        "Feedparser/6.0"
    )
}

RSS_TYPES = {"rss", "rss_translate", "google_news"}
PLAYWRIGHT_TYPES = {
    "web_scrape", "playwright", "playwright_translate", "playwright_cloudflare"
}


def parse_entry_date(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        struct = entry.get(key)
        if struct:
            try:
                return datetime(*struct[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def probe_rss(url: str) -> dict:
    start = time.time()
    out = {
        "status": None,
        "http_status": None,
        "entry_count": 0,
        "fresh_count": 0,
        "newest_date": None,
        "newest_title": None,
        "is_fresh": False,
        "error": None,
        "elapsed_s": None,
    }
    try:
        with httpx.Client(timeout=TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
            resp = client.get(url)
            out["http_status"] = resp.status_code
            if resp.status_code != 200:
                out["status"] = f"http_{resp.status_code}"
                out["error"] = f"HTTP {resp.status_code}"
                out["elapsed_s"] = round(time.time() - start, 2)
                return out
            content = resp.content
        feed = feedparser.parse(content)
        entries = feed.entries
        out["entry_count"] = len(entries)
        if feed.bozo and not entries:
            out["status"] = "parse_error"
            out["error"] = str(feed.bozo_exception)[:200] if feed.bozo_exception else "malformed"
            out["elapsed_s"] = round(time.time() - start, 2)
            return out
        if not entries:
            out["status"] = "empty"
            out["elapsed_s"] = round(time.time() - start, 2)
            return out
        cutoff = datetime.now(timezone.utc) - timedelta(hours=FRESH_HOURS)
        fresh = []
        newest_date = None
        newest_title = None
        for e in entries:
            d = parse_entry_date(e)
            if d:
                if newest_date is None or d > newest_date:
                    newest_date = d
                    newest_title = e.get("title", "")[:160]
                if d >= cutoff:
                    fresh.append(e)
        out["fresh_count"] = len(fresh)
        out["newest_date"] = newest_date.isoformat() if newest_date else None
        out["newest_title"] = newest_title
        out["is_fresh"] = len(fresh) > 0
        out["status"] = "fresh" if out["is_fresh"] else ("stale" if newest_date else "no_dates")
    except httpx.TimeoutException:
        out["status"] = "timeout"
        out["error"] = f"timeout after {TIMEOUT}s"
    except httpx.RequestError as e:
        out["status"] = "request_error"
        out["error"] = type(e).__name__ + ": " + str(e)[:200]
    except Exception as e:
        out["status"] = "exception"
        out["error"] = type(e).__name__ + ": " + str(e)[:200]
    out["elapsed_s"] = round(time.time() - start, 2)
    return out


def probe_source(source: dict) -> dict:
    src_type = source.get("type", "rss")
    base = {
        "name": source["name"],
        "type": src_type,
        "category": source.get("category"),
        "tier": source.get("tier"),
        "url": source.get("url", ""),
        "active_in_yaml": source.get("active", True),
        "extractor": source.get("extractor"),
    }
    if src_type in PLAYWRIGHT_TYPES:
        base.update({
            "status": "skipped_playwright",
            "error": "requires Playwright — not probed in this run",
            "entry_count": 0, "fresh_count": 0, "is_fresh": False,
            "newest_date": None, "newest_title": None,
            "http_status": None, "elapsed_s": 0,
        })
        return base
    if src_type not in RSS_TYPES:
        base.update({
            "status": "unknown_type",
            "error": f"unrecognized type '{src_type}'",
            "entry_count": 0, "fresh_count": 0, "is_fresh": False,
            "newest_date": None, "newest_title": None,
            "http_status": None, "elapsed_s": 0,
        })
        return base
    probe = probe_rss(base["url"])
    base.update(probe)
    return base


def main():
    with open(SOURCES_YAML, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    sources = config.get("sources", [])
    print(f"Probing {len(sources)} sources (timeout={TIMEOUT}s, fresh<{FRESH_HOURS}h, workers={MAX_WORKERS})", flush=True)
    print("-" * 96, flush=True)

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(probe_source, s): s for s in sources}
        for fut in as_completed(futures):
            try:
                r = fut.result()
                results.append(r)
                status = r.get("status") or "?"
                marker = {
                    "fresh": "OK", "stale": "OLD", "empty": "EMPTY",
                    "no_dates": "NODATE", "timeout": "TIMEOUT",
                    "parse_error": "PARSE", "request_error": "NET",
                    "exception": "EXC", "skipped_playwright": "SKIP",
                    "unknown_type": "?TYPE",
                }.get(status, status[:8])
                if status.startswith("http_"):
                    marker = status.upper()
                err = ""
                if r.get("error"):
                    err = f" :: {r['error'][:80]}"
                print(f"  [{marker:>8}] {r['name']:48.48}  "
                      f"e={r.get('entry_count', 0):>3} f={r.get('fresh_count', 0):>2}  "
                      f"{r.get('elapsed_s', 0):>5}s{err}",
                      flush=True)
            except Exception as e:
                src = futures[fut]
                print(f"  [!ERR] {src['name']}  worker_error: {e}", flush=True)

    results.sort(key=lambda x: x["name"])
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "probe_date": TODAY,
            "probed_at": datetime.now(timezone.utc).isoformat(),
            "fresh_threshold_hours": FRESH_HOURS,
            "timeout_s": TIMEOUT,
            "total_sources": len(results),
            "results": results,
        }, f, indent=2, default=str)

    by_status: dict[str, int] = {}
    for r in results:
        s = r.get("status", "?")
        by_status[s] = by_status.get(s, 0) + 1
    print("\n" + "=" * 96)
    print(f"Total: {len(results)} sources")
    for status, count in sorted(by_status.items(), key=lambda x: -x[1]):
        print(f"  {status:>22}  {count:>3}")
    print(f"\nResults: {OUT_JSON}")


if __name__ == "__main__":
    main()
