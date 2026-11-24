# Cloud migration — getting Briefer off the always-on Mac

**Status: production remains hybrid; migration not completed (verified 2026-10-21).**

Max requested moving everything feasible off the M4 without increasing spending.
The public site is on S3/CloudFront, but the Mac still generates/publishes both
editions, stores the production database, runs newsletter jobs and serves the
subscription API through Cloudflare Tunnel. Windows has stopped legacy containers;
Omarchy was offline during the audit. Do not infer that those copies are current.

The GitHub/Neon scraper is a shadow, not production. On October 21 both scrape
steps failed because SQLAlchemy selected the undeclared psycopg 3 driver. The
workflow still showed green because the steps used continue-on-error without a
final gate. This change explicitly selects the installed psycopg2 driver for bare
PostgreSQL URLs and makes incomplete runs fail. The separate connectivity check
reports database size and freshness using aggregate-only queries. The October 21
branch run passed connectivity and measured Neon at 112,762,880 bytes (~108 MiB),
but its newest article was September 24 and its last-24-hour insert count was zero.
Connectivity success is not a production-readiness verdict.

## No-additional-spend migration gates

1. **Repair and verify the existing shadow.** Use standard Linux GitHub runners
   in this public repository. Run the connectivity check and both scrapes; compare
   coverage with the Mac. No retained scrape artifacts are needed; use run logs.
2. **Confirm the actual Neon plan and capacity before production cutover.** The
   Mac database measured 70 MB. Neon currently advertises 1 GB storage and 100
   CU-hours per project/month on Free, but the account's selected plan, current
   usage, transfer quota and growth must be verified. Keep scale-to-zero; avoid
   constant polling that keeps compute awake. Do not enable paid overages.
3. **Make database access portable.** Synthesis SQL and subscriber helpers still
   execute psql inside a named local Docker container. Replace this dependency
   with a protected remote PostgreSQL connection, test against a disposable DB,
   then migrate the live data with a verified backup and a single-writer cutover.
   Never overwrite current subscriber states with the old Neon shadow copy.
4. **Move ordinary jobs first.** RSS/China ingestion, maintenance, health checks,
   reporting and backups can run in GitHub Actions. Keep existing SES/S3 services;
   cloud execution does not make their existing usage charges disappear. Move
   newsletter sending only after unsubscribe, bounce/complaint handling and
   duplicate-send protection work against the same production database.
5. **Move the subscription API.** A free-tier Worker is a candidate, but the
   current Python HTTP server is not a drop-in Worker. Preserve confirmation,
   unsubscribe, suppression, throttling and secret handling; validate these before
   changing DNS/tunnel routing. Confirm shared-account limits before deployment.
6. **Pilot Claude generation with existing subscription authentication.** Official
   Claude Code GitHub Actions supports CLAUDE_CODE_OAUTH_TOKEN from setup-token.
   The old claim that subscription authentication forces home execution is no
   longer a sufficient reason to retain the Mac. The repository currently lacks
   that secret. Use subscription quota only, no API billing fallback; verify quota
   and unattended token renewal. First run without publishing or sending mail.
7. **Keep only the residential-source worker if still needed.** The six .mil
   hosts were previously blocked from cloud IPs. Recheck before the final cutover.
   An M4 is not intrinsically required: a smaller existing home machine may do,
   provided its runtime and reliability are proven. Do not buy proxies/hardware
   or remove those sources without a separate decision.
8. **Retire local services only after verified replacement.** Observe successful
   cloud runs, rehearse rollback, disable duplicate schedules, then retire Docker
   Postgres/nginx and the tunnel once nothing depends on them. Existing public
   pages staying online is not proof the publishing or subscription system works.

Evidence: [October 21 shadow failure](https://github.com/ghanzo/briefer.news/actions/runs/39606045060).
Current provider references (checked October 21):
[GitHub billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions),
[Neon pricing](https://neon.com/pricing),
[Claude subscription authentication](https://code.claude.com/docs/en/github-actions),
[Workers limits](https://developers.cloudflare.com/workers/platform/limits/).

The sections below retain the original August plan and decisions as history;
the verified status and gates above take precedence.

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
3. ~~Shadow scrape from a runner~~ **DONE 2026-08-31, run 33355317086** —
   RSS (65/65 discovered, 0 fetch failures) + China (all 32 ran, `blocked=False`
   everywhere). Per-source failures are IDENTICAL from home vs datacenter
   (MOF 14/14 both, SAMR 8/8 both, NPC 4/4 both) → source-side quirks, not IP
   blocks. **The home-box scrape roster is exactly the 6 Akamai `.mil` hosts —
   the plan's 0.75% assumption is validated.** (Side finding: MOF News has
   never extracted successfully from anywhere — repair independently.)
4. Port the non-Claude jobs to GH Actions cron, writing to Neon, in shadow first.
5. Re-point the home box's Claude jobs + `.mil` scrape at Neon.
6. Cut over: final dump → Neon, enable cloud crons, disable the launchd
   equivalents (keep them committed, disabled), retire local Docker PG + nginx.
7. The mini is then free to become the lean home box — or hand the role to other
   hardware — on your schedule, not under pressure.
