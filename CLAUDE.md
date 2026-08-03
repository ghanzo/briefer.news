# CLAUDE.md — Working in briefer.news  *(current as of 2026-05-28)*

Orientation for a fresh Claude session. Read this, then run `make status` and
skim **`INDEX.md`** (one-line purpose + freshness tag for every root doc).

---

## Start here

```bash
make status      # one-screen orientation: git state, the 24 launchd jobs,
                 # today's live brief stamps + headline word counts, recent
                 # logs, last alerts. Run this first every session.
make help        # all operator targets
```

Then read `INDEX.md`. It tags every root `*.md` as [LIVE] / [REFERENCE] /
[PLANNED] / [STALE] so you don't read a superseded plan as if it were current.

---

## Decisions / "why"

Architecture decisions are recorded in `docs/adr/` (read these before
re-litigating a design choice, and add one for any significant new decision).

---

## What this project is

**briefer.news** — a daily intelligence platform that ingests multiple
governments' output, runs each edition through an autonomous Claude-Code
pipeline, and publishes a static HTML page per edition each morning.

**Live at https://briefer.news** — multi-edition since 2026-05-12: a selector
at the root, US brief at `/usa/`, China brief at `/china/`. A CloudFront
Function rewrites trailing-slash URLs (`/usa/` → `/usa/index.html`). Owner:
Max Goshay. Repo: `github.com/ghanzo/briefer.news`.

Two editions ship today; the design scales to N (UK / EU / Russia planned):
- **US edition** at `/usa/` — ~45 sources (RSS + Akamai-protected DoD), synth 02:30 PDT.
- **China edition** at `/china/` — ~29 Chinese-gov sources, synth 04:00 PDT, English-only voices. See **`CHINA_BRIEF.md`**.

The interpretive lens is in `lens.md` (six layers, priority order: energy/
resources, US-China axis, tech chokepoints, financial currents, human systems,
innovation signals).

> The old `briefer/` econ-CLI predecessor has been **archived** to
> `archive/briefer-cli/`. It is no longer part of this repo's product.

---

## Synthesis is FULLY AUTONOMOUS

There is no manual brief-publish step. Both editions generate and deploy
themselves end-to-end via headless Claude Code (`claude -p`), every morning,
with no human in the loop:

- `scripts/synthesize.sh` (02:30 PDT) — US brief → `/usa/`
- `scripts/synthesize_china.sh` (04:00 PDT) — China brief → `/china/`

Each: world-context (Claude WebSearch, Stage 0) → SQL pre-filter → Claude
picker (~50 items) → SQL fetch full text → Claude synthesizer → deploy to
local nginx + S3 + CloudFront invalidation. Failures are non-fatal: yesterday's
brief stays live until the next successful synth, and `synth_catchup.sh` /
`healthcheck.py` cover a missed run.

(Any older doc or comment claiming "AI synthesis NOT yet wired" / "manual brief
publish" / "Path A only" is stale — it has been autonomous since 2026-05-09.)

---

## The 24 LaunchAgents

The running schedule is **23 active LaunchAgents** (24 plists; `reconfirm` is
committed but disabled) on the M4 Mac mini at home. They
are now committed in **`launchd/`** (source of truth) and synced to
`~/Library/LaunchAgents` via **`scripts/install_launchagents.sh`**:

```bash
make agents-status     # diff repo launchd/ vs live ~/Library/LaunchAgents
make agents-export     # live -> repo (after editing an agent by hand; then commit)
make agents-install    # repo -> live (fresh machine / disk loss recovery)
```

| Time (PDT) | LaunchAgent | Target | What it does |
|---|---|---|---|
| boot / login | `news.briefer.boot` | `boot.sh` | bring-up at login (docker, nginx) |
| boot, KeepAlive | `news.briefer.email_api` | `email_api_server.py` | long-running subscriber API (signup/unsubscribe) |
| every 10 min | `news.briefer.email_bounce_handler` | `email_bounce_handler.py` | poll SQS for SES bounces/complaints |
| 00:30 | `news.briefer.daily` | `daily.sh` | 3 scrapes in parallel (rss + akamai + china) + cleanup |
| 02:30 | `news.briefer.synthesize` | `synthesize.sh` | **autonomous US synth → /usa/** |
| 04:00 | `news.briefer.synthesize.china` | `synthesize_china.sh` | **autonomous China synth → /china/** |
| 05:00, 18:00 | `news.briefer.researcher` | `researcher.sh` | research what's driving traffic / channels |
| 05:30 | `news.briefer.digests` | `daily_digests.sh` | refresh rolling 7-day digest pages |
| 06:00 | `news.briefer.morningbrief` | `morning_brief.sh` | daily site-state report |
| 06:30 | `news.briefer.healthcheck` | `healthcheck.py` | verify both briefs published today; alert if stale |
| 06:30 | `news.briefer.drafter` | `drafter.sh` | draft + auto-post growth/social copy |
| 07:15 | `news.briefer.feedfreshness` | `feed_freshness.py` | watchdog: active feeds that stopped delivering |
| 07:30 | `news.briefer.dmarc` | `dmarc_report.py` | ingest DMARC aggregate reports from S3 |
| 08:30 | `news.briefer.email_send` | `email_send.py` | daily email send pipeline |
| 09:00 | `news.briefer.alertdigest` | `alert_digest.sh` | roll `alerts.log` into one daily digest email |
| 10:00 | `news.briefer.engagement` | `x_engagement_collector.py` | snapshot X-post engagement (10:00 + 16:00) |
| 10:00 | `news.briefer.trafficreport` | `traffic_report_daily.sh`* | daily CloudFront traffic snapshot |
| ~~10:30~~ | `news.briefer.reconfirm` | `reconfirm_pending.py` | **DISABLED 2026-08-03** — was mailing ~718 never-opted-in addresses 30/day; see the plist comment |
| 11:15, 13:05, 15:30 | `news.briefer.synthcatchup` | `synth_catchup.sh` | self-healing retry if either edition is stale |
| 12:30 | `news.briefer.midday` | `daily.sh midday` | bonus daytime scrape (rss+akamai+china), NO cleanup — captures stories breaking during the day for the next morning's brief |
| 14:00 | `news.briefer.critique` | `editorial_critique.sh` | editorial critique of the day's briefs |
| 23:30 | `news.briefer.backup` | `backup_subscribers.sh` | off-box backup of email_subscribers → S3 (`briefer-news-backups`) |
| Sun 10:00 | `news.briefer.analyzer` | `analyzer.sh` | weekly growth analysis |
| Mon 09:00 | `news.briefer.searchreport` | `search_report_weekly.sh` | weekly Search Console snapshot |

\* `news.briefer.trafficreport` runs `scripts/traffic_report_daily.sh`, which wraps `traffic_report.py`.

**Model pinning.** Every Claude-invoking script passes `--model` explicitly,
defaulting via `MODEL="${SYNTH_MODEL:-claude-opus-5}"`, so a changed or pulled
global default (e.g. the 2026-06-15 Fable-5 outage) can never silently change
what a job runs on. Override for a single run with
`SYNTH_MODEL=claude-opus-4-8 make synth`. `preflight.sh` is the one script that
touches the CLI without a pin — it only checks the binary exists.

Logs land in `logs/` (gitignored): `daily-YYYYMMDD.log`, `synthesize-*.log`,
plus per-agent `*.out.log` / `*.err.log`, and `alerts.log`.

**Why the M4 mini specifically:** Akamai bot detection on DoD `.mil` subdomains
blocks cloud datacenter IPs. The mini's residential ISP makes the curl_cffi
Chrome-impersonation bypass work. Production cannot move off-mini without paid
residential proxies (~$50-100/mo).

---

## Brief pipeline overview

1. **Scrape (00:30).** `daily.sh` runs three scrapes concurrently — standard
   RSS, Akamai-protected DoD (`pipeline/scraper/akamai_bypass.py` curl_cffi TLS
   impersonation), and China gov (`pipeline/scraper/china_scrape.py`) — then
   7-day cleanup. Articles land in Postgres.
2. **Pre-filter.** SQL ranks candidates per edition (China uses a two-pool
   design: internal-evolution slots + reserved MFA voice slots).
3. **Pick.** Claude picker selects ~50 of the most consequential items.
4. **Synthesize.** Claude renders the brief HTML to the `prototype_*_2026-05-12.html`
   template, following `BRIEF_STYLE.md` (US) / `CHINA_BRIEF.md` + `DEK.md` (China-side voice).
5. **Validate + deploy.** `validate_brief.py` gates structure; deploy to nginx
   + S3 + CloudFront invalidation.

Brief structure (both editions, **as of 2026-05-28**):
Headline → **Today's events** → **This week** → **Allied Governments** (US only)
→ **Voices** → **Sources**.

> **The on-page dek and the continuity / thread "chip" strip were REMOVED
> 2026-05-27 and are staying removed.** The dek's plain-English, outcome-over-
> process rules in `DEK.md` now apply to the **top-3 event ledes**, not to a
> separate dek element. Any doc still describing a live `<ul class="dek-bullets">`
> or a Day-N thread strip is describing removed UI (see `INDEX.md` tags).

---

## Ops tooling (new this session)

| Tool | Purpose |
|---|---|
| `Makefile` (`make status`) | operator entry point — one-screen orientation + standard verbs |
| `scripts/brief_parser.py` | single source of truth for reading a rendered brief into structured data (~12 consumers) |
| `scripts/validate_brief.py` | post-synth editorial-contract gate (stamp, headline, structure) |
| `scripts/alert.sh` | the single off-box notifier (the only alerting that leaves the mini) |
| `scripts/install_launchagents.sh` | sync `launchd/` ⇄ live agents; rebuild schedule from git |
| `scripts/post_guard.py` | shared lock + length budget for the X posting path |
| `scripts/x_cost_log.py` | append-only X API credit ledger (`make x-costs`) |
| `scripts/preflight.sh` | pre-synth health check (`make preflight`) |
| `tests/` | `python3 -m unittest discover -s tests` — brief_parser regression tests against frozen renders |

---

## Deploy model

Static site → **S3 + CloudFront**, in AWS account `462170975634`. Synth scripts
deploy automatically (Stage 6): copy to S3 (`briefer-news-site`, us-east-1,
private, OAC), invalidate CloudFront (`EMV1VIFYTSI3U`). Non-fatal on AWS errors —
the local nginx site still publishes.

- The domain is **registered in a separate AWS account** (`026090521469`); the
  `registrar` AWS CLI profile holds its creds. Deployment infra is all in
  `462170975634` (`default` profile).
- Root `/` is the selector; `/usa/` and `/china/` are the briefs; a CloudFront
  Function (`briefer-news-index-rewrite`, viewer-request) rewrites `/<dir>/` →
  `/<dir>/index.html`.

```bash
make synth          # run US synth + deploy   ** DEPLOYS LIVE **
make synth-china    # run China synth + deploy ** DEPLOYS LIVE **
make preview        # validate live briefs (read-only)
make healthcheck    # stale-brief check
```

---

## Docker stack

`docker compose up -d` brings up `postgres` (5433) + `adminer` (5050) + `nginx`
(80). The `pipeline` service is profile-tagged (`profiles: [manual]`) so it does
NOT auto-start; it's invoked on demand via `docker compose run --rm pipeline …`.
Validate source yamls after editing:

```bash
python -c "import yaml; yaml.safe_load(open('pipeline/config/sources.yaml'))"
python -c "import yaml; yaml.safe_load(open('pipeline/config/akamai_sources.yaml'))"
python -c "import yaml; yaml.safe_load(open('pipeline/config/china_sources.yaml'))"
```

---

## Where to start reading

1. **`CLAUDE.md`** (this file) + `make status` + **`INDEX.md`**
2. **`BRIEF_STYLE.md`** — US editorial style guide; mandatory before any US synth
3. **`CHINA_BRIEF.md`** + **`DEK.md`** — if your work touches the China side / event-lede voice
4. `lens.md` — interpretive framework (still load-bearing)
5. `scripts/synthesize.sh` / `scripts/synthesize_china.sh` — current synth pipelines
6. `pipeline/main.py` — orchestrator (`--scrape-only` / `--akamai-only` / `--china-only`)

Marketing/growth session? Start with `MARKETING.md` + `GROWTH.md` instead.
Historical plans + the M4 deployment runbook now live under `archive/docs/`.
