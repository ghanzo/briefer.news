# 0006. Adopt ADRs + a Memex context graph

- **Status:** Superseded by [0007](0007-remove-memex-context-graph.md) (2026-06-08)
- **Date:** 2026-06-08
- **Commit(s):** this ADR set; `scripts/{memex_client,spend_tracker,status_tracker}.py`, `scripts/daily_memex.sh`

> **Superseded same day by ADR-0007.** The Memex context graph (daily loop +
> entrypoint + auto-notes) was removed; only the ADRs (this directory) were kept.
> This ADR is retained as the record of what was tried and why.

## Context
Onboarding a Claude session means re-scanning the repo to rebuild context — slow
and token-expensive. We want a curated **context graph** across three layers (past
= why, present = state, future = goals) that a session can read to orient cheaply,
shrinking context usage and cost.

## Decision
- **Past (why):** ADRs in `docs/adr/` — git-versioned, code-connected.
- **Present + Future + Spend:** rolling Memex notes (`Status`, `Goals`, `Spend`)
  written daily by `scripts/daily_memex.sh` (LaunchAgent `news.briefer.spend`,
  09:15) over the **raw MCP protocol — no `claude` call**, so the loop never
  consumes the synth's quota (ADR-0002).
- **Narrative:** dated context-graph notes in Memex linking decisions ↔ state ↔
  goals (Phase 3, still open).

## Consequences
- A session can read distilled context instead of re-deriving it → the whole point.
- Two homes for knowledge — repo ADRs vs living Memex notes — is deliberate
  (code-connected *why* vs auto-updated *state*); keep them cross-linked.
- The daily pulse adds ~$0.30/mo (Cost Explorer API calls) and zero Claude usage.
- Phase 3 (a single "context entrypoint" tying the layers together) remains to do.
