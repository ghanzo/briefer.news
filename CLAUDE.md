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

## Where we are (current build stage)

Project is in **Stage 1 — Source Foundation** (US gov focus).

| Stage | Status | What "done" looks like |
|---|---|---|
| **1. Source foundation** | **In progress, US gov focus** | ~60+ active US gov sources, monitored, with operational notes |
| **2. End-to-end pipeline validation** | Not started | Docker stack runs, Postgres populates, no errors in scrape phase |
| **3. AI quality** | Not started | Stage 1 filter rejection reasons make sense; importance scores look right; Stage 2 summaries are crisp |
| **4. Editorial output** | Not started | Stage 3 daily brief is something Max would actually read |
| **5. Operations** | Stub-only | Scheduler runs, source rot detected, deployed |
| **6. Expansion** | Deferred | International + commercial + data APIs |

**Critical principle:** *Don't add more sources without seeing the pipeline output first.*
The user-facing test for what sources to add is the daily brief, not a probe count.
Stage 1 is closing out, not staying open indefinitely.

### Source counts as of last touch (2026-05-05)

- **44 active sources** (down from 70+ candidate set, intentionally curated)
- **5 HTML-scrape sources** (Playwright): White House News, DOJ Antitrust Press
  Room, DOE Newsroom, ARPA-E, ORNL
- **39 RSS sources** spanning State Dept (2), DoD, Federal Reserve, Treasury,
  USTR, GAO, DOJ NS, CISA, Federal Register (×2), CBP, DOJ OPA, FBI National,
  CFPB, BLS, BEA, CBO, NY Fed Liberty Street, GovInfo (3), Court of Appeals (2),
  EIA, plus international (BBC/AJ/DW/Yonhap/AllAfrica/UK/Kremlin/TASS/UN/WHO/
  IAEA), commercial (OilPrice, Mining.com, Hacker News).
- **~80 held sources** in `pipeline/config/sources.yaml` (`active: false`) ready
  to flip on.

### Pending decision (in flight as of 2026-05-05 night)

User decided to focus on US gov sources first. The natural next moves:

1. Move 14 currently-active non-US sources to held (BBC, AJ, DW, Yonhap,
   AllAfrica, UK Gov, Kremlin RU, TASS RU, UN, WHO, IAEA, OilPrice, Mining.com,
   Hacker News). Keep them in yaml as `active: false`, NOT delete.
2. Activate ~20 held US gov sources (State Dept regional desks, more FedReg
   feeds, GovInfo, Court of Appeals additional circuits, FBI Top Stories, DOL,
   DOE labs, etc.) — see SOURCES.md for the full held list.
3. Result: ~50–60 active US gov sources, 0 active international.
4. Then proceed to Stage 2 (Docker run, end-to-end validation).

The lens.md is **not** changing in this pivot. The lens still applies — we're
just feeding it US gov content first before adding global signal back later.

---

## Architecture map

```
briefernewsapp/
├── CLAUDE.md                       ← you are here
├── README.md                       ← user-facing project overview
├── AIMS.md                         ← interpretive framework + predictions
├── COVERAGE.md                     ← thematic dimensions (categories)
├── PLAN_PROCESSING.md              ← 3-stage pipeline architecture
├── PLAN_SUMMARIZATION.md           ← superseded; kept for cost notes
├── SOURCES_MATRIX.md               ← regional source coverage (★ ratings)
├── SOURCES_PLAN.md                 ← exhaustive source spec (aspirational)
├── SOURCES.md                      ← at-a-glance source status (active/held/broken)
├── SOURCE_NOTES.md                 ← per-source operational notes (depth)
├── lens.md                         ← THE interpretive framework — read this
├── docker-compose.yml              ← postgres + adminer + pipeline + nginx
├── .env.example                    ← required env vars
│
├── pipeline/                       ← main product
│   ├── main.py                       orchestrator (run_scrape + run_process)
│   ├── scheduler.py                  daily 06:00 trigger (via apscheduler)
│   ├── config/sources.yaml           SOURCE OF TRUTH for what gets scraped
│   ├── scraper/
│   │   ├── discovery.py              RSS + Playwright link discovery
│   │   ├── extractor.py              article extraction (trafilatura/BS4/playwright)
│   │   └── browser.py                Playwright singleton manager
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
└── research/                       ← scripts + raw data + samples (this session)
    ├── probe_sources.py              probe sources.yaml against live feeds
    ├── probe_candidates.py           probe candidate URLs from us_gov catalog
    ├── probe_blocked.py              browser-UA retry of HTTP-403 sources
    ├── test_html_scrape.py           end-to-end test for any web_scrape source
    ├── show_wh_samples.py            pull and save real WH articles
    ├── debug_*.py                    site-structure inspectors per source
    ├── *.json                        machine-readable probe results
    ├── *.md                          human-readable probe reports
    ├── us_gov_feeds_catalog_*.md     US-gov feed catalog (140+ candidates)
    └── wh_samples/                   saved article extractions
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

## Recent non-obvious decisions (2026-05-05 session)

1. **WH URL was rebased** from old `/briefing-room/` (now redirects) to
   `/news/` — covers all 4 content sections (briefings/releases/presidential-
   actions/research). `link_pattern: /202` matches date-prefixed article paths.
2. **DOJ Antitrust at `/atr/press-room-0`**, NOT `/atr/news-feeds` (which
   returned HTML index) or `/atr/news` (404). The trailing `-0` is a Drupal
   node-disambiguation artifact, not a typo.
3. **ARPA-E `link_pattern` MUST have trailing slash** (`/news-and-insights/`,
   not `/news-and-insights`). Without it, the bare listing URL leaks through.
4. **DEFERRED sources are documented in SOURCE_NOTES.md** — Atlanta Fed
   (JS-renders + low cadence). Don't re-investigate without checking that file
   first.
5. **`scraper/browser.py` `playwright_fetch` only waits for `networkidle`** —
   sites with perpetual background JS (Atlanta Fed, ANL, INL) time out at 30s.
   Several deferred candidates would unblock if we add a `domcontentloaded`
   fallback + selector wait. Not done yet.
6. **Probe-script bucketing display can mislead.** When a source has multiple
   article URLs all sharing a 2-segment prefix, the bucket count looks like
   "1 hit" because the example is one of many. The Phase 1 first-10-stubs
   list is the source of truth.

---

## Where to start reading (priority order, for new agents)

If you only have time for 5 docs:

1. **`CLAUDE.md`** (this file) — orientation
2. **`SOURCES.md`** — current source status table
3. **`SOURCE_NOTES.md`** — per-source operational notes (only the entries
   relevant to what you're doing)
4. **`lens.md`** — the interpretive framework
5. **`PLAN_PROCESSING.md`** — pipeline architecture

If you have more time, in priority order:
6. `AIMS.md` — full interpretive framework + predictions
7. `pipeline/main.py` — orchestrator code
8. `pipeline/scraper/discovery.py` + `extractor.py` — the scrape layer
9. `pipeline/processor/{filter,gemini,grok,claude}.py` — AI stages
10. `pipeline/db/models.py` — schema
11. `COVERAGE.md` — thematic dimensions (largely informs filter prompts)

---

## Operational notes

- **Local Python:** 3.14 with feedparser, httpx, yaml, playwright, BeautifulSoup,
  lxml all installed. Chromium binary at `~/AppData/Local/ms-playwright/`.
- **Docker not yet stood up** in current session. `docker-compose.yml` is ready;
  needs `.env` with `ANTHROPIC_API_KEY` (or XAI_API_KEY for Grok).
- **Yaml validation:** always run a `python -c "import yaml; yaml.safe_load(...)"`
  check after edits. The file is large (1000+ lines) and easy to break.
- **No commits since 2026-05-05 work began.** All today's research/ files,
  SOURCES.md edits, SOURCE_NOTES.md additions, sources.yaml expansions are
  uncommitted as of this writing. Plus the user's pre-existing Mar 7 work
  (templates, main.py, grok.py, prompts.py) was already uncommitted before
  today's session.
