#!/usr/bin/env python3
"""
morning_brief_gather.py — Pulls today's pipeline status + yesterday's
traffic + recent search-console data + healthcheck state into a single
JSON blob that the morning_brief.sh orchestrator hands to Claude for
synthesis.

No Claude calls here — pure data gathering. Outputs to
.run/morning_brief_data.json.

Usage:
  python3 scripts/morning_brief_gather.py
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from collections import Counter


REPO = Path(__file__).resolve().parent.parent
LOGS = REPO / "logs"
RUN = REPO / ".run"
RUN.mkdir(exist_ok=True)

TODAY = dt.date.today()
YESTERDAY = TODAY - dt.timedelta(days=1)
TODAY_LOG_TAG = TODAY.strftime("%Y%m%d")


# ── Pipeline log parsing ────────────────────────────────────────────────────

def parse_pipeline_log(name: str) -> dict:
    """Read a log file and surface its status + any error lines."""
    path = LOGS / f"{name}-{TODAY_LOG_TAG}.log"
    if not path.exists():
        return {"status": "missing", "exists": False, "tail": [], "errors": []}

    text = path.read_text(errors="replace")
    lines = text.splitlines()
    errors = [l for l in lines if re.search(r"\b(ERROR|FAIL|FAILED|Traceback)\b", l)][:10]

    # Status heuristics: look for end-of-script markers
    has_complete = any(re.search(r"complete[d]? at |Synthesis complete|finished|done", l, re.I) for l in lines[-20:])
    has_brief_produced = any("Brief HTML produced" in l for l in lines)
    has_uploaded = any("uploaded" in l for l in lines)

    status = "ok"
    if errors:
        status = "errors"
    elif not (has_complete or has_brief_produced or has_uploaded):
        status = "incomplete"

    return {
        "status": status,
        "exists": True,
        "size_bytes": path.stat().st_size,
        "errors": errors,
        "tail": lines[-15:],
    }


# ── Live brief structure check (what actually rendered) ────────────────────

def check_live_brief(edition: str) -> dict:
    """Curl the live brief and check key structural elements rendered."""
    url = f"https://briefer.news/{edition}/"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return {"reachable": False, "error": str(e)}

    # Extract date stamp to confirm it's today
    stamp_m = re.search(r'<div class="stamp">([^<]+)</div>', html)
    stamp = stamp_m.group(1) if stamp_m else "(none)"

    # Headline
    head_m = re.search(r'<h2 class="headline">([^<]+)</h2>', html)
    headline = head_m.group(1).strip() if head_m else "(none)"

    # Dek length
    dek_m = re.search(r'<p class="dek">([\s\S]+?)</p>', html)
    if dek_m:
        dek_text = re.sub(r"<[^>]+>", "", dek_m.group(1)).strip()
        dek_word_count = len(dek_text.split())
    else:
        dek_text, dek_word_count = "(none)", 0

    # Structural checks
    h3s = re.findall(r'<h3 class="section-label">([^<]+)</h3>', html)
    visible_events = len(re.findall(r'<ul class="items">[\s\S]*?</ul>', html))
    more_events_present = bool(re.search(r'<details class="more-events">', html))
    voices_present = bool(re.search(r'<div class="voices">', html))
    allied_present = "Allied Governments" in h3s
    outside_gate_present = "Outside the Gate" in h3s
    this_week_present = "This week" in h3s
    canonical_m = re.search(r'<link rel="canonical" href="([^"]+)">', html)
    canonical = canonical_m.group(1) if canonical_m else "(none)"

    return {
        "reachable": True,
        "stamp": stamp,
        "stamp_is_today": TODAY.strftime("%b ").upper().rstrip(" ") in stamp or TODAY.strftime("%B").upper() in stamp,
        "headline": headline[:200],
        "headline_words": len(headline.split()),
        "dek_first_120": dek_text[:120],
        "dek_word_count": dek_word_count,
        "section_labels": h3s,
        "voices_present": voices_present,
        "allied_present": allied_present,
        "outside_gate_present": outside_gate_present,
        "this_week_present": this_week_present,
        "more_events_collapsible_present": more_events_present,
        "canonical": canonical,
        "size_bytes": len(html),
    }


# ── CloudFront traffic (yesterday) ──────────────────────────────────────────

def gather_traffic() -> dict:
    """Run the existing traffic_report logic for yesterday, capture summary."""
    yest_str = YESTERDAY.isoformat()
    try:
        result = subprocess.run(
            ["/usr/bin/python3", str(REPO / "scripts" / "traffic_report.py"),
             "--date", yest_str],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            return {"status": "error", "error": result.stderr[-500:]}
        md = result.stdout
        # Extract structured numbers from the markdown
        totals_row = re.search(
            r"\| ([\d,]+) \| ([\d,]+) \| ([\d.]+ MB) \| ([\d,]+) / ([\d,]+) \|",
            md,
        )
        top_pages_block = re.search(r"## Top 15 pages[\s\S]+?(?=## |$)", md)
        top_refs_block = re.search(r"## Top 10 referrers[\s\S]+?(?=## |$)", md)
        return {
            "status": "ok",
            "date": yest_str,
            "totals_raw": totals_row.groups() if totals_row else None,
            "report_markdown": md,
            "report_size": len(md),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── Search console (latest weekly report) ──────────────────────────────────

def gather_search() -> dict:
    """Read the most-recent search-weekly file if present."""
    candidates = sorted(LOGS.glob("search-weekly-*.md"))
    if not candidates:
        return {"status": "missing"}
    latest = candidates[-1]
    return {
        "status": "ok",
        "date": latest.name.replace("search-weekly-", "").replace(".md", ""),
        "report_markdown": latest.read_text(errors="replace"),
    }


# ── Healthcheck ────────────────────────────────────────────────────────────

def gather_healthcheck() -> dict:
    path = LOGS / "healthcheck-launchagent.log"
    if not path.exists():
        return {"status": "missing"}
    text = path.read_text(errors="replace")
    tail = text.splitlines()[-30:]
    last_today = [l for l in tail if TODAY.isoformat() in l]
    last_fail = [l for l in tail if "FAIL" in l.upper()]
    return {
        "status": "ok" if last_today and not any("FAIL" in l.upper() for l in last_today) else "check",
        "today_lines": last_today,
        "any_fail_in_tail": last_fail[-3:],
    }


# ── Cron-runtime errors across all of today's logs ─────────────────────────

def gather_aws_costs() -> dict:
    """Pull AWS spend from the deployment account's Cost Explorer.
    Month-to-date by service + yesterday's daily by service. Cost Explorer
    is enabled in the deployment account (462170975634); the registrar
    account does not have CE enabled (one-time UI activation needed)."""
    aws_bin = "/Users/maxgoshay/.local/bin/aws"
    month_start = TODAY.strftime("%Y-%m-01")
    today_str = TODAY.isoformat()
    yest_str = YESTERDAY.isoformat()

    def query(period_start, period_end, granularity):
        try:
            out = subprocess.check_output(
                [aws_bin, "ce", "get-cost-and-usage",
                 "--time-period", f"Start={period_start},End={period_end}",
                 "--granularity", granularity,
                 "--metrics", "UnblendedCost",
                 "--group-by", "Type=DIMENSION,Key=SERVICE",
                 "--output", "json"],
                text=True, timeout=30,
            )
            data = json.loads(out)
            groups = data.get("ResultsByTime", [{}])[0].get("Groups", [])
            by_service = {
                g["Keys"][0]: float(g["Metrics"]["UnblendedCost"]["Amount"])
                for g in groups
            }
            total = sum(by_service.values())
            return {"total_usd": round(total, 2),
                    "by_service": {k: round(v, 4) for k, v in by_service.items() if v > 0}}
        except Exception as e:
            return {"error": str(e)[:200]}

    return {
        "deployment_account": {
            "month_to_date": query(month_start, today_str, "MONTHLY"),
            "yesterday": query(yest_str, today_str, "DAILY"),
        },
        "registrar_account": "Cost Explorer not enabled (User not enabled for cost explorer access). Enable once in the Billing console → Cost Explorer → Launch. Until then, domain renewal cost is the known annual line item (~$15/year for briefer.news, renews 2026-08-08).",
        "known_offsite_costs": {
            "anthropic_claude_api": "Estimated $15-30/day in synth + morning-brief usage. No public billing API; check console.anthropic.com manually for actual.",
            "cloudflare": "Free tier (Web Analytics only — no DNS routing).",
            "buttondown": "Free tier until 100+ subscribers ($9/mo above).",
            "github": "Free (public repo).",
        },
    }


# ── Site-quality scoring ────────────────────────────────────────────────────
# Mechanical checks of today's published briefs against the binding specs
# (DEK.md, BRIEF_STYLE.md, CHINA_BRIEF.md, the page-structure expectations).
# Each check is binary — easy to compute, easy to trend day-over-day.

DEK_BANNED_PATTERNS = [
    # Template openers (DEK.md hard rules)
    (r"\bthreads through\b",       "template opener: 'X threads through today'"),
    (r"\bsits behind every\b",     "template opener: 'X sits behind every move'"),
    (r"\bmeets [A-Z][a-z]+'s? .{1,40}from a posture of\b", "template opener: 'X meets Y from a posture of Z'"),
    # Interpretive framings caught from the 2026-05-26 worked example
    (r"\banswers with\b",          "interpretive verb: 'X answers with Y'"),
    (r"\bresponds with\b",         "interpretive verb: 'X responds with Y'"),
    (r"\barrives the same week as\b", "interpretive grouping: 'arrives the same week as'"),
    (r"\bcomes as\b",              "interpretive grouping: 'X comes as Y'"),
    (r"\baimed less at .+ than at\b", "intent attribution: 'aimed less at X than at Y'"),
    (r"\bnow treats\b",            "interpretive characterization: 'now treats X as Y'"),
    (r"\bnow views\b",             "interpretive characterization: 'now views X as Y'"),
    (r"\bincreasingly sees\b",     "interpretive characterization: 'increasingly sees X as Y'"),
    # Hedge constructions
    (r"\bwhile .+ even .+\b",      "hedge construction: 'while X even Y'"),
    (r"\beven as\b",               "hedge construction: 'even as'"),
    # Doctrine name-drops (DEK.md banned)
    (r"\bnew quality productive forces\b|NQPF\b", "doctrine name-drop: NQPF"),
    (r"\b15th? Five-Year Plan\b|\b15FYP\b",       "doctrine name-drop: 15FYP"),
    (r"\bdual circulation\b",      "doctrine name-drop: dual circulation"),
    (r"\bcommon prosperity\b",     "doctrine name-drop: common prosperity"),
    (r"\bMade in China 2025\b|\bMIC2025\b",       "doctrine name-drop: MIC2025"),
    (r"\b30/60\b",                 "doctrine name-drop: 30/60 carbon"),
]


def score_brief(brief: dict, edition: str) -> dict:
    """Score today's brief on mechanical site-quality criteria. Returns a
    dict of {check: pass/fail/skipped} plus an aggregate score."""
    if not brief.get("reachable"):
        return {"reachable": False}

    checks = {}

    # 1) Dek factual-framing check — scan first 600 chars for banned patterns
    dek_text = brief.get("dek_first_120", "") + " "  # ideally the full dek, but first_120 is what we capture
    # If we have a fuller dek excerpt, prefer it
    full_dek = brief.get("dek_text") or dek_text
    hits = []
    for pattern, label in DEK_BANNED_PATTERNS:
        if re.search(pattern, full_dek, re.IGNORECASE):
            hits.append(label)
    checks["dek_no_banned_patterns"] = {
        "pass": len(hits) == 0,
        "hits": hits,
    }

    # 2) Dek word count in DEK.md range (30-55)
    dwc = brief.get("dek_word_count", 0)
    checks["dek_word_count_30_55"] = {"pass": 30 <= dwc <= 55, "actual": dwc}

    # 3) Headline word count per BRIEF_STYLE.md
    # US: 12-16. China: ≤12 (per CHINA_BRIEF.md, HARD MAX 12 WORDS).
    hwc = brief.get("headline_words", 0)
    if edition == "us":
        checks["headline_words_12_16"] = {"pass": 12 <= hwc <= 16, "actual": hwc}
    else:
        checks["headline_words_le_12"] = {"pass": 1 <= hwc <= 12, "actual": hwc}

    # 4) Structural integrity
    checks["voices_present"] = {"pass": brief.get("voices_present", False)}
    checks["more_events_present"] = {"pass": brief.get("more_events_collapsible_present", False)}
    checks["this_week_present"] = {"pass": brief.get("this_week_present", False)}
    if edition == "us":
        checks["allied_present"] = {"pass": brief.get("allied_present", False),
                                    "note": "conditional — omitted on days with no allied material; this is expected to vary"}
    else:
        checks["outside_gate_present"] = {"pass": brief.get("outside_gate_present", False),
                                          "note": "conditional — sources currently parked, expected absent until direct scrapers ship"}

    # 5) Canonical declares the live URL
    expected_canonical = f"https://briefer.news/{'usa' if edition == 'us' else 'china'}/"
    checks["canonical_correct"] = {
        "pass": brief.get("canonical") == expected_canonical,
        "expected": expected_canonical,
        "actual": brief.get("canonical", "(none)"),
    }

    # 6) Stamp is today
    checks["stamp_is_today"] = {"pass": brief.get("stamp_is_today", False),
                                "actual": brief.get("stamp", "(none)")}

    # Aggregate score — % of non-conditional checks passing
    countable = [v for k, v in checks.items()
                 if k not in ("allied_present", "outside_gate_present")
                 and isinstance(v, dict) and "pass" in v]
    passed = sum(1 for c in countable if c["pass"])
    score_pct = round(100 * passed / len(countable), 1) if countable else 0.0

    return {
        "reachable": True,
        "checks": checks,
        "score_pct": score_pct,
        "passed": passed,
        "total_countable": len(countable),
    }


def gather_reminders() -> list[str]:
    """Read .run/reminders.json (a date -> [messages] map) and return
    any reminders whose date matches today. Lets the operator schedule
    one-off "do this on date X" nudges that surface in the morning brief
    on the matching day.

    File format:
      { "2026-05-31": ["Downgrade AWS Business+...", "..."] }

    Missing file or no entry for today = empty list. Returns text
    strings; the brief synthesizer surfaces them in a "## Reminders for
    today" section if non-empty."""
    path = REPO / ".run" / "reminders.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data.get(TODAY.isoformat(), [])
    except Exception:
        return []


def scan_today_errors() -> list[str]:
    """Sweep today's log files for any ERROR / FAIL / Traceback lines."""
    seen: list[str] = []
    for f in LOGS.glob(f"*-{TODAY_LOG_TAG}*.log"):
        for line in f.read_text(errors="replace").splitlines():
            if re.search(r"\b(ERROR|FAIL|FAILED|Traceback|exception)\b", line, re.I):
                seen.append(f"{f.name}: {line.strip()[:200]}")
    return seen[:30]


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    data = {
        "generated_at": dt.datetime.now().isoformat(),
        "today": TODAY.isoformat(),
        "yesterday": YESTERDAY.isoformat(),
        "pipeline": {
            "scrape":      parse_pipeline_log("daily"),
            "us_synth":    parse_pipeline_log("synthesize"),
            "china_synth": parse_pipeline_log("synthesize-china"),
            "digests":     parse_pipeline_log("daily-digests"),
            "weekly":      parse_pipeline_log("weekly"),
            "healthcheck": gather_healthcheck(),
        },
        "live_briefs": {
            "us":    check_live_brief("usa"),
            "china": check_live_brief("china"),
        },
        "site_quality": {},  # filled below — score AFTER live_briefs collected
        "traffic":   gather_traffic(),
        "search":    gather_search(),
        "costs":     gather_aws_costs(),
        "reminders_for_today": gather_reminders(),
        "errors_today": scan_today_errors(),
    }

    # Score the live briefs against site-quality checks
    data["site_quality"] = {
        "us":    score_brief(data["live_briefs"]["us"], "us"),
        "china": score_brief(data["live_briefs"]["china"], "china"),
    }

    out = RUN / "morning_brief_data.json"
    out.write_text(json.dumps(data, indent=2, default=str))
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
