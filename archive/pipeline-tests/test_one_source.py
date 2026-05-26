"""
test_one_source.py — End-to-end sanity check on one source.

Loads sources.yaml, picks one source by name (default: BBC — World), runs the
real discovery + extraction code, and prints what comes out at each stage.

Usage:
  python test_one_source.py
  python test_one_source.py --source "State Dept — Press Releases"
  python test_one_source.py --source "Hacker News — Best Stories" --extract 1
  python test_one_source.py --list
"""

import argparse
import sys
from pathlib import Path

import yaml

from scraper.discovery import fetch_rss, discover_web_scrape
from scraper.extractor import extract_article

SOURCES_YAML = Path(__file__).parent / "config" / "sources.yaml"
RULE = "-" * 80

# Windows console defaults to cp1252; force utf-8 so feed titles with em-dashes,
# curly quotes, etc. don't crash the print calls.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_sources() -> list[dict]:
    with open(SOURCES_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)["sources"]


def pick_source(sources: list[dict], name: str) -> dict:
    matches = [s for s in sources if name.lower() in s["name"].lower()]
    if not matches:
        print(f"No source matched '{name}'. Use --list to see available names.")
        sys.exit(1)
    if len(matches) > 1:
        print(f"Ambiguous '{name}' — matched {len(matches)}:")
        for s in matches:
            print(f"  - {s['name']}")
        sys.exit(1)
    return matches[0]


def list_sources(sources: list[dict]) -> None:
    print(f"{'NAME':<55} {'TYPE':<14} {'TIER':<5} CATEGORY")
    print(RULE)
    for s in sources:
        active = "" if s.get("active", True) else " (inactive)"
        print(f"{s['name'] + active:<55} {s.get('type', 'rss'):<14} "
              f"{s.get('tier', 2):<5} {s.get('category', '')}")


def discover(source: dict) -> list[dict]:
    src_type = source.get("type", "rss")
    if src_type in ("rss", "google_news", "rss_translate"):
        return list(fetch_rss(source))
    if src_type in ("web_scrape", "playwright", "playwright_translate"):
        return list(discover_web_scrape(source))
    print(f"Unknown source type: {src_type}")
    sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="BBC — World",
                    help="Source name (substring match). Default: BBC — World")
    ap.add_argument("--extract", type=int, default=0,
                    help="Index of stub to fully extract (default 0 = first)")
    ap.add_argument("--list", action="store_true", help="List all sources and exit")
    ap.add_argument("--max-stubs", type=int, default=5, help="How many stubs to print")
    ap.add_argument("--preview", type=int, default=800,
                    help="Chars of extracted text to print")
    args = ap.parse_args()

    sources = load_sources()

    if args.list:
        list_sources(sources)
        return

    source = pick_source(sources, args.source)

    print(RULE)
    print(f"SOURCE     : {source['name']}")
    print(f"TYPE       : {source.get('type', 'rss')}")
    print(f"URL        : {source['url']}")
    print(f"TIER       : {source.get('tier', 2)}   CATEGORY: {source.get('category', '?')}")
    print(RULE)

    # ── Stage 1: discover stubs ──
    print("\n[1/2] DISCOVERY — fetching feed/listing...")
    stubs = discover(source)
    print(f"      → {len(stubs)} stubs")

    if not stubs:
        print("\nNo stubs returned. Feed may be empty or blocked.")
        return

    print(f"\nFirst {min(args.max_stubs, len(stubs))} stubs:")
    print(RULE)
    for i, stub in enumerate(stubs[:args.max_stubs]):
        date = stub["publish_date"].isoformat() if stub["publish_date"] else "no-date"
        inline = "  [inline-text]" if stub.get("full_text") else ""
        print(f"  [{i}] {date}{inline}")
        print(f"      {stub['title'][:100]}")
        print(f"      {stub['url'][:100]}")

    # ── Stage 2: extract one ──
    if args.extract >= len(stubs):
        print(f"\n--extract {args.extract} out of range (have {len(stubs)} stubs)")
        return

    target = stubs[args.extract]
    print(f"\n[2/2] EXTRACTION — full article for stub [{args.extract}]")
    print(RULE)
    print(f"Title : {target['title']}")
    print(f"URL   : {target['url']}")

    if target.get("full_text"):
        text = target["full_text"]
        method = target.get("extraction_method", "rss_inline")
        print(f"Source: feed already had full text ({method})")
    else:
        print(f"Fetching with extractor='{target.get('extractor', 'trafilatura')}'...")
        text, method = extract_article(target["url"], target.get("extractor", "trafilatura"))
        print(f"Method: {method}")

    if not text:
        print("\n[!] Extraction returned nothing.")
        return

    print(f"Length: {len(text)} chars")
    print(RULE)
    print(text[:args.preview])
    if len(text) > args.preview:
        print(f"\n... [{len(text) - args.preview} more chars truncated]")
    print(RULE)


if __name__ == "__main__":
    main()
