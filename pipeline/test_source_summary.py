"""
test_source_summary.py — Print a summary table of all configured sources.
"""

import os
import yaml

config_path = os.path.join(os.path.dirname(__file__), "config", "sources.yaml")
with open(config_path, encoding="utf-8") as f:
    data = yaml.safe_load(f)

sources = data.get("sources", [])

active   = [s for s in sources if s.get("active", True)]
inactive = [s for s in sources if not s.get("active", True)]

# ── By type ──────────────────────────────────────────────────────────────────
from collections import Counter, defaultdict
type_counts  = Counter(s.get("type", "rss") for s in active)
tier_counts  = Counter(s.get("tier", 2)     for s in active)
cat_counts   = Counter(s.get("category", "?") for s in active)

# ── Print ─────────────────────────────────────────────────────────────────────
W = 72
print("\n" + "═" * W)
print(f"  SOURCE INVENTORY  —  {len(active)} active  /  {len(inactive)} disabled  /  {len(sources)} total")
print("═" * W)

print(f"\n  By type:   " + "   ".join(f"{t}={n}" for t, n in sorted(type_counts.items())))
print(f"  By tier:   " + "   ".join(f"tier{t}={n}" for t, n in sorted(tier_counts.items())))
print(f"  By category:")
for cat, n in sorted(cat_counts.items(), key=lambda x: -x[1]):
    bar = "█" * n
    print(f"    {cat:<16} {n:2d}  {bar}")

# ── Active sources grouped by category ───────────────────────────────────────
by_cat = defaultdict(list)
for s in active:
    by_cat[s.get("category", "?")].append(s)

cat_order = ["geopolitics", "technology", "energy", "finance", "health",
             "science", "climate", "ecosystem", "materials", "social"]

print(f"\n{'─' * W}")
print(f"  ACTIVE SOURCES\n")
for cat in cat_order:
    srcs = by_cat.get(cat, [])
    if not srcs:
        continue
    print(f"  {cat.upper()}")
    for s in srcs:
        t   = s.get("type", "rss")
        tier = s.get("tier", 2)
        tag = {"rss": "RSS", "google_news": "GNews", "web_scrape": "Browser"}.get(t, t)
        print(f"    [{tag:<7} T{tier}]  {s['name']}")
    print()

# ── web_scrape sources callout ────────────────────────────────────────────────
ws = [s for s in active if s.get("type") == "web_scrape"]
if ws:
    print(f"{'─' * W}")
    print(f"  PLAYWRIGHT (web_scrape) SOURCES  — {len(ws)} total\n")
    for s in ws:
        print(f"    {s['name']}")
        print(f"      url     : {s['url']}")
        print(f"      pattern : {s.get('link_pattern', '(none)')}")
    print()

print("═" * W + "\n")
