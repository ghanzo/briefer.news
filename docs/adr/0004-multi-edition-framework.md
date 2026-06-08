# 0004. Multi-edition framework (US + China)

- **Status:** Accepted
- **Date:** 2026-05-12
- **Commit(s):** e86334f (multi-edition restructure), e61234b, 8dd1e9f

## Context
A single US brief left obvious adjacent demand — China especially, which
out-performs the US page on search impressions. Hardcoding a second edition would
not scale to the editions we want (UK / EU / Russia).

## Decision
Restructure into a **per-edition framework**: selector at `/`, briefs at `/usa/`
and `/china/`, each with its own source list, style guide, synthesizer, and
LaunchAgents. China runs gov-only with Xi-first voices and ≤30-day recency.

## Consequences
- A new edition needs only: a source list, an edition style guide (like
  `CHINA_BRIEF.md`), LaunchAgents, and a deploy path.
- **Trade-off:** each edition multiplies the per-day `claude -p` calls → more
  pressure on the quota SPOF (ADR-0002). Editions scale coverage but not for free.
