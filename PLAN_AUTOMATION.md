# Briefer News — Automation Plan

> The daily brief, automated. Compute on your M4 Mac mini at home;
> publish to AWS each morning. Drafted: 2026-05-07.

---

## Goal

A daily brief that runs unattended overnight on the Mac mini, generates the day's published page in the May-6 cadence, and pushes the finished artifact to briefer.news on AWS — with you reviewing nothing in the steady state, but able to intercept and edit before publish if you want.

You should be able to wake up at 8am, open `briefer.news` on your phone, and read today's brief.

---

## Architecture overview

```
┌─────────────────────────────────────────────────────┐
│  M4 Mac mini (home)                                 │
│  ──────────                                         │
│  • Postgres (the master DB — never leaves the mini) │
│  • Pipeline code (Python, scraper + builder)        │
│  • Claude Code OR Claude API (synthesis)            │
│  • Generated static site (output/)                  │
│                                                     │
│  ┌──────┐   ┌──────────┐   ┌──────────┐   ┌──────┐  │
│  │Scrape│ → │Filter (G)│ → │Summarize │ → │Brief │  │
│  │      │   │  (Groq)  │   │ (Claude) │   │ (Cl.)│  │
│  └──────┘   └──────────┘   └──────────┘   └──────┘  │
│       ↓                                       ↓     │
│   articles                              brief.json  │
│   in DB                                             │
│                                                     │
│  Build → static HTML in output/                     │
└────────────────────┬────────────────────────────────┘
                     │  rsync / aws s3 sync (~100KB/day)
                     ↓
┌─────────────────────────────────────────────────────┐
│  AWS                                                │
│  ──────────                                         │
│  • S3 bucket: static-site files                     │
│  • CloudFront: CDN + HTTPS                          │
│  • Route 53: briefer.news → CloudFront              │
│                                                     │
│  No database. No compute. Just static hosting.      │
└─────────────────────────────────────────────────────┘
```

**Key principle:** the mini is the source of truth. AWS holds only the rendered output. If AWS dies, you re-deploy from the mini. If the mini dies, AWS keeps serving yesterday's brief until you fix it.

---

## Daily timeline (mini, all times local)

| Time | Stage | Approx. duration | Owner |
|---|---|---|---|
| 04:00 | **Wake from sleep** (LaunchAgent) | — | macOS |
| 04:00 | **Stage 1: Scrape** | 8–15 min | Python (no AI) |
| 04:15 | **Stage 1.5: Filter** | 30 sec | Groq API (cheap) |
| 04:20 | **Stage 2: Summarize articles** | 5–15 min | Claude (Code or API) |
| 04:35 | **Stage 3: Synthesize brief** | 1–2 min | Claude (Code or API) |
| 04:40 | **Build static HTML** | <30 sec | Python/Jinja2 |
| 04:45 | **Publish to AWS** | 30 sec | aws s3 sync |
| 04:50 | **Done — site live** | — | — |

Total wall clock: ~50 minutes. Most of the time is in scrape (HTTP-bound) and Stage 2 summarization (one Claude call per article, ~30/day after filtering).

If you want a manual review window, a cleaner schedule is:

| Time | Stage |
|---|---|
| 04:00 | Scrape + Filter + Summarize → produces draft brief in `output/draft/` |
| 04:45 | LaunchAgent stops here. Draft sits ready. |
| 07:00 | (Optional) you review the draft on phone or laptop |
| 07:30 | Approve → second LaunchAgent triggers `build + publish` |
| 07:35 | Live |

This gives you 2.5 hours to wake up, glance at the draft, and decide whether to publish, edit, or skip the day. Belt-and-suspenders for the first month while you're tuning the pipeline.

---

## Components (per stage)

### Stage 1 — Scrape (no AI)

Already built. Lives in `pipeline/scraper/`. Currently runs in ~10 minutes for ~300 articles across 39 active sources.

**What it does:** RSS discovery + HTML scrape (Playwright for JS-heavy sources) + extract full text → write to Postgres `articles` table.

**Cron command:**
```bash
cd ~/briefernewsapp/pipeline && python main.py --scrape-only
```

**Failure modes:**
- Network outage → no articles scraped today. Pipeline should detect (count check) and skip Stage 2/3 with a clear error.
- Source rot (URL pattern changed) → that one source returns 0 stubs. Pipeline continues; logged but doesn't fail the run.
- DB connection issue → hard fail. Need monitoring.

### Stage 1.5 — Filter (cheap API)

Already supported. Uses Groq Llama 3 to filter ~300 stubs down to ~50 worth summarizing.

**Cost:** ~$0.001/day (literal cents/year).

**Why it matters:** without filter, Stage 2 would summarize 300 articles via Claude — way more cost (and time) than necessary. Filter trades $0.001 of Groq for $1+ of Claude.

**Cron:** runs as part of `pipeline/main.py` already. Just needs `GROQ_API_KEY` in `.env`.

### Stage 2 — Summarize (Claude)

For each filtered article (~30–50/day), produce a structured summary: headline, summary, importance score, category, tags, named entities.

**Cost via API (Claude Haiku):** ~$0.001 per article × 50 articles = $0.05/day · ~$18/year.
**Cost via API (Claude Sonnet):** ~$0.01 per article × 50 articles = $0.50/day · ~$180/year.
**Cost via Claude Code subscription:** $0 incremental, but counts against your usage limits.

**Recommendation:** Haiku via API. It's cheap, predictable, and frees Claude Code for higher-value work. If you really want to use Claude Code here, see the headless-Claude-Code section below.

### Stage 3 — Synthesize brief (Claude)

The big one. Reads all summaries from today + the lens (lens.md) + the style guide (BRIEF_STYLE.md) and generates the final brief in May-6 cadence.

This is the **single most consequential AI step** — quality here determines whether the brief is good or bad.

**Approach options:**

| Approach | Cost | Quality | Notes |
|---|---|---|---|
| **Claude API (Sonnet)** | ~$0.10/day · ~$36/year | High, predictable | Best default. Designed for this. |
| **Claude API (Opus)** | ~$0.50/day · ~$180/year | Highest | Worth it if Sonnet drift is real. |
| **Claude Code (headless)** | $0 incremental | Same as API | Counts against subscription limits. See caveats below. |

**Recommendation:** Start with Claude API Sonnet. Cheap, contractually clean, fully supported. If you find that you want Claude Code's specific behavior (file-walking, tool use, etc.), we can switch later.

### Stage 4 — Build static HTML

Already built (Jinja2 templates in `pipeline/builder/`). Reads brief JSON from DB + style guide + writes to `output/index.html` and `output/archive/YYYY-MM-DD.html`.

The current Jinja templates are from an older design. Need to update to match the May-6 prototype HTML (the typographic system we've built). One-time port, then it just runs daily.

### Stage 5 — Publish to AWS

```bash
aws s3 sync ~/briefernewsapp/output/ s3://briefer-news-site/ --delete
aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"
```

Where:
- `briefer-news-site` is the S3 bucket (need to create)
- CloudFront distribution sits in front (need to create)
- Route 53 already exists for briefer.news → just need an A/AAAA alias to the new CloudFront distribution

**Cost:** S3 ~$0.01/month for site storage; CloudFront ~$0/month at this traffic (free tier covers it); Route 53 already $0.50/month (zone hosting).

---

## On Claude Code via cron

**Is it technically possible?** Yes. Claude Code's CLI supports headless mode:

```bash
claude -p "Read @input.json, follow @BRIEF_STYLE.md, output brief.json" \
  --output-format json \
  --max-turns 10 \
  > brief.json
```

A LaunchAgent could trigger this on schedule. Authentication uses the OAuth token cached in `~/.claude/`, so once you've signed in interactively once, the cron job uses that session.

**Caveats:**

1. **Subscription terms.** Claude Pro/Max plans are intended for individual interactive use. Running automated cron jobs *might* trip Anthropic's automation-policy clauses. For one-job-per-day personal use it's likely fine, but it's not what the subscription is designed for. The API is the contractually clean path.

2. **Usage limits.** Pro = 5-hour rolling window cap. If your cron job hits Stage 2 + Stage 3 in one window, plus you do interactive work earlier in the day, you could blow the cap. Max plans have higher limits but still finite.

3. **Auth token expiry.** OAuth tokens refresh, but if the refresh fails (network issue, account event) the cron job dies silently. API keys don't have this problem.

4. **Tooling.** Claude Code has access to file-system tools, git, etc., which Stage 3 doesn't really need. Overkill for a synthesis call.

**My take:** Use the **API for Stage 2 + 3**. It's $30–50/year for the highest-quality option, fully supported, no auth-expiry surprises. Reserve Claude Code for interactive work like editing the style guide, debugging the pipeline, and inspecting results — exactly what you're doing now.

If you really want to lean into the existing subscription, the hybrid that makes most sense:
- Stage 1.5 (filter): Groq API, cheap
- Stage 2 (summarize): Claude API Haiku, very cheap
- Stage 3 (synthesize): Claude Code in headless mode, $0 incremental but slower and contractually adventurous

---

## Authentication & secrets (on mini)

Lives in `~/briefernewsapp/.env`:

```
DATABASE_URL=postgresql://briefer:...@localhost:5432/briefer
GROQ_API_KEY=gsk_...        # for Stage 1 filter
ANTHROPIC_API_KEY=sk-ant... # for Stage 2 + 3 (if using API)
AWS_ACCESS_KEY_ID=AKIA...   # for S3 sync
AWS_SECRET_ACCESS_KEY=...
CLOUDFRONT_DISTRIBUTION_ID=E...
```

Permissions on `.env` should be `chmod 600` (owner-only). Mac LaunchAgent inherits the user environment.

If using Claude Code instead of API: no `ANTHROPIC_API_KEY` needed. Auth lives in `~/.claude/` and is invisible to the pipeline.

---

## Power & wake-from-sleep

The mini needs to be available at 04:00 every day.

**Recommended config (System Settings → Energy):**
- "Prevent automatic sleeping" when display is off — leave on. M4 mini idles at ~3W; ~$3/year electricity.
- Schedule a wake-up at 03:55 just before the cron job (belt-and-suspenders for sleep edge cases).

Or use `pmset` from terminal:
```bash
sudo pmset repeat wakeorpoweron MTWRFSU 03:55:00
```

---

## Failure modes & monitoring

What can go wrong, in rough order of likelihood:

| Failure | Symptom | Detection | Action |
|---|---|---|---|
| Network out at 4am | Scrape returns 0 articles | `articles_extracted < 50` | Skip Stage 2/3; serve yesterday's brief; notify. |
| Source pattern rot | One source contributes 0 | Per-source count drift | Logged, brief continues, flag for next-day review. |
| Postgres locked / corrupted | DB connection error | Stage 1 hard fail | Halt; notify immediately. |
| Claude API down | Stage 2/3 timeout | Fail after 3 retries | Fall back to manual; preserve summaries for retry. |
| Claude Code session expired | (Code-only) auth error | Run script returns non-zero | Notify; needs manual re-auth. |
| AWS push fails | S3 sync error | exit code | Site stays at yesterday's; notify. |
| Brief is garbage | Output looks wrong | Hard to detect automatically | Manual review window catches it. |

**Notification options:**

1. **Email-on-failure** — `mail` command + `cron` MAILTO= setup. Simple, but easy to miss.
2. **Push notification** — Pushover (one-time $5, lifetime), Pushbullet, or `terminal-notifier` + iCloud sync.
3. **Status page** — `~/briefernewsapp/status.json` that the build also pushes to S3. You have a `briefer.news/status` URL that always shows last-run state.

I'd start with #2 (Pushover to phone). $5 once, real-time alerts, takes 10 minutes to wire up.

---

## AWS handoff contract

What goes from mini → AWS each day:

```
output/
├── index.html              ← today's brief, the home page
├── archive/
│   ├── 2026-05-08.html     ← today's permanent archive page
│   └── (one per past day)
├── seals/                  ← agency seals (only re-pushed if changed)
├── images/                 ← brief imagery (none for now)
└── style.css               ← actually inline in index.html — no separate file
```

What does NOT go to AWS:
- Postgres database
- Article full-text
- Pipeline code
- `.env` secrets
- Logs

**S3 sync command:**
```bash
aws s3 sync output/ s3://briefer-news-site/ --delete
```

Total daily upload: ~100KB (one new HTML file + maybe an updated index). Free tier covers it indefinitely.

---

## Phasing — what to build first

I'd structure this in five phases, each independently shippable:

### Phase 1: Stage 1 + Stage 2 + Stage 3 wired up locally (no AWS)
- Pipeline currently halts at scrape; need to wire Stage 2 + 3 with API keys.
- Output: `output/index.html` rendered locally.
- Verify by opening `file:///path/to/output/index.html` in browser.
- **Done when:** running `python main.py --run-now` produces a publishable brief on disk in 30–60 minutes.

### Phase 2: Update Jinja templates to match May-6 prototype
- Port the typographic system from `prototype_2026-05-06.html` into `pipeline/builder/templates/`.
- Variables: `headline`, `voices[]`, `items[]`, `sources[]`, `date`, `issue_number`.
- **Done when:** generated `output/index.html` looks identical to the prototype.

### Phase 3: Move pipeline to mini
- Install Postgres, Python, dependencies on mini.
- Migrate DB (or just start fresh — sources.yaml is the source of truth).
- Test full pipeline end-to-end on mini.
- **Done when:** `python main.py --run-now` works on mini.

### Phase 4: AWS hosting setup
- Create S3 bucket + CloudFront distribution + ACM cert.
- Update Route 53 to point briefer.news at CloudFront.
- Push first version of `output/` manually.
- **Done when:** briefer.news shows the brief.

### Phase 5: Cron / LaunchAgent + monitoring
- LaunchAgent plist for daily 04:00 trigger.
- Pushover integration for failure notifications.
- Wake/sleep schedule.
- **Done when:** wake up the next day, check phone, see "brief published" notification, open briefer.news → today's brief.

Each phase is 1–3 sessions. Phases 1 + 2 are the longest because they involve real engineering (template port, prompt tuning).

---

## Improvements / things to add to the plan

Things you didn't mention that I'd build in:

1. **Manual review window** — recommended for the first month. Pipeline produces a draft at 04:30; you review on phone at 7am; approve to publish. Drops out of the loop once the system is reliable.

2. **Yesterday-fallback** — if today's pipeline fails, the AWS site keeps serving yesterday's brief automatically. Easy: don't push if Stage 3 fails. CloudFront serves the cached previous index.html.

3. **Archive page** — every day's brief gets a permanent URL at `briefer.news/2026/05/08`. Adds an archive list page accessible from the footer.

4. **RSS feed** — auto-generated from each day's brief. Subscribers get the brief in their reader without visiting the site. ~50 lines of code.

5. **Status endpoint** — `briefer.news/status.json` showing last-successful-run timestamp, source counts, and any active warnings. Makes diagnostic from anywhere trivial.

6. **Dry-run flag** — `python main.py --run-now --dry-run` runs the full pipeline but doesn't push to AWS. Use this for testing prompt changes without polluting production.

7. **Snapshot before publish** — before `aws s3 sync --delete`, snapshot the current site state to `s3://briefer-news-site-backups/` so you can roll back if a bad publish goes through.

8. **Prompt versioning** — each brief should record which version of `BRIEF_STYLE.md` was used to generate it. If output quality drifts, you can correlate with prompt changes. Just stamp the git SHA into a brief metadata field.

---

## Decisions (locked 2026-05-07)

1. **Stage 2 + 3 AI provider:** **Claude Code on cron (primary).** Anthropic API as **backup fallback** if Claude Code fails (auth expired, usage limit hit, etc.). The pipeline detects Claude Code failure and falls back to API automatically.
2. **Manual review window:** **No — full autopilot from day one.** Brief publishes at ~04:50; user sees it for the first time when they wake up.
3. **AWS deployment:** **S3 + CloudFront + ACM** — cheapest path, fastest delivery, automatic HTTPS.
4. **Monitoring channel:** TBD (see "Monitoring" below).
5. **First publish target:** **Today if possible, else Monday 2026-05-11.** Phase 1 today (local proof-of-concept); phases 2–5 by Monday if we move quickly.

---

## What's NOT in this plan

- **Newsletter/email distribution** — explicitly out of scope for v1. RSS only.
- **Social media auto-posting** — out of scope. You can tweet manually if you want.
- **Comments / community** — never. The brief is read-only.
- **Multiple briefs per day** — out of scope. One brief, one publish, every morning.
- **Multiple language editions** — out of scope. English only.
- **Paywall / subscriptions** — out of scope. The brief is free; sources are public.

Each of these is reasonable to add later. None should distract from getting the daily brief reliable first.

---

## Reference files

- `CLAUDE.md` — project orientation
- `BRIEF_STYLE.md` — editorial style guide (the synthesizer's constitution)
- `lens.md` — interpretive framework
- `pipeline/main.py` — orchestrator (currently scrape-only is wired)
- `docker-compose.yml` — current local stack (Postgres, pipeline, nginx)

---

## What I'd build first (concrete next session)

When you're ready to move from prototype to pipeline, the first session's work is:

1. Set up `.env` on this Windows box with `ANTHROPIC_API_KEY` (test key, low limit).
2. Wire `pipeline/main.py --run-now` to actually call Stage 2 + 3 with the recent May 7 scrape data.
3. Generate one brief end-to-end into `output/index.html` (using the May-6 prototype template).
4. Compare against the manually-tightened May 7 brief I just produced.
5. Iterate on the Stage 3 prompt until output matches manual quality.

This is "Phase 1" only — no Mac mini work, no AWS work yet. It's the proof-of-concept that the pipeline can do what we just did manually. Once that lands, the rest is operational engineering.

Total time estimate to live site: **3–5 working sessions** if dedicated. Could be longer if Stage 3 prompt-tuning takes more iteration than expected (this is the single biggest unknown — the manual May-6 brief took human judgment that the AI has to be coached to replicate).
