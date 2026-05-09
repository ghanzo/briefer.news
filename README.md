# briefer.news

A daily intelligence brief on US-government output. Autonomously scraped, curated, and synthesized into a published page each morning.

## What it is

Every morning, this pipeline scrapes ~45 sources of US-government and allied output (State Dept, CENTCOM, DOJ, Treasury, CISA, the Federal Register, UK MoD, etc.). A few hours later, Claude curates the most consequential ~50 items and synthesizes them into a 9-bullet daily brief in the style of [`BRIEF_STYLE.md`](BRIEF_STYLE.md). The result is published as a single static HTML page.

Live output: **briefer.news** *(public domain pending CNAME release from AWS Support; meanwhile the brief is served from `https://d1sl4o5xm2ds0o.cloudfront.net`)*.

## Architecture

```
M4 Mac mini at home (residential IP — required for Akamai bypass)
├── Postgres ─────────── article store (7-day rolling retention)
├── Pipeline ─────────── Python scrape stack
│                        (curl_cffi + Playwright + trafilatura)
├── Claude Code ──────── headless picker + synthesizer + WebSearch
└── nginx ────────────── local source-of-truth render
                            │
                            ▼
                    AWS S3 + CloudFront
                       (public edge)
```

**Why the mini specifically:** Akamai bot-detection on DoD `.mil` subdomains blocks cloud datacenter IPs. The mini's residential ISP is what makes the curl_cffi Chrome-impersonation bypass actually work. Verified live for war.gov, centcom.mil, navy.mil, jcs.mil, af.mil. See [`research/dod_bypass_findings_2026-05-07.md`](research/dod_bypass_findings_2026-05-07.md).

## Daily flow

| Time (PDT) | LaunchAgent | Stages |
|---|---|---|
| 04:00 | `news.briefer.daily` | RSS scrape (39 sources) → Akamai sweep (6 sources) → DB cleanup (7-day retention) |
| 07:00 | `news.briefer.synthesize` | World-context (Claude WebSearch) → SQL pre-filter (200 candidates) → Claude picker (~50) → SQL fetch full text → Claude synthesizer → deploy to local nginx + S3 + CloudFront invalidation |

Logs land in `logs/daily-YYYYMMDD.log` and `logs/synthesize-YYYYMMDD.log`. Failures are non-fatal — yesterday's brief stays live until the next successful synth.

## Editorial framework

| File | Purpose |
|---|---|
| [`BRIEF_STYLE.md`](BRIEF_STYLE.md) | Style rules: 9 bullets, 3 voices, 12–16-word headline, plain English, ≤2 DOJ items, ≤3 purely-domestic items, named actors, sourced citations |
| [`lens.md`](lens.md) | Interpretive framework: energy/resources, US-China axis, tech chokepoints, financial currents, human systems, innovation signals |
| [`AIMS.md`](AIMS.md) | Long-arc themes and predictions |
| [`COVERAGE.md`](COVERAGE.md) | Thematic dimensions / categories |
| [`CLAUDE.md`](CLAUDE.md) | Orientation for Claude sessions working in this repo |

## Setup on a new machine

For the full Mac mini deployment runbook (LaunchAgents, AWS infra, monitoring), see [`MIGRATION.md`](MIGRATION.md).

For local development:

```bash
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD; AI keys optional (uses Claude Code by default)

docker compose up -d postgres nginx
# Local site at http://localhost (after first synthesize run)

# Manual scrape (RSS + Akamai-protected):
docker compose run --rm pipeline python main.py --scrape-only
docker compose run --rm pipeline python main.py --akamai-only

# Manual synthesis (requires `claude` CLI installed and authenticated):
scripts/synthesize.sh
```

The `pipeline` container is profile-tagged (`profiles: [manual]`) so it doesn't auto-start with `docker compose up`. It's invoked on-demand by the operations scripts.

## Project layout

```
briefer.news/
├── pipeline/                       # scraping + DB
│   ├── config/sources.yaml         # ← source of truth for active feeds (39 standard)
│   ├── config/akamai_sources.yaml  # ← Akamai-protected feeds (6 active)
│   ├── scraper/                    # discovery, extractor, akamai_bypass, browser
│   │   ├── akamai_bypass.py        # curl_cffi TLS-impersonation fetcher
│   │   └── akamai_scrape.py        # orchestrator for .mil sources
│   ├── processor/                  # legacy AI integrations (Grok/Gemini/Claude API)
│   ├── builder/                    # Jinja2 templates (older path)
│   └── db/models.py                # SQLAlchemy schema
├── scripts/                        # operational scripts (LaunchAgent targets)
│   ├── daily.sh                    # 04:00 — scrape + cleanup
│   ├── synthesize.sh               # 07:00 — world-context + picker + synth + publish
│   ├── cleanup.sh                  # 7-day article retention
│   └── world_context.sh            # Claude WebSearch → ambient global-narrative file
├── research/                       # design references, sample briefs, probe scripts
│   ├── prototype_2026-05-07.html   # visual template (dark mode default)
│   └── brief_*.md                  # human-written reference briefs
├── nginx/nginx.conf
├── docker-compose.yml
├── BRIEF_STYLE.md                  # editorial style guide
├── lens.md                         # interpretive framework
├── CLAUDE.md                       # orientation for Claude sessions
└── MIGRATION.md                    # M4 mini deployment runbook
```

## Status snapshot

| | |
|---|---|
| Source pool | 45 active feeds (39 standard RSS, 6 Akamai-protected) |
| Daily article volume | ~50–80 net new articles/day after dedup |
| Local site | Live at http://localhost on the mini |
| Public domain (briefer.news) | Pending — AWS Support case open to release a CNAME claim from a self-closed Amplify-managed distribution |
| Edge URL (interim) | https://d1sl4o5xm2ds0o.cloudfront.net |
| AWS cost | ~$0.50/mo (Route 53 zone only) |
| Mini cost | ~$3/yr electricity (M4 idles at ~3W) |
