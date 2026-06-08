# 0005. Editorial self-critique loop

- **Status:** Accepted
- **Date:** 2026-06-03
- **Commit(s):** 7431c08 (Phase 1), 232ca58 (Phase 2), 740edd3 (freshness/world axes)

## Context
Brief quality drifted in ways only a human re-reading daily would catch — buried
high-value items, voice-register skew, single-agency over-indexing. We wanted
quality to compound without a human editing prompts every day.

## Decision
A daily **judgment loop** (`news.briefer.critique`, 14:00): Claude critiques the
published US brief against `BRIEF_STYLE.md` + the candidate pool across 7 axes,
writes `research/editorial_notes.md`, and the next 02:30 synth consumes those notes
as soft guidance. Advisory only — it never republishes or edits the style guide.

## Consequences
- Quality compounds, and the loop demonstrably **closes** (yesterday's notes change
  today's brief — verified).
- It surfaces recurring misses that soft notes alone can't fix (dropped CISA KEV
  items; the CENTCOM sourcing gap). Those should **escalate to hard gates**, not
  more notes — a pattern worth its own future ADR.
- Adds one more daily `claude -p` call to the shared quota (ADR-0002), but at 14:00,
  deliberately off-peak from the morning crunch.
