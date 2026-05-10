# CLAUDE.md — Working in briefer.news

This file orients a fresh Claude session. Read it first.

---

## What this project is

**briefer.news** — a daily intelligence brief that ingests US-government output, runs it through an autonomous Claude-Code pipeline, and publishes a static HTML page each morning. **Live at https://briefer.news.** Owner is Max Goshay. Repo at `github.com/ghanzo/briefer.news`.

Two products in this repo:

1. **`pipeline/` + `scripts/`** — the news-ingestion + autonomous synthesis stack. **This is the main, shipped product.**
2. **`briefer/`** — a separate Click-based CLI for ingesting economic time series (FRED, Yahoo Finance) into DuckDB with AI interpretation. Companion tool, not the main product.

The interpretive lens is in `lens.md` and `AIMS.md` — six layers in priority order: energy/resources, US-China axis, tech chokepoints, financial currents, human systems, innovation signals.

A **parallel China-source brief** is in active development. Source list and scraper are scaffolded (`pipeline/config/china_sources.yaml`, `pipeline/scraper/china_scrape.py`); 499 Chinese-language articles already in DB; synthesizer not yet built. See **`CHINA_BRIEF.md`** for design + status.

---

## Where we are (current build stage — updated 2026-05-10)

| Stage | Status |
|---|---|
| **1. Source foundation (US gov)** | **Done** — 45 active US-gov + allied sources scraping daily |
| **2. Pipeline validation** | **Done** — autonomous scrape runs at 04:00 PDT every day |
| **3. AI synthesis** | **Done — autonomous via Claude Code headless.** SQL pre-filter → picker → synthesizer, with world-context layer. Brief generated 07:00 PDT daily. |
| **4. Editorial output** | **Done** — dark-mode default, accessibility-first headlines, 9-bullet/3-voice format locked |
| **5. Operations** | **Done** — two LaunchAgents on M4 mini, autonomous + cleanup + S3 publish + CloudFront invalidation. AWS deployment complete. |
| **6. China-source brief** | **In active development** — sources scaffolded, 499 articles in DB, synthesizer pending. See `CHINA_BRIEF.md`. |
| **7. Expansion** | Deferred — international + commercial + data APIs |

**Critical principle (still applies):** *Don't add more sources without seeing the pipeline output first.* The user-facing test is the daily brief, not a probe count.

---

## How the autonomous flow runs

Two LaunchAgents on the M4 Mac mini at home:

| Time (PDT) | LaunchAgent | What runs |
|---|---|---|
| 04:00 | `news.briefer.daily` | `scripts/daily.sh` → standard scrape (39 RSS) → Akamai sweep (6 sources) → cleanup (7-day retention) |
| 07:00 | `news.briefer.synthesize` | `scripts/synthesize.sh` → world-context (Claude WebSearch, Stage 0) → SQL pre-filter (200 candidates) → Claude picker (~50) → SQL fetch full text → Claude synthesizer → deploy to local nginx + S3 + CloudFront invalidation |

Logs land in `logs/daily-YYYYMMDD.log` and `logs/synthesize-YYYYMMDD.log`. Failures are non-fatal — yesterday's brief stays live until the next successful synth.

**Why the M4 mini specifically:** Akamai bot detection on DoD `.mil` subdomains (war.gov, centcom.mil, navy.mil, jcs.mil, af.mil) blocks cloud datacenter IPs. The mini's residential ISP makes the curl_cffi Chrome-impersonation bypass actually work. **Production cannot move off-mini without paid residential proxies (~$50-100/mo).**

---

## Source counts (US gov + allied)

- **39 active standard RSS / web-scrape sources** in `pipeline/config/sources.yaml` — State Dept regional desks, DoD, Federal Reserve, Treasury, USTR, GAO, DOJ NS, CISA, Federal Register (×2), CBP, DOJ OPA, FBI National, CFPB, BLS, BEA, CBO, NY Fed Liberty Street, GovInfo (3), Court of Appeals (2), EIA, plus international (BBC/AJ/DW/Yonhap/AllAfrica/UK/Kremlin/TASS/UN/WHO/IAEA), commercial (OilPrice, Mining.com, Hacker News).
- **6 active Akamai-protected sources** in `pipeline/config/akamai_sources.yaml` — DOD War.gov, CENTCOM, Navy.mil, JCS, U.S. Air Force, UK MoD. Scraped via `--akamai-only` stage with curl_cffi TLS-impersonation. ~50 articles/day (mostly de-dup; UK MoD is the highest-yield).
- **Total: 45 active sources** producing **~50-100 net new articles/day** after dedup.
- Held sources (`active: false`) remain in yaml ready to enable later.

---

## Editorial framework (key files)

| File | Purpose |
|---|---|
| `BRIEF_STYLE.md` | Editorial style guide. **Read end-to-end before any synthesis.** Includes the load-bearing **Accessibility rule** for headlines (replace acronyms with plain descriptors, dinner-party readability test). |
| `lens.md` | Interpretive framework (6 layers, US-China-axis-aware) |
| `AIMS.md` | Long-arc themes and predictions |
| `COVERAGE.md` | Thematic dimensions / categories |
| `research/prototype_2026-05-07.html` | The visual template the synthesizer mirrors. **Defaults to `theme-ink` (dark mode).** Picker default = Dark, JS fallback = ink. |
| `CHINA_BRIEF.md` | Companion editorial doc for the China-source brief |

Brief format (locked):
- **9 bullets** per brief in priority order
- **3 voices** as `<blockquote class="pull">`, 12-30 words each, mix of registers, **never invent a quote**
- **Headline**: 12-16 words, ONE OR TWO CLEAR ACTIONS MAX, plain English, **no jargon** (GAESA → "Cuba's military business arm"; DFARS → "Pentagon foreign-ownership rule"; FY27 → "2027 budget")
- **≤2 DOJ items**, **≤3 purely-domestic items** of 9
- Each bullet: bold lead (2-4 words), tight description, citation `<sup>`, `<span class="when">Date · Agency</span>`

---

## Architecture map

```
briefernewsapp/
├── CLAUDE.md                       ← you are here
├── README.md                       ← public-facing project overview
├── BRIEF_STYLE.md                  ← editorial style guide (READ before any synthesis)
├── CHINA_BRIEF.md                  ← China-side editorial + status (NEW 2026-05-10)
├── lens.md                         ← interpretive framework
├── AIMS.md                         ← long-arc themes
├── COVERAGE.md                     ← thematic dimensions
├── MIGRATION.md                    ← M4 mini deployment runbook (HISTORICAL — done; see Postmortem section at bottom)
├── PLAN_AUTOMATION.md              ← original deployment plan (HISTORICAL / superseded)
├── PLAN_PROCESSING.md              ← earlier processing plan (HISTORICAL / superseded)
├── PLAN_SUMMARIZATION.md           ← earliest summarization sketch (HISTORICAL / superseded)
├── SOURCES.md / SOURCE_NOTES.md    ← per-source operational notes (US gov)
├── SOURCES_MATRIX.md / SOURCES_PLAN.md  ← regional + aspirational source planning
├── DESIGN_REFERENCES.md            ← visual / typographic references
├── docker-compose.yml              ← postgres + adminer + nginx + (manual-profile) pipeline
├── .env.example                    ← required env vars (real .env is gitignored)
├── aws-support-case-body.md        ← saved AWS Support case body (used for the Amplify resolution)
│
├── scripts/                        ← OPERATIONAL SCRIPTS — LaunchAgent targets
│   ├── daily.sh                    ← 04:00 — scrape + cleanup
│   ├── synthesize.sh               ← 07:00 — world-context + picker + synth + deploy + S3
│   ├── cleanup.sh                  ← 7-day article retention (called from daily.sh)
│   └── world_context.sh            ← Claude WebSearch → ambient global-narrative file
│
├── pipeline/                       ← scraping + DB + (legacy) processor
│   ├── main.py                     ← orchestrator (--scrape-only / --akamai-only / --china-only / --run-now)
│   ├── scheduler.py                ← legacy in-container APScheduler (NOT used in production — pipeline service is profile-tagged)
│   ├── config/sources.yaml         ← SOURCE OF TRUTH for standard scrape (39 active)
│   ├── config/akamai_sources.yaml  ← SOURCE OF TRUTH for Akamai-protected scrape (6 active)
│   ├── config/china_sources.yaml   ← SOURCE OF TRUTH for China gov scrape (NEW 2026-05-10, 23 active)
│   ├── scraper/
│   │   ├── discovery.py            ← RSS + Playwright link discovery (standard sources)
│   │   ├── extractor.py            ← article extraction (trafilatura/BS4/playwright)
│   │   ├── browser.py              ← Playwright singleton manager
│   │   ├── akamai_bypass.py        ← curl_cffi TLS-impersonation fetch
│   │   ├── akamai_scrape.py        ← orchestrator for Akamai-protected sources
│   │   └── china_scrape.py         ← orchestrator for China gov sources (NEW 2026-05-10)
│   ├── processor/                  ← LEGACY — pre-Claude-Code AI integrations (Grok / Gemini / Claude API)
│   │                                  Not used in current production flow. synthesize.sh uses headless `claude -p`.
│   ├── builder/                    ← LEGACY — Jinja2 templates (older render path)
│   ├── db/models.py                ← SQLAlchemy: Source, Article, ArticleSummary, DailyBriefing, etc.
│   └── output/                     ← legacy render output (production uses /Users/maxgoshay/code/briefernewsapp/.run/)
│
├── briefer/                        ← companion CLI for econ time series (FRED + Yahoo)
│
├── research/                       ← design references, sample briefs, probe scripts
│   ├── prototype_2026-05-06.html   ← original LIVE site prototype (kept for reference)
│   ├── prototype_2026-05-07.html   ← visual template the synthesizer uses (DARK DEFAULT)
│   ├── brief_2026-05-06.md         ← May 6 hand-written brief (markdown)
│   ├── brief_2026-05-07.md         ← May 7 hand-written brief (markdown)
│   ├── brief_2026-05-07.5_wider-lens.md ← A/B comparison: gov + news outlets
│   ├── source_gap_analysis_2026-05-07.md ← analysis of what gov-only misses
│   ├── dod_bypass_findings_2026-05-07.md ← Akamai bypass research
│   └── (probe and debug scripts)
│
├── nginx/nginx.conf
├── pgadmin/                        ← (legacy admin UI)
└── logs/                           ← per-day operational logs (gitignored)
    └── (.run/ for synth intermediates, also gitignored)
```

---

## Recent non-obvious decisions

### 2026-05-10 (briefer.news LIVE; China brief sources scaffolded)

1. **AWS Amplify CNAME conflict resolved.** The `briefer.news` / `www.briefer.news` aliases were trapped on an Amplify-managed CloudFront distribution in our own us-east-2 (account `462170975634`, app `d3gh6znsloy9bt` named "briefer"). `cloudfront list-conflicting-aliases` masks the source account ID, so we couldn't locate it ourselves — AWS Support (Amplify team, Kajal G.) used internal tooling to find it. Fix: `aws amplify delete-domain-association --app-id d3gh6znsloy9bt --domain-name briefer.news --region us-east-2`, then `aws cloudfront associate-alias --target-distribution-id EMV1VIFYTSI3U --alias briefer.news` (and same for www). Total resolution: ~30 seconds of CLI once we knew where to look.
2. **China-source brief sources scaffolded.** `pipeline/config/china_sources.yaml` defines 23 active sources (MFA, State Council, Xinhua, NDRC, PBOC, MOF, MIIT, CAC, Stats Bureau, CCDI, NPC, Qiushi, Court, Procuracy, CSRC, SAFE, SASAC, Shanghai/Beijing/Guangdong/Zhejiang). Three held (SCIO/NFRA/Customs) for follow-up. `pipeline/scraper/china_scrape.py` mirrors the akamai pattern, adds bespoke MFA discovery + custom selectors (`pages_content`, `detail`). First scrape captured 499 articles across 11 sources (the other 12 sources have URL-pattern regex misses to fix). See `CHINA_BRIEF.md` for full state.

### 2026-05-09 (autonomous flow validated; world context added)

1. **First fully autonomous run worked end-to-end.** 04:00 scrape, 07:00 synth, fresh brief at http://localhost. No manual intervention needed. **The Path A → Path B leap (manual brief → autonomous AI synth) happened ahead of plan.**
2. **World-context layer added** as Stage 0 of `synthesize.sh`. `scripts/world_context.sh` runs Claude with WebSearch enabled (requires `--allowedTools WebSearch WebFetch Read Write Edit --permission-mode acceptEdits`). Output `~200 word` `world_context.md` is referenced by both picker and synthesizer prompts as **ambient signal, not directive**. The synthesizer can connect bullets to global narrative arcs without inventing facts.
3. **Headline accessibility rule added to BRIEF_STYLE.md.** Old "no jargon like CENTCOM" was too narrow — synthesizer was letting through GAESA, FY27, DFARS, oil-graft, etc. New rule: *if you'd have to explain a term at a dinner party, rewrite it.* Explicit substitutions table baked into both BRIEF_STYLE.md and the synth prompt.

### 2026-05-08 (autonomous launch + AWS infrastructure built)

1. **Dark mode set as default.** `<body class="theme-ink">`, picker `.active` moved to Dark button, JS fallback theme = ink. Light still available via the toggle.
2. **AWS deployment built.** S3 bucket `briefer-news-site` (us-east-1, private), OAC `E2XRSK5V6A89MY`, ACM cert for briefer.news + www.briefer.news, CloudFront distribution `EMV1VIFYTSI3U` at `d1sl4o5xm2ds0o.cloudfront.net`, Route 53 alias A-records pre-staged.
3. **AWS account split discovered**. Domain registered in `026090521469` (max@max.goshay@gmail.com); deployment account is `462170975634` (max@ghanzo@gmail.com). Both stay; nameservers updated to point at the deployment account's hosted zone `Z07630701MT6TMX2WHCGE`.
4. **AWS pipeline service profile-tagged.** `docker-compose.yml`'s `pipeline` service was originally `restart: unless-stopped` and got auto-started by nginx's `depends_on`, which fired the in-container APScheduler — competing with the LaunchAgent. Fix: `profiles: [manual]`, removed restart policy, removed nginx's depends_on. Pipeline image still used via `docker compose run --rm pipeline …`.
5. **`scripts/synthesize.sh` Stage 6 publishes to S3 + CloudFront** automatically. Non-fatal on AWS errors (local site still publishes if AWS is down).
6. **AWS Support upgrade required**: filing Technical cases requires Business+ ($29/mo). Subscribe → file → downgrade pattern is fine. **AWS rebranded "Developer Support" to "Business+"** at the same $29 price point.

### 2026-05-07 (Akamai bypass + brief format + automation plan)

(Preserved from prior CLAUDE.md — still relevant.)

1. **Akamai bypass is curl_cffi + Chrome TLS impersonation, free.** Confirmed working from a residential IP for war.gov, centcom.mil, navy.mil, jcs.mil, af.mil. NOT working from cloud datacenter IPs. See `pipeline/scraper/akamai_bypass.py`.
2. **DoD subdomains use DotNetNuke ArticleCS GetList API**. Module IDs: war.gov=2842, centcom.mil=1144, navy.mil=4025, jcs.mil=8253, af.mil=811.
3. **Rate limiting per Akamai domain: 90-180s** between fetches. See `_DOMAIN_INTERVALS` in `akamai_bypass.py`.
4. **Brief format locked at 9 bullets, 3 voices** (down from initial 16-bullet attempts).
5. **International audience by default** — domestic-only items capped at 3 of 9 bullets; DOJ items capped at 2 of 9.
6. **Gov-only sourcing chosen for trust posture** (vs. gov+news A/B in `research/brief_2026-05-07.5_wider-lens.md`).
7. **Original AWS infrastructure cleaned up.** Account dropped from $5.67/mo to $0.50/mo.

### 2026-05-05 (initial source foundation)

1. **WH URL was rebased** from `/briefing-room/` → `/news/` (covers all 4 content sections).
2. **DOJ Antitrust at `/atr/press-room-0`** (trailing `-0` is Drupal node-disambiguation).
3. **ARPA-E `link_pattern` MUST have trailing slash** (`/news-and-insights/`).
4. **`scraper/browser.py` `playwright_fetch` only waits for `networkidle`** — sites with perpetual background JS time out at 30s.

---

## Where to start reading (priority order, for new agents)

### If you have time for 3 docs:
1. **`CLAUDE.md`** (this file) — orientation
2. **`BRIEF_STYLE.md`** — editorial style guide; mandatory before any synthesis
3. **`CHINA_BRIEF.md`** — if your work touches the China side

### If you have time for more:
4. `lens.md` — interpretive framework (still load-bearing)
5. `scripts/synthesize.sh` — current synth pipeline (skim Stage 0-6 structure)
6. `scripts/daily.sh` — current scrape pipeline
7. `MIGRATION.md` — historical deployment runbook + Postmortem at bottom
8. `pipeline/main.py` — orchestrator entry point (--scrape-only / --akamai-only / --china-only)
9. `pipeline/scraper/akamai_bypass.py` + `akamai_scrape.py` — Akamai-source layer
10. `pipeline/scraper/china_scrape.py` — China-source layer (NEW)
11. `pipeline/db/models.py` — DB schema
12. `research/brief_2026-05-07.md` — example hand-written brief

### Skip unless specifically relevant:
- `PLAN_AUTOMATION.md`, `PLAN_PROCESSING.md`, `PLAN_SUMMARIZATION.md` (historical / superseded)
- `pipeline/processor/` (legacy AI integrations not used in production)
- `pipeline/builder/` (legacy Jinja2 path not used in production)

---

## Operational notes

### Running things manually
```bash
# Standard scrape (39 RSS, ~10 min):
docker compose run --rm pipeline python main.py --scrape-only

# Akamai-protected scrape (6 sources, ~30-60 min):
docker compose run --rm pipeline python main.py --akamai-only

# China gov scrape (23 sources, ~2-3h on first run):
docker compose run --rm pipeline python main.py --china-only

# Manual brief synthesis (the autonomous LaunchAgent at 07:00 calls this):
scripts/synthesize.sh

# Manual cleanup (7-day retention; runs as part of daily.sh):
scripts/cleanup.sh

# Generate world context (Stage 0 of synth):
scripts/world_context.sh

# Inspect a LaunchAgent's status:
launchctl list | grep briefer
launchctl print gui/$(id -u)/news.briefer.daily

# Manually trigger a LaunchAgent (skips schedule wait):
launchctl start news.briefer.daily
launchctl start news.briefer.synthesize
```

### Docker stack
- `docker compose up -d` brings up `postgres` (5433) + `adminer` (5050) + `nginx` (80). The `pipeline` service is profile-tagged (`profiles: [manual]`) so it does NOT auto-start; only ephemeral `docker compose run --rm pipeline …` invocations.
- Pipeline image needs `curl_cffi` (in `requirements.txt`).
- nginx serves the local site at `http://localhost`; same content also published to S3 + CloudFront for `https://briefer.news`.

### YAML validation
Always validate after editing source yamls:
```bash
python -c "import yaml; yaml.safe_load(open('pipeline/config/sources.yaml'))"
python -c "import yaml; yaml.safe_load(open('pipeline/config/akamai_sources.yaml'))"
python -c "import yaml; yaml.safe_load(open('pipeline/config/china_sources.yaml'))"
```

### AWS profiles
- `~/.aws/credentials` has two profiles: `default` (deployment account `462170975634`, user `maxbriefer`) and `registrar` (registrar account `026090521469`, user `max`).
- For Route 53 / S3 / CloudFront / ACM in the deployment account: default profile.
- For Route 53 Domains (the registrar) operations: `--profile registrar`.

### Headless `claude -p` requirements
The synth and world-context scripts use Claude Code in headless mode. Required flags:
- `--allowedTools` — explicit list. WebSearch, WebFetch, Read, Write, Edit at minimum for world_context.sh; Read, Write, Edit for synthesize.sh.
- `--permission-mode acceptEdits` — auto-accepts file writes
- `--max-turns 40` (synth) or `25` (world_context) — enough budget for chunked file reads
- Files outside `${REPO}/.run/` may not be readable by headless Claude (sandbox limit) — keep all intermediates in `.run/`.

### Git status as of 2026-05-10
Latest commit on `main`: `dd7b395 Update README to match the autonomous M4-mini pipeline`. About to add another commit batch for these doc refreshes + the China scaffolding (`china_sources.yaml`, `china_scrape.py`, `--china-only` in `main.py`, `CHINA_BRIEF.md`, new `MIGRATION.md` postmortem).
