# INDEX.md — root document map  *(as of 2026-05-28)*

Every `*.md` at the repo root, with a one-line purpose and a freshness tag.
Start with **`CLAUDE.md`** and `make status`.

**Tags:** `[LIVE]` describes the running system / binding rules — trust it ·
`[REFERENCE]` accurate background or a spec for an element that no longer
renders — read for context, not as live UI · `[PLANNED]` scoped but not built ·
`[STALE]` superseded; do not act on it.

| Doc | Tag | Purpose |
|---|---|---|
| `CLAUDE.md` | [LIVE] | Session orientation: the 16 LaunchAgents, autonomous synth, brief pipeline, ops tooling, deploy model. Rewritten + dated 2026-05-28. |
| `INDEX.md` | [LIVE] | This file — the root-doc map. |
| `README.md` | [LIVE] | Public-facing project overview: what it is, daily flow, architecture, status snapshot. |
| `BRIEF_STYLE.md` | [LIVE] | US editorial style guide — mandatory before any US synth. Note: its "Page structure" still lists a Dek (item 4) and Thread strip (item 5); **both were removed 2026-05-27** (flagged inline). |
| `CHINA_BRIEF.md` | [LIVE] | China-edition editorial framing, source list, synth architecture. Note: a few inline references to the dek and Day-N thread chips describe the removed UI (flagged inline). |
| `DEK.md` | [REFERENCE] | Plain-English, outcome-over-process synopsis rules. The on-page dek element was **removed 2026-05-27**; these rules now apply to the **top-3 event ledes**, not a separate dek block. |
| `WEEKLY.md` | [LIVE] | Voice + structure of the weekly digest (`/weekly/`); binding on the weekly synth. |
| `lens.md` | [LIVE] | Interpretive framework — the reader model and the six analytic layers. Load-bearing for all synthesis. |
| `MARKETING.md` | [LIVE] | Entry point for marketing/growth sessions (distribution, channels, voice). |
| `GROWTH.md` | [LIVE] | Researcher / Drafter / Analyzer growth-agent loop. In progress; Bluesky + X wire up on credentials/credits. |
| `EMAIL.md` | [LIVE] | Self-built email infra (SES + Postgres + custom template). In progress — Buttondown stays parallel until first real send. |
| `X_POSTING.md` | [REFERENCE] | X (Twitter) posting implementation state. Tabled 2026-05-22 pending API credits (note: a $25 credit was funded 2026-05-27 — see `MARKETING.md`/`x_cost_log.py`). |
| `HN_LAUNCH.md` | [PLANNED] | Show HN launch-post draft + timing. Hold until ready to post. |
| `CHINA_ALLIED.md` | [PLANNED] | Design spec for a non-PRC "Allied Governments"-equivalent section on the China brief. Scoped 2026-05-23, not implemented. |
| `CLEANUP.md` | [REFERENCE] | Known hygiene-only loose ends (e.g. inert GCP service account). None security-required. |

## Not at the root (moved)

- Historical plans + the M4 deployment runbook + source-planning docs
  (`AIMS.md`, `COVERAGE.md`, `MIGRATION.md`, `PLAN_*.md`, `SOURCES*.md`,
  `DESIGN_REFERENCES.md`, `aws-support-case-body.md`) now live under
  **`archive/docs/`**.
- The old econ-CLI predecessor lives under **`archive/briefer-cli/`**; legacy
  pipeline tests under `archive/pipeline-tests/`.
