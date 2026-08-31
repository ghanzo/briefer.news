# Cloud migration — getting Briefer off the always-on Mac

**Status:** IN PROGRESS — 2026-08-30. Both forks decided; hosted PG live and
proven from a runner; shadow-scrape pilot in flight.
**Goal:** the scheduled non-Claude pipeline runs in the cloud, driven from the
GitHub repo. One small home box remains for the two things that can't move
cheaply: the `.mil` scrape (residential IP) and the Claude jobs (subscription
auth — Fork 2). Any laptop can clone and operate everything.

---

## The one fact that shapes everything

Of the last 7 days' corpus, **0.75%** of articles (68 of 9,071) come from the 6
DoD `.mil` hosts that Akamai blocks from datacenter IPs. That share is the *only*
part of the system that needs a residential IP. Everything else — RSS, all `.gov`,
all China-gov, the synth, the deploy — runs from anywhere.

So this is not "can Briefer move to cloud" (it can); it's "what do we do with the
0.75%." See the fork at the bottom.

| Component | Today | Cloud target | Portable? |
|---|---|---|---|
| Serving | S3 + CloudFront | unchanged | ✅ already cloud |
| Scheduler | 23 launchd jobs (macOS) | GitHub Actions cron | ✅ rewrite, not port |
| Postgres | Docker on the mini | hosted (Neon / Supabase / RDS) | ✅ |
| Synth (12 jobs) | `claude -p` via subscription OAuth | **stays on the home box** (`claude -p`, subscription — Fork 2) | ❌ by choice, $0 |
| Scrape — 99% | curl_cffi from home | GH Actions runner | ✅ |
| Scrape — 6 `.mil` hosts | residential IP + curl_cffi | **cannot move** | ❌ see fork |

---

## Why GitHub Actions (not a VM)

- The repo is already the source of truth (`ghanzo/briefer.news`).
- Built-in `on: schedule` cron replaces launchd directly; no always-on host, no
  per-hour cost.
- Built-in encrypted secrets replace `.env` — provision fresh secrets there, never
  ship this machine's `.env` around.
- 6-hour job ceiling is far above any synth run.

A small always-on VM (Fly/Render/EC2) is the wrong default here: it costs money to
idle **and** has a datacenter IP, so it breaks the `.mil` scrape anyway — the one
thing a VM would be for.

---

## What has to change (concrete)

1. **Secrets → GH encrypted secrets.** Postgres URL (`NEON_DATABASE_URL`, set
   2026-08-30), AWS keys for SES/S3 jobs that move to cloud. No `ANTHROPIC_API_KEY`
   (Fork 2). `.env` never leaves the mini as a file.
2. **launchd → `.github/workflows/*.yml` cron.** One workflow per cadence
   (scrape 00:30, US synth 02:30, China 04:00, catch-up, healthcheck). Times move
   to UTC.
3. **Postgres → hosted.** Dump `briefer_postgres`, restore to Neon/Supabase, swap
   the connection string. Nightly backup already goes to S3.
4. **Auth model — unchanged.** Fork 2 decided: Claude jobs keep subscription
   `claude -p` on the home box. Mitigate the OAuth-expiry SPOF (Aug 18–22
   outage mode) with the existing preflight probe + the off-box cloud
   liveness healthcheck, not with a paid API key.
5. **The `.mil` decision.** See below.

---

## The two decisions that are Max's alone

### Fork 1 — the 0.75% `.mil` dependency  →  DECIDED 2026-08-30: option (a)
- **(a) Keep one tiny always-on box at home** (a Pi, or the reformatted mini) running
  *only* the 6-host `.mil` scrape, writing to the same hosted Postgres. Everything
  else is cloud. Cost: ~0, one low-power device stays on.  **← chosen.**
- **(b) Residential proxy** (~$50–100/mo) so the cloud runner can reach `.mil`. Fully
  cloud, no home device, recurring cost.
- **(c) Drop `.mil`.** Simplest. But those 68 articles carry outsized editorial
  weight — CENTCOM's Iran statements were a lead story — so this is a real content
  loss, not just a 0.75% trim.

### Fork 2 — synth billing  →  DECIDED 2026-08-30: stay on subscription
No metered `ANTHROPIC_API_KEY`. All Claude jobs (synths, catch-up, world-context,
critique, morning brief, drafter, researcher, analyzer) run on the home box under
the existing subscription — $0 marginal cost. Consequence: the Fork-1 home box is
not just a `.mil` scraper; it is the Claude worker. Its two jobs share one trait:
they need something a datacenter can't cheaply have (a residential IP; a
subscription login). Everything that needs neither goes to GitHub Actions.

---

## Workflow conventions (bake into every ported job)

- **Odd-minute schedules** (`17 8 * * *`, not `0 8 * * *`) — top-of-hour cron on
  shared runners queues; odd minutes dodge the crowd. Expect fire times to be
  minutes late regardless; the catch-up pattern already tolerates this.
- **60-day keep-alive** — GitHub disables scheduled workflows in repos with no
  commit activity for 60 days. One workflow must auto-commit a trivial daily
  stamp so the crons can never silently die of quiet success.
- **Secrets via GH encrypted secrets only**; nothing credential-shaped in YAML.

## Order (updated 2026-08-30)

1. ~~Stand up hosted Postgres; restore a dump; point a **test** workflow at it.~~
   **DONE 2026-08-30** — Neon `briefer-news` (us-west-2), full restore verified,
   `db-connectivity-check` green from a runner.
2. ~~Port one read-only job to GH Actions cron end-to-end.~~ **DONE 2026-08-30**
   — `liveness-healthcheck` on 2×-daily cron.
3. **Shadow scrape from a runner** (`shadow-scrape.yml`) — validate which non-.mil
   sources tolerate a datacenter IP; the failures define the home box's scrape list.
4. Port the non-Claude jobs to GH Actions cron, writing to Neon, in shadow first.
5. Re-point the home box's Claude jobs + `.mil` scrape at Neon.
6. Cut over: final dump → Neon, enable cloud crons, disable the launchd
   equivalents (keep them committed, disabled), retire local Docker PG + nginx.
7. The mini is then free to become the lean home box — or hand the role to other
   hardware — on your schedule, not under pressure.
