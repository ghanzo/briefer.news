#!/usr/bin/env python3
"""validate_brief.py — the post-synth editorial contract gate.

Why this exists: the synth produces a rendered brief HTML that is an unversioned
contract. A structurally broken brief (wrong stamp, missing headline, leaked
REMOVED section, a citation pointing at a source that does not exist, the wrong
canonical edition) is WORSE than no update — it ships garbage to subscribers and
poisons the archive. This gate runs AFTER the synth's existing `grep -q`
structural smoke check and BEFORE the S3 upload / CloudFront invalidate. If it
finds an ERROR, the wiring keeps yesterday's brief live (the synth's existing
exit-0-leave-yesterday pattern) rather than deploying a broken page.

Two tiers:
  ERRORS  — the brief is structurally broken; these BLOCK the deploy.
  WARNINGS — soft style misses; publish anyway but flag (a too-short headline
             is a WARNING, never an ERROR — today's 8-word US brief must ship).

Exit code: non-zero ONLY if there is >=1 ERROR. Warnings alone => exit 0.

Built on scripts/brief_parser.py (the single source of truth for reading a
brief). Stdlib only, no venv — matches the rest of scripts/.

Side effect: writes ${REPO}/.run/brief_proof_<edition>.txt with the parsed
summary (headline + the 5 visible ledes + counts) so the operator can eyeball
what was validated.

CLI:
    python3 scripts/validate_brief.py .run/usa_brief_today.html --edition us
    python3 scripts/validate_brief.py https://briefer.news/china/ --edition china
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from brief_parser import parse_file, parse_url  # noqa: E402

REPO = _HERE.parent
RUN_DIR = REPO / ".run"

# Canonical URL each edition must declare. A US brief that claims the /china/
# canonical (or vice-versa) is a cross-wiring bug that would index the wrong
# edition — a hard ERROR.
EXPECTED_CANONICAL = {
    "us": "https://briefer.news/usa/",
    "china": "https://briefer.news/china/",
}

# Sections that were REMOVED from the contract (2026-05-27). If the synth leaks
# one back into the RENDERED markup, it is a regression that ships stale content
# — a hard ERROR. Each entry: (human label, compiled detector).
#
# These match RENDERED ELEMENTS, never bare text: the prototype legitimately
# keeps the .backdrop / .fyp CSS rules (and their comments naming "Strategic
# Backdrop" / "Five-Year Plan") in the preserved <style> block, so a plain
# substring search would false-positive on every China brief. We only fire on
# the actual block markup the synth would emit if it leaked the section back.
_REMOVED_PATTERNS = [
    ("<ul class=\"dek-bullets\"> (removed dek-bullets block)",
     re.compile(r'<ul\s+class="dek-bullets"', re.I)),
    ("<p class=\"dek\"> (removed dek paragraph)",
     re.compile(r'<p\s+class="dek"', re.I)),
    ("<p class=\"thread-strip\"> (removed continuity strip)",
     re.compile(r'<p\s+class="thread-strip"', re.I)),
    ("<div class=\"backdrop\"> (removed Strategic Backdrop content)",
     re.compile(r'<div\s+class="backdrop"', re.I)),
    ("<article class=\"fyp\"> (removed Five-Year Plan block)",
     re.compile(r'<article\s+class="fyp"', re.I)),
]
# Edition-conditional removed sections: 'Strategic Backdrop' / 'Five-Year Plan'
# were removed from China 2026-05-27 and were never part of US. We flag them
# only when they appear as a RENDERED section heading — i.e. in the parsed
# <h3 class="section-label"> list — not when they merely appear as preserved
# CSS comment text in the <style> block.
_REMOVED_LABELS = ["Strategic Backdrop", "Five-Year Plan", "Five Year Plan"]


def _expected_stamp_variants(today: datetime.date) -> list[str]:
    """The synth renders the stamp in CAPS like 'MAY 28, 2026'. Allow both the
    zero-padded (%d -> '08') and non-padded ('8') day forms, since the prompt
    examples are inconsistent and either is acceptable."""
    mon = today.strftime("%b").upper()
    yr = today.year
    # dict.fromkeys dedupes while preserving order (the two forms collide for
    # 2-digit days like the 28th, differ for single-digit days like the 8th).
    return list(dict.fromkeys([f"{mon} {today.day:02d}, {yr}", f"{mon} {today.day}, {yr}"]))


def validate(d: dict, edition: str, today: datetime.date | None = None,
             raw_html: str | None = None) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for a parsed brief dict.

    `raw_html` is needed to detect leaked REMOVED sections (some live only in
    markup the parser intentionally drops). If omitted, those checks are skipped.
    """
    today = today or datetime.date.today()
    errors: list[str] = []
    warnings: list[str] = []
    ed = edition.lower()

    # ── ERRORS (block deploy) ───────────────────────────────────────────────

    # stamp != today
    stamp = (d.get("date") or "").strip()
    variants = _expected_stamp_variants(today)
    if stamp not in variants:
        errors.append(
            f"stamp '{stamp or '(empty)'}' is not today — expected one of {variants}")

    # headline empty
    headline = (d.get("headline") or "").strip()
    if not headline:
        errors.append("headline is empty")

    # events visible / more counts
    vis = d.get("events_visible_count", 0)
    more = d.get("events_more_count", 0)
    if vis != 5:
        errors.append(f"events_visible_count is {vis}, expected 5")
    if more != 4:
        errors.append(f"events_more_count is {more}, expected 4")

    # voices count
    nv = len(d.get("voices") or [])
    if nv != 6:
        errors.append(f"voices count is {nv}, expected 6")

    # sources empty
    sources = d.get("sources") or []
    if not sources:
        errors.append("sources bibliography is empty")

    # canonical != expected edition URL
    expected_canon = EXPECTED_CANONICAL.get(ed)
    canon = (d.get("canonical") or "").strip()
    if expected_canon is None:
        errors.append(f"unknown edition '{edition}' (expected us|china)")
    elif canon != expected_canon:
        errors.append(
            f"canonical '{canon or '(missing)'}' != expected {expected_canon}")

    # meta_description missing
    if not (d.get("meta_description") or "").strip():
        errors.append("meta_description is missing")

    # leaked REMOVED section present (rendered-element markup, not CSS comments)
    if raw_html is not None:
        for label, pat in _REMOVED_PATTERNS:
            if pat.search(raw_html):
                errors.append(f"leaked REMOVED section present: {label}")
    # leaked REMOVED section heading — check the PARSED section-label list only
    # (a rendered <h3 class="section-label">), never raw HTML, so preserved CSS
    # comments naming these sections do not false-positive.
    section_labels = d.get("section_labels") or []
    for lbl in _REMOVED_LABELS:
        if any(lbl in s for s in section_labels):
            errors.append(
                f"leaked REMOVED section present: '{lbl}' section heading "
                f"(removed 2026-05-27, not expected)")

    # max event cite marker numeral > number of numbered sources.
    # Only EVENT cites with numeric markers count (visible+more tiers — allied
    # uses letter markers). Numbered sources are those with digit markers (the
    # main 1-N <ol>; allied/outside-gate use lettered markers a,b,c). A numeral
    # higher than the bibliography length points at a source that does not exist.
    numbered_sources = [s for s in sources if str(s.get("marker", "")).isdigit()]
    n_numbered = len(numbered_sources)
    event_nums = [
        int(e["cite_marker"])
        for e in (d.get("events") or [])
        if e.get("tier") in ("visible", "more")
        and e.get("cite_marker")
        and str(e["cite_marker"]).isdigit()
    ]
    if event_nums:
        max_cite = max(event_nums)
        if max_cite > n_numbered:
            errors.append(
                f"max event cite marker {max_cite} > {n_numbered} numbered sources "
                f"(citation points at a source that does not exist)")

    # ── WARNINGS (publish anyway, but flag) ─────────────────────────────────

    # Headline length: the synth prompt mandates 5-8 words (one event), and
    # explicitly allows up to 10 when two events are joined by a semicolon. The
    # band here MUST match that — an earlier 12-16 target was a stale pre-2026-05
    # contract that made every prompt-compliant brief trip a false-positive WARN
    # (which emailed the operator on the same channel as real crit failures).
    hw = d.get("headline_words", 0)
    if ed == "us":
        if not (5 <= hw <= 10):
            warnings.append(
                f"US headline is {hw} words (style target 5-10) — publishing anyway")
    elif ed == "china":
        if not (5 <= hw <= 10):
            warnings.append(
                f"China headline is {hw} words (style target 5-10) — publishing anyway")

    return errors, warnings


def build_proof(d: dict, edition: str) -> str:
    """The eyeball summary written to .run/brief_proof_<edition>.txt: headline,
    the 5 visible ledes, and the structural counts the gate checked."""
    visible = [e for e in (d.get("events") or []) if e.get("tier") == "visible"]
    lines = [
        f"edition         : {edition}",
        f"stamp           : {d.get('date')}",
        f"canonical       : {d.get('canonical')}",
        f"headline        : {d.get('headline')}  ({d.get('headline_words')} words)",
        f"meta_description: {'present' if d.get('meta_description') else 'MISSING'}"
        f" ({len(d.get('meta_description') or '')} chars)",
        f"events          : {d.get('events_visible_count')} visible"
        f" + {d.get('events_more_count')} more",
        f"voices          : {len(d.get('voices') or [])}",
        f"sources         : {len(d.get('sources') or [])}",
        f"sections        : {', '.join(d.get('section_labels') or [])}",
        "",
        "Five visible event ledes:",
    ]
    for i, e in enumerate(visible, 1):
        lede = e.get("lead") or "(no lede)"
        lines.append(f"  {i}. {lede}")
    return "\n".join(lines) + "\n"


def _report(errors: list[str], warnings: list[str], edition: str, source: str) -> None:
    print("=" * 63)
    print(f"validate_brief — {edition} edition — {source}")
    print("=" * 63)
    if errors:
        print(f"ERRORS ({len(errors)}) — these BLOCK the deploy:")
        for e in errors:
            print(f"  [ERROR] {e}")
    else:
        print("ERRORS  : none")
    if warnings:
        print(f"WARNINGS ({len(warnings)}) — publish anyway, but flagged:")
        for w in warnings:
            print(f"  [WARN]  {w}")
    else:
        print("WARNINGS: none")
    verdict = "FAIL — keep yesterday's brief live" if errors else "PASS — ok to deploy"
    print("-" * 63)
    print(f"VERDICT : {verdict}")
    print("=" * 63)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Validate a rendered briefer.news brief against the editorial contract.")
    ap.add_argument("source", help="path to a rendered .html file or an http(s) URL")
    ap.add_argument("--edition", required=True, choices=["us", "china"],
                    help="which edition this brief is (drives canonical + headline checks)")
    ap.add_argument("--no-proof", action="store_true",
                    help="skip writing .run/brief_proof_<edition>.txt")
    args = ap.parse_args(argv)

    is_url = args.source.startswith("http")
    raw_html = None
    if is_url:
        d = parse_url(args.source)
    else:
        raw_html = Path(args.source).read_text(encoding="utf-8")
        d = parse_file(args.source)

    errors, warnings = validate(d, args.edition, raw_html=raw_html)
    _report(errors, warnings, args.edition, args.source)

    if not args.no_proof:
        try:
            RUN_DIR.mkdir(parents=True, exist_ok=True)
            proof_path = RUN_DIR / f"brief_proof_{args.edition}.txt"
            proof_path.write_text(build_proof(d, args.edition), encoding="utf-8")
            print(f"proof written: {proof_path}")
        except Exception as e:  # proof is best-effort; never fail the gate on it
            sys.stderr.write(f"could not write proof file: {e}\n")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
