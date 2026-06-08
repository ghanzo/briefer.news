# 0001. Government primary sources only

- **Status:** Accepted
- **Date:** 2026-05 (foundational; backfilled 2026-06-08)
- **Commit(s):** aa70baa (scaffold), db08290 (source expansion)

## Context
The space is crowded with secondary news aggregators. To be trustworthy and
defensible — and to occupy a niche no one else does — the brief needed a hard,
mechanically checkable sourcing rule, not "good editorial judgment."

## Decision
Every event and voice, in every edition, must trace to a **government primary
source** (`.gov` / `.gov.cn` / allied-gov). No wire copy, no opinion, no
aggregators. The picker gates on a source allowlist; trending non-gov stories are
deliberately excluded even when they dominate the news cycle.

## Consequences
- Trust + a unique position: "government data, synthesized."
- Verifiable by construction — `validate_brief.py` and the critique loop (ADR-0005)
  can check sourcing automatically.
- **Cost:** real stories with no gov primary source get dropped — e.g. the active
  U.S.–Iran war when CENTCOM's feed is broken. The rule is only as good as source
  coverage, which makes **scraper health load-bearing** (a down source = a blind
  spot, not just a missed item).
- Editorial rules live in `BRIEF_STYLE.md` (US) and `CHINA_BRIEF.md` (China).
