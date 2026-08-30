# Cloud migration — getting Briefer off the always-on Mac

**Status:** PLANNED — 2026-08-30
**Goal:** the scheduled pipeline runs in the cloud, driven from the GitHub repo,
so no machine has to stay awake. Any laptop can then clone and operate it.

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
| Synth (12 jobs) | `claude -p` via subscription OAuth | `claude -p` / API with `ANTHROPIC_API_KEY` | ✅ needs a key |
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

1. **Secrets → GH encrypted secrets.** `ANTHROPIC_API_KEY`, Postgres URL, AWS keys
   for the S3/CloudFront deploy. `.env` never leaves the mini as a file.
2. **launchd → `.github/workflows/*.yml` cron.** One workflow per cadence
   (scrape 00:30, US synth 02:30, China 04:00, catch-up, healthcheck). Times move
   to UTC.
3. **Postgres → hosted.** Dump `briefer_postgres`, restore to Neon/Supabase, swap
   the connection string. Nightly backup already goes to S3.
4. **Auth model → API key.** The synth authenticates today via the Claude
   subscription (`claude -p`). In cloud that becomes metered `ANTHROPIC_API_KEY`
   billing — a real cost line to price before flipping (see fork 2).
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

### Fork 2 — synth billing
Subscription `claude -p` → metered `ANTHROPIC_API_KEY`. Each synth is a large-context
call, run several times/day across two editions plus catch-up. Worth pricing a
representative day before committing, so the monthly number is a decision, not a
surprise.

---

## Suggested order

1. Stand up hosted Postgres; restore a dump; point a **test** workflow at it.
2. Port one job (healthcheck — read-only, safe) to GH Actions cron end-to-end.
3. Port the synths behind `ANTHROPIC_API_KEY`; run in shadow (no deploy) for a day.
4. Resolve Fork 1; wire the `.mil` path accordingly.
5. Cut over cron; disable the launchd equivalents (keep them committed, disabled).
6. The mini is now optional — reformat or repurpose on your schedule, not under pressure.
