# CLAUDE.md — Working in briefer.news

This file orients a fresh Claude session. Read it first.

---

## What this project is

**briefer.news** — a daily intelligence brief that ingests US government output
(plus international and commercial sources later), runs it through a 3-stage AI
pipeline, and produces a published daily brief. Owner is Max Goshay. Repo at
`github.com/ghanzo/briefer.news`.

Two codebases live in this repo:

1. **`pipeline/`** — the news-ingestion pipeline. RSS + HTML-scrape sources →
   Postgres → AI summarization → static HTML site. This is the main product.
2. **`briefer/`** — a separate Click-based CLI for ingesting economic time
   series (FRED, Yahoo Finance) into DuckDB with AI interpretation. Companion
   tool, not the main product.

The **interpretive lens** is in `lens.md` and `AIMS.md`. It hasn't changed.
Six layers in priority order: energy/resources, US-China axis, tech chokepoints,
financial currents, human systems, innovation signals.

---

## Where we are (current build stage — updated 2026-05-07)

| Stage | Status | What "done" looks like |
|---|---|---|
| **1. Source foundation** | **Functionally complete** | 45 active sources scraping daily; Akamai bypass for DoD subdomains live |
| **2. End-to-end pipeline validation** | **Scrape validated** | Docker stack runs; Postgres populates; ~400 articles/day from 45 sources |
| **3. AI quality** | **Manual synthesis only** | Stage 2/3 not yet wired; manual brief writing producing publishable output |
| **4. Editorial output** | **Prototype done, format locked** | Live prototype at `research/prototype_2026-05-06.html`; style codified in `BRIEF_STYLE.md` |
| **5. Operations** | **Plan locked, not built** | `PLAN_AUTOMATION.md` has decisions; M4 mini deployment scheduled for Sunday May 10 |
| **6. Expansion** | Deferred | International + commercial + data APIs |

**Critical principle:** *Don't add more sources without seeing the pipeline output first.*
The user-facing test for what sources to add is the daily brief, not a probe count.
Stage 1 is closed; we've moved into operational deployment phase.

### Source counts as of 2026-05-07

- **39 active US-gov RSS sources** in `pipeline/config/sources.yaml`
  spanning State Dept regional desks, DoD, Federal Reserve, Treasury,
  USTR, GAO, DOJ NS, CISA, Federal Register (×2), CBP, DOJ OPA, FBI National,
  CFPB, BLS, BEA, CBO, NY Fed Liberty Street, GovInfo (3), Court of Appeals (2),
  EIA, plus international (BBC/AJ/DW/Yonhap/AllAfrica/UK/Kremlin/TASS/UN/WHO/
  IAEA), commercial (OilPrice, Mining.com, Hacker News).
- **6 active Akamai-protected sources** in `pipeline/config/akamai_sources.yaml`
  scraped via separate `--akamai-only` stage with curl_cffi TLS-impersonation
  bypass: war.gov (DoD), centcom.mil, navy.mil, jcs.mil, af.mil, plus
  UK Ministry of Defence (gov.uk atom feed, not Akamai but uses the same path)
- **Total: 45 active sources** producing ~400 articles/day in latest run
- Held sources (`active: false`) remain in yaml ready to flip on later

### Daily scrape cadence

Two stages, run sequentially:

```bash
python pipeline/main.py --scrape-only      # ~10 min, 39 RSS sources, ~350 articles
python pipeline/main.py --akamai-only      # ~30-60 min, 6 Akamai-protected sources, ~50 articles
```

The Akamai stage uses curl_cffi with Chrome TLS impersonation to defeat
Akamai bot detection on DoD `.mil` subdomains. Implementation: `pipeline/scraper/akamai_bypass.py`.
Per-domain rate limits enforced (90–180s between requests for war.gov,
centcom.mil, etc.).

### Brief format (locked 2026-05-07)

The editorial style guide is `BRIEF_STYLE.md` at repo root. Key rules:

- **9 bullets** per brief (down from initial 16-bullet attempts)
- **3 voices**, 12–30 words each, mix of registers
- **Headline** 12–16 words, two clauses, plain English (no jargon like "CENTCOM")
- **≤2 DOJ items** unless DOJ is the day's dominant story
- **≤3 purely-domestic items** of 9 — international audience by default
- Each bullet has bold lead (2–4 words), citation, date · agency tag

The style guide has good/bad examples paired throughout. Synthesizer should
read this end-to-end before generating.

### Operational deployment plan

The full automation plan with locked decisions is `PLAN_AUTOMATION.md`. Highlights:

- Compute on M4 Mac mini (residential IP — important for Akamai bypass)
- Daily 04:00 cron firing scrape + (eventually) Stage 2/3 + publish to AWS
- AI synthesis: Claude Code on cron (primary), Anthropic API as fallback
- Hosting: S3 + CloudFront + ACM + Route 53 (briefer.news already in user's AWS)
- Full autopilot — no manual review window after stabilization
- Target first live publish: Monday 2026-05-11
- Migration steps: see `MIGRATION.md`

---

## Architecture map

```
briefernewsapp/
├── CLAUDE.md                       ← you are here
├── README.md                       ← user-facing project overview
├── BRIEF_STYLE.md                  ← editorial style guide (READ before any synthesis)
├── PLAN_AUTOMATION.md              ← deployment / cron / AWS plan with locked decisions
├── MIGRATION.md                    ← step-by-step setup for the M4 mini
├── AIMS.md                         ← interpretive framework + predictions
├── COVERAGE.md                     ← thematic dimensions (categories)
├── PLAN_PROCESSING.md              ← 3-stage pipeline architecture
├── PLAN_SUMMARIZATION.md           ← superseded; kept for cost notes
├── SOURCES_MATRIX.md               ← regional source coverage (★ ratings)
├── SOURCES_PLAN.md                 ← exhaustive source spec (aspirational)
├── SOURCES.md                      ← at-a-glance source status (active/held/broken)
├── SOURCE_NOTES.md                 ← per-source operational notes (depth)
├── DESIGN_REFERENCES.md            ← visual / typographic references (Citizen Lab etc.)
├── lens.md                         ← THE interpretive framework — read this
├── docker-compose.yml              ← postgres + adminer + pipeline + nginx
├── .env.example                    ← required env vars (mini needs a real .env)
│
├── pipeline/                       ← main product
│   ├── main.py                       orchestrator with --scrape-only / --akamai-only / --run-now flags
│   ├── scheduler.py                  daily trigger (via apscheduler)
│   ├── config/sources.yaml           SOURCE OF TRUTH for standard scrape (39 active US-gov RSS)
│   ├── config/akamai_sources.yaml    SOURCE OF TRUTH for akamai-protected scrape (6 active)
│   ├── scraper/
│   │   ├── discovery.py              RSS + Playwright link discovery (standard sources)
│   │   ├── extractor.py              article extraction (trafilatura/BS4/playwright)
│   │   ├── browser.py                Playwright singleton manager
│   │   ├── akamai_bypass.py          curl_cffi TLS-impersonation fetch + DNN ArticleCS API discovery (NEW 2026-05-07)
│   │   └── akamai_scrape.py          orchestrator for akamai-protected sources, fail-soft per source (NEW)
│   ├── processor/
│   │   ├── filter.py                 Stage 1: Groq Llama filter
│   │   ├── filter_criteria.md        ← edit this to tune what gets filtered
│   │   ├── gemini.py                 Stage 2: Gemini Flash article summarizer
│   │   ├── grok.py                   Stage 2 + 3: Grok (preferred provider)
│   │   ├── claude.py                 fallback Claude provider
│   │   ├── prompts.py                all prompt templates
│   │   ├── summarizer_instructions.md ← edit this to tune Stage 2 output
│   │   └── site_voice.md             ← edit this to tune Stage 3 voice
│   ├── builder/
│   │   ├── site.py                   Jinja2 → static HTML
│   │   └── templates/                base.html + index.html
│   ├── db/
│   │   ├── models.py                 SQLAlchemy: Source, Article, ArticleSummary,
│   │   │                              DailyBriefing, CategorySummary, ScrapeRun,
│   │   │                              RejectedUrlHash, BriefingOutput
│   │   └── migrations/001_initial.sql
│   └── output/                       generated HTML lands here, served by nginx
│
├── briefer/                        ← companion CLI for econ time series
│   ├── cli.py                        Click commands: pull, watch, digest, dashboard
│   ├── sources/{fred,yahoo}.py       data adapters
│   ├── analysis/{deltas,interpret}.py  metric computation + Claude analysis
│   ├── config/catalog.py             177 series catalog (FRED + Yahoo)
│   └── db/schema.py                  DuckDB tables
│
└── research/                       ← scripts + raw data + samples
    ├── prototype_2026-05-06.html     ← LIVE site prototype (refined design)
    ├── prototype_2026-05-07.html     ← dated archive of May 7 brief
    ├── brief_2026-05-06.md           ← May 6 brief (markdown source)
    ├── brief_2026-05-07.md           ← May 7 brief (markdown source — gov-only, on the live site)
    ├── brief_2026-05-07.5_wider-lens.md ← A/B comparison: gov + news outlets (NOT on site, archived)
    ├── source_gap_analysis_2026-05-07.md ← analysis of what gov-only misses vs news outlets
    ├── dod_bypass_findings_2026-05-07.md ← Akamai bypass research notes
    ├── probe_sources.py              probe sources.yaml against live feeds
    ├── probe_candidates.py           probe candidate URLs from us_gov catalog
    ├── probe_blocked.py              browser-UA retry of HTTP-403 sources
    ├── probe_mil_family.py           probe DoD .mil subdomains for ArticleCS module IDs
    ├── find_module_id.py             helper for discovering DNN moduleIDs
    ├── find_dod_api.py / inspect_dod_api.py / inspect_dod_js.py / probe_dod_rss.py — DoD API discovery scripts
    ├── test_html_scrape.py           end-to-end test for any web_scrape source
    ├── seals/                        agency seals (PNG/SVG, public domain)
    ├── images/                       generated test imagery (Hormuz cartographic)
    └── us_gov_feeds_catalog_*.md     US-gov feed catalog (140+ candidates)
```

---

## Conventions

### Adding a new source

The repeating pattern, validated 5× in 2026-05-05 session:

1. **For RSS:** add directly to `sources.yaml` as `type: rss`, run
   `research/probe_sources.py` to verify. If fresh, it's done.

2. **For HTML-scrape (Playwright):**
   1. Inspect the listing page (often via `research/debug_<source>.py` —
      saves the rendered HTML for review).
   2. Run `research/test_html_scrape.py` with `link_pattern: ""` to discover
      the URL structure.
   3. Find the substring pattern that catches articles but excludes nav/landing
      pages. Common patterns: `/202` (year-prefix), `/articles/`, `/opa/`,
      `/news-and-insights/` (trailing slash often load-bearing).
   4. Re-run `test_html_scrape.py` with the right `link_pattern` — confirm 10+
      stubs and ≥3 successful extractions.
   5. Add to `sources.yaml` in the **HTML-scrape (Playwright)** subsection of
      ACTIVE block.
   6. Add a per-source entry to `SOURCE_NOTES.md` (template at top of that file).
   7. Add a row to `SOURCES.md` in the HTML-scrape table.
   8. Update yaml header counts and the `# ACTIVE — N sources` comment.

### Probe scripts

- `research/probe_sources.py` reads `pipeline/config/sources.yaml` and tests
  every entry. Output: `research/probe_<DATE>.json` + `.md`.
- `research/probe_candidates.py` tests a hardcoded list of new candidate URLs
  (used for catalog discovery, not config).
- `research/probe_blocked.py` retries HTTP 403 candidates with browser-UA.

These ran in ~25 seconds for ~150 sources parallelized. Re-run periodically;
sources rot silently.

### File-encoding gotcha

Python-on-Windows console can't encode emoji to charmap. Probe scripts strip
non-ASCII before printing AND set `$env:PYTHONIOENCODING = "utf-8"` in
PowerShell calls. Don't print emoji to stdout in scripts that might run
unattended.

### Editing prompts

The three editorial prompts live in markdown files and are loaded into the
prompt at runtime:
- `pipeline/processor/filter_criteria.md` — Stage 1 Groq filter
- `pipeline/processor/summarizer_instructions.md` — Stage 2 article summarizer
- `pipeline/processor/site_voice.md` — Stage 3 brief voice

**Edit these to tune output, not the Python prompt strings.** They're injected
into prompts as-is. Treat like code.

---

## Recent non-obvious decisions

### 2026-05-07 (Akamai bypass + brief format + automation plan)

1. **Akamai bypass is curl_cffi + Chrome TLS impersonation, free.** Confirmed
   working from a residential IP for war.gov, centcom.mil, navy.mil, jcs.mil,
   af.mil. NOT working from cloud datacenter IPs — production deploy MUST be
   on the M4 mini's home connection. See `pipeline/scraper/akamai_bypass.py`.
2. **DoD subdomains use DotNetNuke ArticleCS GetList API** for article
   discovery. Module IDs: war.gov=2842, centcom.mil=1144, navy.mil=4025,
   jcs.mil=8253, af.mil=811. Discoverable via `dnn_ctr<NUM>_Article_*` ID in
   page source. Three different listing-card formats handled in the parser
   (story-card, listing-with-preview, generic anchor with /Article/<digit>/
   pattern).
3. **Akamai defenders are per-org, not strictly shared.** war.gov and centcom
   probably share DoD's contract; ODNI / NATO / UK MoD are separate. But a
   residential IP making rapid probes against any one Akamai property CAN get
   that specific property's session flagged. Cooldown: typically 4-12 hours.
4. **Rate limiting per Akamai domain: 90–180s between fetches** (war.gov,
   centcom.mil, navy.mil), 60–120s for less-strict ones. See `_DOMAIN_INTERVALS`
   in `akamai_bypass.py`.
5. **Brief format locked at 9 bullets, 3 voices.** See `BRIEF_STYLE.md`. Earlier
   experiments at 16 bullets felt long; 9 is the right density for "what
   happened today" without padding.
6. **International audience by default** — domestic-only items capped at 3 of
   9 bullets; DOJ items capped at 2 of 9.
7. **Headline rule: plain English, no jargon** — replaced "CENTCOM strikes
   Iranian targets" with "U.S. forces strike Iranian targets" because most
   readers don't know what CENTCOM is.
8. **Gov-only sourcing was tested vs gov+news, gov-only chosen.** A/B comparison
   in `research/brief_2026-05-07.5_wider-lens.md` shows what wider sources add
   (Pakistan mediation, UK position, French ship attack, war origin context).
   Decision: stay gov-only for trust posture.
9. **AWS infrastructure cleaned up 2026-05-07.** Account dropped from $5.67/mo
   to $0.50/mo. Killed: WorkMail, gptnews.earth zone, stopped EC2 instance,
   zombie S3 buckets, failed ACM certs. Kept: briefer.news Route 53 zone.
   See git log for commit `79071ce..de66583` window.
10. **Automation locked.** Claude Code on cron primary, API fallback. Full
    autopilot, no manual review. S3+CloudFront. Target Monday 2026-05-11.
    See `PLAN_AUTOMATION.md`.

### 2026-05-05 (initial source foundation)

1. **WH URL was rebased** from old `/briefing-room/` (now redirects) to
   `/news/` — covers all 4 content sections. `link_pattern: /202` matches
   date-prefixed article paths.
2. **DOJ Antitrust at `/atr/press-room-0`**, NOT `/atr/news-feeds` (HTML
   index) or `/atr/news` (404). Trailing `-0` is Drupal node-disambiguation,
   not a typo.
3. **ARPA-E `link_pattern` MUST have trailing slash** (`/news-and-insights/`).
4. **DEFERRED sources documented in SOURCE_NOTES.md** — Atlanta Fed (JS-renders
   + low cadence), ANL, INL.
5. **`scraper/browser.py` `playwright_fetch` only waits for `networkidle`** —
   sites with perpetual background JS time out at 30s.

---

## Where to start reading (priority order, for new agents)

If you only have time for 5 docs:

1. **`CLAUDE.md`** (this file) — orientation
2. **`BRIEF_STYLE.md`** — editorial style guide; mandatory before any synthesis
3. **`PLAN_AUTOMATION.md`** — what we're deploying and why
4. **`MIGRATION.md`** — step-by-step setup if you're on a fresh machine
5. **`lens.md`** — interpretive framework

If you have more time, in priority order:
6. `research/brief_2026-05-07.md` — most recent brief, the canonical example
7. `pipeline/main.py` — orchestrator with --scrape-only / --akamai-only flags
8. `pipeline/scraper/akamai_bypass.py` + `akamai_scrape.py` — Akamai-source layer
9. `pipeline/scraper/discovery.py` + `extractor.py` — standard-source layer
10. `pipeline/db/models.py` — DB schema
11. `SOURCES.md` + `SOURCE_NOTES.md` — source status and per-source notes
12. `AIMS.md` + `COVERAGE.md` — interpretive framework + thematic dimensions

---

## Operational notes

- **Production deploy is on M4 Mac mini at user's home** (residential IP
  required for Akamai bypass). Setup steps in `MIGRATION.md`.
- **Docker stack:** `docker-compose.yml` runs Postgres (5433), Adminer (5050),
  pipeline container, nginx. Pipeline image needs `curl_cffi` (already in
  `requirements.txt`).
- **Python deps install via Docker.** Local Python on dev machines may not
  have all deps; canonical env is the pipeline container.
- **Yaml validation:** always run `python -c "import yaml; yaml.safe_load(open('pipeline/config/sources.yaml'))"`
  after edits. Files are large and easy to break.
- **Two scrape commands daily** (in order):
  ```bash
  python main.py --scrape-only      # 39 standard RSS, ~10 min, ~350 articles
  python main.py --akamai-only      # 6 Akamai-protected, ~30-60 min, ~50 articles
  ```
- **Git is current as of 2026-05-07.** `97393ef` is the latest commit on `main`.
  Includes: akamai bypass module + scraper + sources, BRIEF_STYLE.md,
  PLAN_AUTOMATION.md, two May-7 brief versions (gov-only on site, wider-lens
  archived).
