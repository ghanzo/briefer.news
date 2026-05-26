#!/usr/bin/env python3
"""
build_sources_page.py — Generate the public /sources/ page from the
three pipeline YAML configs (sources.yaml, akamai_sources.yaml,
china_sources.yaml). Lists ACTIVE sources only, grouped by edition
and editorial tier.

Self-contained: stdlib + a minimal YAML scanner (same approach used
in threads_today.py). No PyYAML dep on the host.

Output: .run/sources_page.html

Usage:
  python3 scripts/build_sources_page.py
"""

from __future__ import annotations

import html as html_lib
import re
import sys
from pathlib import Path
from string import Template

REPO = Path(__file__).resolve().parent.parent
RUN_DIR = REPO / ".run"
CONFIG_DIR = REPO / "pipeline" / "config"


# ── Minimal YAML scanner (tailored to our source-file structure) ───────────

def parse_sources_yaml(text: str) -> list[dict]:
    """Parse a sources YAML file with the structure:
       sources:
         - name: "..."
           type: ...
           url: "..."
           category: ...
           active: false  (optional; defaults true)
    Returns list of dicts.
    """
    entries: list[dict] = []
    current: dict | None = None
    inside_sources = False

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        # Skip blanks and comments
        if not stripped or stripped.startswith("#"):
            continue

        # Top-level: detect 'sources:' marker
        if re.match(r"^sources:\s*$", line):
            inside_sources = True
            continue
        if not inside_sources:
            continue

        # New entry starts with "  - name: ..." (2-space indent then "- ")
        m = re.match(r"^\s*-\s*name:\s*(.+?)\s*$", line)
        if m:
            if current is not None:
                entries.append(current)
            current = {"name": _unquote(m.group(1))}
            continue

        # Key within current entry
        m = re.match(r"^\s+([A-Za-z_]\w*):\s*(.*?)\s*$", line)
        if m and current is not None:
            key = m.group(1)
            val = _parse_value(m.group(2))
            current[key] = val
            continue

    if current is not None:
        entries.append(current)
    return entries


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def _parse_value(raw: str):
    raw = raw.strip()
    if raw == "" or raw.lower() == "null":
        return None
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    return _unquote(raw)


def is_active(entry: dict) -> bool:
    """active defaults to true unless explicitly false."""
    v = entry.get("active")
    if v is None:
        return True
    if isinstance(v, bool):
        return v
    return str(v).lower() not in ("false", "no", "0")


# ── Category labels & tier ordering ────────────────────────────────────────

US_TIER_LABELS = {
    1: "Tier 1 — primary federal",
    2: "Tier 2 — mainstream / regional",
    3: "Tier 3 — analysis / innovation",
}
US_CATEGORY_LABELS = {
    "geopolitics": "Geopolitics",
    "economy": "Economy",
    "security": "Security & enforcement",
    "energy": "Energy",
    "technology": "Technology",
    "science": "Science",
    "health": "Health",
    "defense": "Defense (DoD via Akamai-bypass)",
    "defense_allied": "Defense (allied)",
    "intelligence": "Intelligence",
    "foreign_policy_allied": "Foreign policy (allied)",
}

CHINA_CATEGORY_ORDER = [
    "diplomacy", "state_council", "state_media", "leadership",
    "economic_planning", "monetary", "fiscal", "industry_tech",
    "internet_data", "economic_data", "party_press", "party_theory",
    "discipline_inspection", "legislative", "judicial",
    "financial_reg", "state_owned", "commercial_business",
    "energy_reg", "provincial", "white_papers", "trade_data",
]
CHINA_CATEGORY_LABELS = {
    "diplomacy": "Foreign affairs (MFA + Foreign Minister)",
    "state_council": "State Council (policy + top news)",
    "state_media": "State media (Xinhua)",
    "leadership": "Top leadership beat",
    "economic_planning": "Economic planning (NDRC)",
    "monetary": "Monetary policy (PBOC)",
    "fiscal": "Fiscal policy (Ministry of Finance)",
    "industry_tech": "Industry / tech (MIIT)",
    "internet_data": "Internet & AI / data (CAC)",
    "economic_data": "Economic data (Stats Bureau)",
    "party_press": "Party press (People's Daily, CPC News)",
    "party_theory": "Party theory (Qiushi)",
    "discipline_inspection": "Anti-corruption (CCDI)",
    "legislative": "Legislative (NPC)",
    "judicial": "Judicial (Supreme Court + Procuracy)",
    "financial_reg": "Financial regulators (SAFE)",
    "state_owned": "State-owned enterprises (SASAC)",
    "commercial_business": "Commercial press (Caixin, Yicai)",
    "energy_reg": "Energy regulators (NEA, CEC)",
    "provincial": "Provincial governments",
    "white_papers": "State Council Information Office",
    "trade_data": "Customs / trade data",
}


# ── Render ──────────────────────────────────────────────────────────────────

def _domain_from(entry: dict, edition: str) -> str:
    """Best-effort domain extraction for display."""
    if "domain" in entry and entry["domain"]:
        return entry["domain"]
    url = entry.get("url") or entry.get("listing_url") or entry.get("api_url") or ""
    m = re.search(r"https?://([^/]+)", url)
    if m:
        return m.group(1)
    return ""


def render_us_section(entries: list[dict]) -> str:
    """US RSS sources grouped by tier and category. Active only."""
    active = [e for e in entries if is_active(e)]
    # Group by category
    by_cat: dict[str, list[dict]] = {}
    for e in active:
        cat = e.get("category", "other")
        by_cat.setdefault(cat, []).append(e)

    parts = []
    for cat, items in sorted(by_cat.items()):
        label = US_CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
        parts.append(f'<h4 class="src-cat">{label}</h4>')
        parts.append('<ul class="src-list">')
        for e in items:
            name = html_lib.escape(e["name"])
            domain = html_lib.escape(_domain_from(e, "us"))
            parts.append(f'<li><span class="src-name">{name}</span> <span class="src-domain">{domain}</span></li>')
        parts.append('</ul>')
    return "\n".join(parts)


def render_china_section(entries: list[dict]) -> str:
    active = [e for e in entries if is_active(e)]
    by_cat: dict[str, list[dict]] = {}
    for e in active:
        cat = e.get("category", "other")
        by_cat.setdefault(cat, []).append(e)

    # Order by CHINA_CATEGORY_ORDER, then any leftover alphabetically
    ordered_cats = [c for c in CHINA_CATEGORY_ORDER if c in by_cat]
    leftover = sorted(set(by_cat.keys()) - set(ordered_cats))
    parts = []
    for cat in ordered_cats + leftover:
        label = CHINA_CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
        parts.append(f'<h4 class="src-cat">{label}</h4>')
        parts.append('<ul class="src-list">')
        for e in by_cat[cat]:
            name = html_lib.escape(e["name"])
            domain = html_lib.escape(_domain_from(e, "china"))
            parts.append(f'<li><span class="src-name">{name}</span> <span class="src-domain">{domain}</span></li>')
        parts.append('</ul>')
    return "\n".join(parts)


PAGE_TPL = Template(r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="/favicon.ico" sizes="any">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">
  <title>Sources · Briefer News</title>
  <meta name="description" content="Active government primary-source feeds powering Briefer News. U.S. + China editions, grouped by editorial category.">
  <meta property="og:title" content="Sources · Briefer News">
  <meta property="og:description" content="Active government primary-source feeds powering Briefer News.">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://briefer.news/sources/">
  <link rel="canonical" href="https://briefer.news/sources/">
  <meta property="og:site_name" content="Briefer News">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root, body.theme-kraft {
      --paper: #F5EFE2;
      --ink: #1A1614;
      --ink-soft: #3D332C;
      --ink-light: #6B5D52;
      --sepia: #7A4F2E;
      --black: #14110F;
      --cream: #F2EBD9;
      --tagline: #C9BFA7;
    }
    * { box-sizing: border-box; }
    html, body {
      margin: 0; padding: 0;
      background: var(--paper); color: var(--ink);
      font-family: 'EB Garamond', Garamond, Georgia, serif;
      font-size: 21px; line-height: 1.55;
      -webkit-font-smoothing: antialiased;
      overflow-x: hidden;
    }
    header.masthead {
      background: var(--black); color: var(--cream);
      padding: 22px 24px 16px; text-align: center;
      border-bottom: 1px solid var(--ink);
    }
    header.masthead h1 {
      font-family: 'EB Garamond', Garamond, Georgia, serif;
      font-weight: 600;
      font-size: clamp(28px, 4.4vw, 44px);
      letter-spacing: 0.01em;
      margin: 0 0 6px; line-height: 1;
    }
    header.masthead p.tagline {
      font-style: italic; font-weight: 400;
      font-size: clamp(12px, 1.3vw, 14px);
      color: var(--tagline);
      letter-spacing: 0.02em;
      margin: 0;
    }
    main {
      max-width: 760px;
      margin: 0 auto;
      padding: 18px 24px 60px;
    }
    h2.page-title {
      font-family: 'EB Garamond', Garamond, Georgia, serif;
      font-size: clamp(28px, 3vw, 34px);
      font-weight: 500;
      line-height: 1.2;
      margin: 0 0 8px;
    }
    p.page-intro {
      color: var(--ink-light);
      max-width: 60ch;
      margin: 0 0 32px;
      font-size: 17px;
      line-height: 1.5;
      padding-top: 12px;
      position: relative;
    }
    p.page-intro::before {
      content: '';
      display: block;
      width: 40px; height: 2px;
      background: var(--sepia);
      margin: 0 0 12px;
    }
    p.page-intro b { color: var(--ink); font-weight: 600; }
    h3.edition-label {
      font-family: 'EB Garamond', Garamond, Georgia, serif;
      font-size: 26px;
      font-weight: 500;
      margin: 40px 0 6px;
    }
    p.edition-blurb {
      color: var(--ink-light);
      max-width: 64ch;
      margin: 0 0 18px;
      font-size: 17px;
    }
    h4.src-cat {
      font-family: 'IBM Plex Mono', ui-monospace, monospace;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--sepia);
      margin: 22px 0 8px;
      padding-bottom: 4px;
      border-bottom: 1px solid var(--ink-soft);
    }
    ul.src-list {
      list-style: none;
      padding: 0; margin: 0;
    }
    ul.src-list li {
      padding: 7px 0;
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      gap: 10px 20px;
      border-bottom: 1px dotted var(--ink-soft);
      font-size: 16px;
    }
    .src-name {
      color: var(--ink);
    }
    .src-domain {
      font-family: 'IBM Plex Mono', ui-monospace, monospace;
      font-size: 11px;
      letter-spacing: 0.06em;
      color: var(--ink-light);
    }
    footer.site-foot {
      margin-top: 48px;
      padding-top: 18px;
      border-top: 1px solid var(--ink-soft);
      display: flex;
      flex-wrap: wrap;
      gap: 8px 22px;
      font-family: 'IBM Plex Mono', ui-monospace, monospace;
      font-size: 11px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }
    footer.site-foot a {
      color: var(--sepia);
      text-decoration: none;
      border-bottom: 1px dotted var(--sepia);
    }
    footer.site-foot a:hover { border-bottom-style: solid; }
  </style>
</head>
<body class="theme-kraft">
  <header class="masthead">
    <h1>Briefer News</h1>
    <p class="tagline">Sources</p>
  </header>

  <main>
    <h2 class="page-title">Active sources</h2>
    <p class="page-intro"><b>This is the complete list of every source Briefer News reads from.</b> Each bullet, each voice, each dek traces back to one of these feeds. Government sources only: no wires, no analyst commentary, no aggregator inputs. Sources held back, blocked, or pruned do not appear here.</p>

    <h3 class="edition-label">U.S. edition</h3>
    <p class="edition-blurb">$US_COUNT active feeds across federal departments, financial regulators, the Federal Register, judicial filings, and four allied-government sources (UK MoD, NATO, Australia DFAT, Japan MoFA). Allied-government items publish in a separate "Allied Governments" block on the daily brief &mdash; never blended into the U.S.-federal Events list. DoD .mil subdomains (war.gov, CENTCOM, Navy, JCS, Air Force) reach via curl_cffi Chrome-impersonation; everything else via standard RSS or Playwright.</p>

    $US_SECTION

    <h3 class="edition-label">China edition</h3>
    <p class="edition-blurb">$CN_COUNT active Chinese-government feeds covering State Council policy releases, central regulators (NDRC, PBOC, MIIT, CAC), Party theoretical organs (Qiushi), judicial and discipline-inspection bodies (Supreme Court, Procuracy, CCDI), MFA daily press conferences, the PLA (MND and 81.cn), leadership-beat coverage from People's Daily and Xinhua, and provincial governments. All scraped via curl_cffi Chrome-impersonation.</p>

    $CN_SECTION

    <footer class="site-foot">
      <a href="/usa/">U.S. brief</a>
      <a href="/china/">China brief</a>
      <a href="/about/">About</a>
      <a href="https://github.com/ghanzo/briefer.news" target="_blank" rel="noopener">GitHub</a>
    </footer>
  </main>
</body>
</html>
""")


def main() -> int:
    us_main = parse_sources_yaml((CONFIG_DIR / "sources.yaml").read_text(encoding="utf-8"))
    us_akamai = parse_sources_yaml((CONFIG_DIR / "akamai_sources.yaml").read_text(encoding="utf-8"))
    china = parse_sources_yaml((CONFIG_DIR / "china_sources.yaml").read_text(encoding="utf-8"))

    us_all = us_main + us_akamai
    us_active = [e for e in us_all if is_active(e)]
    china_active = [e for e in china if is_active(e)]

    page = PAGE_TPL.substitute(
        US_COUNT=str(len(us_active)),
        CN_COUNT=str(len(china_active)),
        US_SECTION=render_us_section(us_all),
        CN_SECTION=render_china_section(china),
    )

    RUN_DIR.mkdir(exist_ok=True)
    out = RUN_DIR / "sources_page.html"
    out.write_text(page, encoding="utf-8")
    print(f"us:    {len(us_active)} active")
    print(f"china: {len(china_active)} active")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
