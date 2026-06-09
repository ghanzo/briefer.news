# 0007. Remove the Memex context graph; keep ADRs

- **Status:** Accepted
- **Date:** 2026-06-08
- **Supersedes:** 0006
- **Commit(s):** the change that removes `scripts/{spend_tracker,status_tracker,memex_client}.py`, `scripts/daily_memex.sh`, the `news.briefer.spend` LaunchAgent, and the CLAUDE.md entrypoint section

## Context
ADR-0006 adopted a three-layer context graph: ADRs (repo) + auto-updated Memex
notes (Status / Goals / Spend) + a context entrypoint. After building it, the
cost/benefit didn't hold up:
- The "cheaper orientation" benefit was modest — a session still reads the actual
  code it edits; the graph only saved the start-of-session re-learn.
- The Memex notes were a second home for knowledge and a maintenance surface, and
  the Status note largely duplicated `make status`.
- The hand-written layer drifts (CLAUDE.md was already stale), so the durable value
  was concentrated in the ADRs anyway.

## Decision
Keep **ADRs** (`docs/adr/`) as the project's decision log. **Remove** the rest of
the context graph: the daily Memex loop (`spend_tracker.py`, `status_tracker.py`,
`memex_client.py`, `daily_memex.sh`), the `news.briefer.spend` LaunchAgent, and the
CLAUDE.md "Context graph" entrypoint section. The Memex notes (Spend / Status /
Goals / Context) are retired — delete them from the Memex UI (there is no MCP
delete tool).

## Consequences
- Simpler: one home for the "why" (the repo), no extra daily agent, no Memex
  coupling for project state.
- **Lost:** the spend dashboard (re-addable from git if cost complexity grows — it
  showed ≈ $103/mo, ~97% the Claude Max subscription) and the auto goal/subscriber
  tracking.
- **Open finding it surfaced — still unaddressed:** only ~3 of ~47 email signups
  are confirmed. The signup→confirm **funnel**, not traffic, is the real bottleneck
  for the 30-subscriber goal. Worth a dedicated investigation.
- Everything removed is recoverable from git history (it briefly shipped under
  commits `accd7d7` / `eeefde9`).
