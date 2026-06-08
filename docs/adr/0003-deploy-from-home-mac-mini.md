# 0003. Deploy from the home M4 Mac mini (residential IP)

- **Status:** Accepted
- **Date:** 2026-05 (foundational; backfilled 2026-06-08)
- **Commit(s):** db08290, de66583 (Akamai bypass), 607f91a (CENTCOM live); see `MIGRATION.md`

## Context
Several high-value sources (DoD `.mil`, allied gov) sit behind Akamai. The free
bypass — `curl_cffi` + Chrome TLS impersonation — works only from a **residential
IP**; it fails from cloud datacenter IPs. The alternative is a paid residential
proxy (~$50–100/mo).

## Decision
Run the whole pipeline (scrape → synth → deploy) on the **home M4 Mac mini** and
publish to AWS S3 + CloudFront from there. AWS holds only static hosting + DNS.

## Consequences
- Akamai sources work for free; AWS cost stays ~$1–2/mo.
- **Trade-off:** the mini is a single point of failure (power / network / uptime),
  and the pipeline can't move to the cloud without buying a residential proxy.
- macOS **LaunchAgents** are the scheduler (`launchd/`), which also means scheduling
  is host-local, not portable.
