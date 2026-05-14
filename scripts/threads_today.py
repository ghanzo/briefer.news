#!/usr/bin/env python3
"""
threads_today.py — Resolve threads.yaml for today; emit per-edition chip strings.

Reads pipeline/config/threads.yaml. For each thread:
  - Skip if end_date set and < today
  - Skip if start_date > today (hasn't started yet)
  - Compute day count from start_date to today (inclusive)
  - Format the chip per display_format (day / month / year / event)

Writes one chip per line to:
  .run/threads_us.txt
  .run/threads_china.txt

Each chip is pre-formatted as `Day 76 · Iran war`. The synth wraps it in
HTML inside the prototype's continuity strip.

Self-contained — uses only stdlib (no PyYAML dep). Parses the specific
threads.yaml structure with a hand-rolled scanner.

Usage:
  python3 scripts/threads_today.py YYYY-MM-DD
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
THREADS_YAML = REPO / "pipeline" / "config" / "threads.yaml"
RUN_DIR = REPO / ".run"


def parse_threads(text: str) -> list[dict]:
    """Minimal YAML parser for the threads.yaml structure.

    Recognizes:
      - "  - id: <value>" → starts a new thread block
      - "    <key>: <value>" → adds a key to the current block
      - "[a, b]" list literal for editions
      - "null" → None
      - Comments (#...) and blank lines ignored
    """
    threads: list[dict] = []
    current: dict | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # New thread block
        m = re.match(r"  - id:\s*(.+?)\s*$", line)
        if m:
            if current is not None:
                threads.append(current)
            current = {"id": _unquote(m.group(1))}
            continue
        # Key within current thread
        m = re.match(r"    ([A-Za-z_]\w*):\s*(.*?)\s*$", line)
        if m and current is not None:
            key = m.group(1)
            val_raw = m.group(2)
            current[key] = _parse_value(val_raw)
            continue
    if current is not None:
        threads.append(current)
    return threads


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def _parse_value(raw: str):
    raw = raw.strip()
    if raw.lower() == "null" or raw == "":
        return None
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1]
        return [_unquote(x).strip() for x in inner.split(",") if x.strip()]
    return _unquote(raw)


def chip_for(t: dict, today: date) -> tuple[str, int] | None:
    start_str = t.get("start_date")
    if not start_str:
        return None
    start = datetime.strptime(start_str, "%Y-%m-%d").date()
    end_str = t.get("end_date")
    if end_str:
        end = datetime.strptime(end_str, "%Y-%m-%d").date()
        if end < today:
            return None
    days = (today - start).days + 1
    if days < 1:
        return None  # arc hasn't started yet
    fmt = t.get("display_format") or "day"
    name = t.get("name", t.get("id", "?"))
    if fmt == "day":
        chip = f"Day {days} · {name}"
    elif fmt == "month":
        # Calendar months elapsed since start, 1-indexed (Month 1 = arc's first month).
        months = (today.year - start.year) * 12 + (today.month - start.month)
        if today.day < start.day:
            months -= 1
        months = max(1, months + 1)
        chip = f"Month {months} · {name}"
    elif fmt == "year":
        # Calendar years elapsed since start, 1-indexed (Year 1 = arc's first year).
        years = today.year - start.year
        if (today.month, today.day) < (start.month, start.day):
            years -= 1
        years = max(1, years + 1)
        chip = f"Year {years} · {name}"
    elif fmt == "event":
        chip = name
    else:
        chip = f"Day {days} · {name}"
    return chip, days


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: threads_today.py YYYY-MM-DD", file=sys.stderr)
        return 2
    try:
        today = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    except ValueError as e:
        print(f"bad date: {e}", file=sys.stderr)
        return 2

    if not THREADS_YAML.exists():
        print(f"threads.yaml not found at {THREADS_YAML}", file=sys.stderr)
        return 1

    text = THREADS_YAML.read_text(encoding="utf-8")
    threads = parse_threads(text)

    resolved: list[tuple[str, int, list[str]]] = []
    for t in threads:
        result = chip_for(t, today)
        if result is None:
            continue
        chip, days = result
        editions = t.get("editions") or []
        if isinstance(editions, str):
            editions = [editions]
        resolved.append((chip, days, editions))

    # Freshest first (newest threads leftmost; longest-running rightmost)
    resolved.sort(key=lambda x: x[1])

    RUN_DIR.mkdir(exist_ok=True)
    for edition in ("us", "china"):
        out_path = RUN_DIR / f"threads_{edition}.txt"
        chips = [chip for chip, _days, editions in resolved if edition in editions]
        out_path.write_text("\n".join(chips) + ("\n" if chips else ""), encoding="utf-8")
        print(f"{edition}: {len(chips)} thread(s) → {out_path}")
        for c in chips:
            print(f"   {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
