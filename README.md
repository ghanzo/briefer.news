# briefer.news

A daily intelligence platform on multi-government output. Autonomously scraped, curated, and synthesized into a published page per edition each morning.

## What it is

Every morning, this pipeline scrapes ~72 sources of government output across two editions:
- **US edition** — 45 sources (State Dept, CENTCOM, DOJ, Treasury, CISA, Federal Register, UK MoD, etc.) → brief at **https://briefer.news/usa/**
- **China edition** — 27 Chinese-government sources (MFA, State Council, Xinhua, NDRC, PBOC, MIIT, CAC, Qiushi, CCDI, NPC, judicial, provincial, etc.) → brief at **https://briefer.news/china/**

A few hours after each scrape, Claude curates the most consequential ~50 items per edition and synthesizes them into a 9-bullet daily brief in the style of [`BRIEF_STYLE.md`](BRIEF_STYLE.md). The China brief follows additional editorial rules in [`CHINA_BRIEF.md`](CHINA_BRIEF.md) (bilingual voices, diplomatic-vocabulary calibration, internal-evolution priority).

The site root **https://briefer.news** is an editions selector with live-fetched headlines from each edition. Designed to scale to additional country editions (UK / EU / Russia planned).

## Architecture

**[Interactive pipeline flow map →](https://ghanzo.github.io/briefer.news/pipeline-flows.html)** — click any flow (overnight scrape, publish a brief, refresh digests, edition routing) to trace it step-by-step through every component, annotated with what is passed between them. Source: [`docs/pipeline-flows.html`](docs/pipeline-flows.html).

```mermaid
flowchart LR
    GOV["Gov sources<br/>RSS / Akamai / PRC"]
    subgraph mini["M4 Mac mini (home, residential IP)"]
        DSH["daily.sh<br/>parallel scrape"]
        PG[("Postgres<br/>article store")]
        SYN["synthesize.sh<br/>synthesize_china.sh<br/>daily_digests.sh"]
        CLA["Claude CLI<br/>pick + synthesize"]
        NGX["nginx<br/>local render"]
    end
    subgraph aws["AWS edge"]
        S3[("S3 origin")]
        CF["CloudFront<br/>edition routing"]
    end
    GOV --> DSH
    DSH --> PG
    PG --> SYN
    SYN --> CLA
    CLA --> NGX
    NGX --> S3
    S3 --> CF
    CF --> RDR(["Reader"])
```

**Why the mini specifically:** Akamai bot-detection on DoD `.mil` subdomains blocks cloud datacenter IPs. The mini's residential ISP is what makes the curl_cffi Chrome-impersonation bypass actually work. Verified live for war.gov, centcom.mil, navy.mil, jcs.mil, af.mil. See [`research/dod_bypass_findings_2026-05-07.md`](research/dod_bypass_findings_2026-05-07.md).

## Daily flow

| Time (PDT) | LaunchAgent | Stages |
|---|---|---|
| 04:00 | `news.briefer.daily` | **3 scrapes in parallel** — RSS (39 sources) + Akamai (6 sources) + China (27 sources) — then DB cleanup (7-day retention) |
| 07:00 | `news.briefer.synthesize` | World-context (Claude WebSearch) → SQL pre-filter (200 candidates) → Claude picker (~50) → SQL fetch full text → Claude synthesizer → deploy to `/usa/` + S3 + CloudFront invalidation |
| 07:30 | `news.briefer.synthesize.china` | SQL pre-filter (175 internal + 25 reserved MFA) → Claude picker (≥6 MFA required) → SQL fetch full text → Claude synthesizer (bilingual voices, diplomatic-glossary calibration) → deploy to `/china/` + S3 + CloudFront invalidation |

Logs: `logs/daily-YYYYMMDD.log`, `logs/synthesize-YYYYMMDD.log`, `logs/synthesize-china-YYYYMMDD.log`. Failures are non-fatal — yesterday's brief stays live until the next successful synth.

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
│   ├── daily.sh                    # 04:00 — parallel scrapes (rss+akamai+china) + cleanup
│   ├── synthesize.sh               # 07:00 — US synth → /usa/
│   ├── synthesize_china.sh         # 07:30 — China synth → /china/
│   ├── cleanup.sh                  # 7-day article retention
│   └── world_context.sh            # Claude WebSearch → ambient global-narrative file
├── research/                       # design references, sample briefs, probe scripts
│   ├── prototype_us_2026-05-12.html      # CURRENT US template (dark default, nav strip)
│   ├── prototype_china_2026-05-12.html   # CURRENT China template (red theme, PRC flag)
│   ├── prototype_selector_2026-05-12.html # CURRENT home selector (two-card layout)
│   ├── prototype_2026-05-07.html         # original US template (kept; superseded)
│   └── brief_*.md                  # human-written reference briefs
├── docs/pipeline-flows.html        # interactive pipeline flow map (served via GitHub Pages)
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
| Source pool | **72 active feeds** — 45 US (39 RSS + 6 Akamai-protected) + 27 Chinese-government |
| Daily article volume | ~200-300 net new articles/day after dedup across both editions |
| Local site | Live at http://localhost on the mini |
| Public domain | **Live** at https://briefer.news (multi-edition) since 2026-05-12 |
| US edition | Live at https://briefer.news/usa/ — autonomous synth 07:00 PDT |
| China edition | Live at https://briefer.news/china/ — autonomous synth 07:30 PDT (since 2026-05-12). Bilingual voices, internal-evolution framing |
| Selector | Live at https://briefer.news/ — JS-fetched headlines from each edition |
| AWS cost | ~$0.50/mo (Route 53 zone only) |
| Mini cost | ~$3/yr electricity (M4 idles at ~3W) |
