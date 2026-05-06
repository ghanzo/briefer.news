"""
Re-probe the HTTP 403 candidates from candidates_probe_2026-05-05.json
with browser-like headers. Many gov sites fingerprint feedparser/curl-style
User-Agent strings and block them at the WAF; a real-browser UA + Accept
headers may unlock them.

Output: research/blocked_probe_<DATE>.json
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import httpx

ROOT = Path(__file__).resolve().parent.parent
INPUT_JSON = ROOT / "research" / "candidates_probe_2026-05-05.json"
TODAY = datetime.now(timezone.utc).date().isoformat()
OUT_JSON = ROOT / "research" / f"blocked_probe_{TODAY}.json"

TIMEOUT = 25
FRESH_HOURS = 72
MAX_WORKERS = 8

# Browser-like headers — Chrome 121 on Windows 11
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def parse_entry_date(entry):
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        struct = entry.get(key)
        if struct:
            try:
                return datetime(*struct[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def probe_with_browser(url: str) -> dict:
    start = time.time()
    out = {
        "status": None, "http_status": None,
        "entry_count": 0, "fresh_count": 0,
        "newest_date": None, "newest_title": None,
        "is_fresh": False, "error": None, "elapsed_s": None,
    }
    try:
        with httpx.Client(timeout=TIMEOUT, headers=BROWSER_HEADERS, follow_redirects=True) as client:
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


def probe_one(item: dict) -> dict:
    name = item["name"]
    url = item["url"]
    section = item.get("section", "")
    flag = item.get("flag", "")
    result = probe_with_browser(url)
    return {
        "name": name,
        "section": section,
        "url": url,
        "flag": flag,
        "previous_status": item.get("status"),
        **result,
    }


def main():
    with open(INPUT_JSON, encoding="utf-8") as f:
        data = json.load(f)

    # Filter to only the HTTP 403 entries from the candidates probe
    blocked = [r for r in data["results"] if r.get("status") == "http_403"]
    print(f"Re-probing {len(blocked)} HTTP 403 candidates with browser-like headers", flush=True)
    print(f"  UA: Chrome 121 on Windows 11; full Accept + Sec-Fetch headers", flush=True)
    print("-" * 100, flush=True)

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(probe_one, item): item for item in blocked}
        for fut in as_completed(futures):
            try:
                r = fut.result()
                results.append(r)
                status = r.get("status") or "?"
                marker = {
                    "fresh": "OK", "stale": "OLD", "empty": "EMPTY",
                    "no_dates": "NODATE", "timeout": "TIMEOUT",
                    "parse_error": "PARSE", "request_error": "NET",
                    "exception": "EXC",
                }.get(status, status[:8])
                if status.startswith("http_"):
                    marker = status.upper()
                err = ""
                if r.get("error"):
                    err = f" :: {r['error'][:60]}"
                safe_name = r['name'].encode('ascii', errors='replace').decode('ascii')
                line = (f"  [{marker:>10}] {safe_name:42.42}  "
                        f"e={r.get('entry_count', 0):>3} f={r.get('fresh_count', 0):>2}  "
                        f"{r.get('elapsed_s', 0):>5}s{err}")
                try:
                    print(line, flush=True)
                except UnicodeEncodeError:
                    pass
            except Exception as e:
                item = futures[fut]
                try:
                    print(f"  [!ERR] {item['name']}  worker_error: {e}", flush=True)
                except UnicodeEncodeError:
                    pass

    results.sort(key=lambda x: x["name"])
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "probe_date": TODAY,
            "probed_at": datetime.now(timezone.utc).isoformat(),
            "fresh_threshold_hours": FRESH_HOURS,
            "headers_used": "browser-like (Chrome 121 / Win11)",
            "total_sources": len(results),
            "results": results,
        }, f, indent=2, default=str)

    by_status: dict[str, int] = {}
    for r in results:
        s = r.get("status", "?")
        by_status[s] = by_status.get(s, 0) + 1
    print("\n" + "=" * 100)
    print(f"Total: {len(results)} sources re-probed")
    for status, count in sorted(by_status.items(), key=lambda x: -x[1]):
        print(f"  {status:>22}  {count:>3}")
    unlocked = sum(1 for r in results if r.get("status") in ("fresh", "stale", "no_dates", "empty", "parse_error"))
    print(f"\nUnlocked (no longer 4xx): {unlocked}/{len(results)}")
    print(f"Results: {OUT_JSON}")


if __name__ == "__main__":
    main()
