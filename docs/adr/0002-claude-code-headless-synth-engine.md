# 0002. Claude Code (headless) as the synth engine

- **Status:** Accepted
- **Date:** 2026-05 (foundational; backfilled 2026-06-08)
- **Commit(s):** n/a (the original "Path B" plan, now fully shipped); see `scripts/synthesize.sh`

## Context
The picker, synthesizer, and world-context steps need a capable LLM every day. Two
options: (A) the Anthropic API, metered per token, or (B) the Claude Code
subscription run headless (`claude -p`). The project already pays for a Claude
**Max** plan ($100/mo).

## Decision
Use **Claude Code headless** as the primary engine for picker + synthesizer +
WebSearch. Keep the Anthropic API as a fallback (legacy `processor/` modules).

## Consequences
- **Cost:** ~$0 marginal per run against the flat $100/mo sub — which is ~97% of
  total project spend (`Projects/Briefer/Spend.md`).
- **Trade-off — the quota SPOF:** every daily script shares ONE subscription's
  quota. When the morning window is exhausted, the synth's `claude -p` calls block
  for hours; `synth_catchup` (13:05) exists to rescue this. This is the single
  biggest systemic risk in the system.
- **Open question this raises:** whether to move the synth to the metered API to
  decouple it from the sub quota — a cost-vs-reliability call the Spend tracker is
  explicitly meant to inform. (Future ADR if/when decided.)
