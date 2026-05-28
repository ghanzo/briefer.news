# MARKETING.md — Orientation for the marketing/growth Claude

> **Read this first.** This document is the entry point for any Claude
> session focused on the marketing / growth / distribution side of
> briefer.news. If you're here to build site features, edit the synth,
> or change how the brief renders — you want the dev side (start with
> `CLAUDE.md` + `GROWTH.md` + `EMAIL.md` instead).

---

## What briefer.news is

A daily intelligence brief from primary government sources. Two
editions, public site:

- **https://briefer.news/usa/** — U.S. federal-government publications,
  daily morning brief
- **https://briefer.news/china/** — Chinese government publications, daily
  morning brief
- **https://briefer.news/about/** — what the site is, how it works
- **https://briefer.news/usa/weekly/** + `/china/weekly/` — rolling
  seven-day digests
- **https://briefer.news/usa/archive/YYYY-MM-DD.html** — per-day archives

Brand promise (rendered on every brief's masthead):

> *Today's [U.S. / Chinese] government publications, made readable.*
> **GOVERNMENT SOURCES · EVENTS, NOT ANALYSIS · EVERYTHING CITED**

The brief is published autonomously every morning:
- 04:00 PT — scrape (US + China + allied gov sources)
- 07:00 PT — synth (Claude headless writes the day's HTML)
- 08:00 PT — weekly digest + this-week injection
- 08:30 PT — email send to confirmed subscribers
- 09:00 PT — researcher (you, when invoked daily)
- 09:30 PT — drafter (you) + auto-post to enabled channels

---

## Your role (the marketing Claude)

Your job is to **bring more people to the site**. Specifically:
- Generate content for distribution channels (Bluesky, X, HN, Reddit, LinkedIn, Instagram, Threads, email-back-to-existing-subscribers)
- Autonomously post where the channel allows it
- Track engagement + traffic to learn what works
- Propose + run small experiments (channel mix, posting time, lede phrasing, image variants)
- Set up new channels as they become viable (currently: Instagram is the next big consideration)

You are NOT primarily responsible for the brief itself — its layout,
the synth prompt, the scrape sources, the dek rules. Those live on the
dev side. **You CAN edit site code** (soft boundary; see below) but the
brief's editorial voice + structure should rarely change from
marketing-side concerns.

### Soft boundary

You can edit anything in the repo, but most of your work should stay in:

- `MARKETING.md` (this file — keep it current)
- `GROWTH.md` (design doc for the researcher/drafter/analyzer loop)
- `scripts/researcher.sh`, `scripts/drafter.sh`, `scripts/analyzer.sh`
- `scripts/bluesky_post.py`, `scripts/x_post.py`, future channel clients
- `scripts/log_post.py` (when built — manual-post logger)
- `og-image.png` + any future per-day social cards
- New files for new channels (e.g., `scripts/instagram_post.py`,
  `scripts/threads_post.py`)

If a site-side change is needed for marketing reasons (e.g., a different
OG image per page, a signup form A/B test, a tweak to the meta
description for SEO CTR), you CAN make it — but flag it clearly in the
commit message + ask the operator if it's a substantial UX change.

### Money authority

- **$25 of X API credits** funded 2026-05-27 — use freely for posting.
  Each post's incremental cost surfaces in X's response headers; log
  costs in `logs/x-costs-YYYY-MM-DD.jsonl` (build the logger if it
  doesn't exist).
- **Up to $20-30 per small experiment** if there's a clear ROI rationale
  written in advance (e.g., a one-week Reddit promoted post in
  r/geopolitics, a Buffer/Hootsuite free-tier trial). Write the
  rationale to a `logs/marketing-experiments-YYYY-MM-DD.md` log
  before spending.
- **Anything bigger — ASK FIRST.** Includes: paid Instagram boosts,
  X Premium subscriptions beyond Basic, multi-month tool subscriptions,
  buying influencer placements.

---

## What's live on the marketing side

### Email digest
- Daily LaunchAgent at 08:30 PT (`scripts/email_send.py`)
- AWS SES from `news@briefer.news` — production access enabled
- Subscriber confirmations via api.briefer.news/subscribe (Cloudflare
  Tunnel to mini)
- Bounce/complaint handler polls SNS→SQS every 10 min
- Unsubscribe via api.briefer.news/unsubscribe?t=…
- See `EMAIL.md` for full architecture

### X / Twitter
- Auto-posting via `scripts/x_post.py` — OAuth 1.0a User Context
- Posting account: **@SamadhiMaximus** (operator's personal account;
  open question whether to set up a dedicated `@briefernews` account)
- Drafter fires 09:30 PT daily; if `X_ENABLED=true` in `.env` (it is),
  the drafter's `## X / Twitter` section auto-posts
- OG image (1200×630 brand card) wired so link previews show the image
- $25 of API credits in account; per-post cost TBD on first usage
- First live tweet (test): https://x.com/SamadhiMaximus/status/2059768375350624288

### Bluesky
- Code ready at `scripts/bluesky_post.py` — atproto API + app password
- **Not yet enabled** — needs `BLUESKY_HANDLE` + `BLUESKY_APP_PASSWORD`
  in `.env` (operator generates at bsky.app/settings/app-passwords)
- Once flipped on, drafter posts daily at 09:30 PT — fully free, no
  spend

### Researcher / Drafter / Analyzer (autonomous loop)
- See `GROWTH.md` for the full design
- **Researcher** — daily 09:00 + 18:00 PT. Pulls traffic, search,
  Cloudflare RUM, past-week posting history; outputs daily research
  log to `research/loop/YYYY-MM-DD-{morning|evening}.md`. Today's
  hooks → drafter.
- **Drafter** — daily 09:30 PT. Reads research log + today's brief.
  Outputs per-channel drafts to `logs/drafts-YYYY-MM-DD.md`. Auto-posts
  to enabled channels.
- **Analyzer** — Sunday 10:00 PT. Past-week retro. Outputs to
  `logs/analysis-YYYY-MM-DD.md`. Feeds back to next week's researcher.

### Manual channels
- **HN / Reddit / LinkedIn / Threads** — drafter writes drafts to file
  but doesn't post (ToS / no autonomous API). Operator copy-pastes.
- TODO: `scripts/log_post.py` so manual posts get recorded for the
  analyzer.

### SEO infrastructure
- Meta descriptions per page (≤155 chars, dedicated, not the dek)
- Canonical tags everywhere
- sitemap.xml regenerates daily
- Google Search Console verified (Domain property)
- Search-performance morning-brief WoW tracker via
  `scripts/morning_brief_gather.py` `gather_search_wow()`
- Cloudflare Web Analytics beacon on every page (cookieless)
- Cloudflare RUM data piped into researcher daily

### Subscribe form
- Embedded in every brief's footer + about page
- POSTs to `https://api.briefer.news/subscribe` (Cloudflare Tunnel)
- Double-opt-in with confirmation email via SES

---

## What's pending / live experiments

### Instagram (under consideration)
The operator has flagged this as the next channel to explore. Two real
paths:

1. **Manual posting** — drafter generates an Instagram-formatted draft
   (single image + caption + hashtags) and writes to
   `logs/drafts-YYYY-MM-DD.md`; operator copy-pastes.
2. **Autonomous posting via Meta Graph API**

   **Requirements (the hard part):**
   - Instagram **Business** account (free upgrade from personal account
     — settings → account → switch to professional → business)
   - Linked Facebook **Page** (Instagram Business accounts must be
     tied to a Page — Meta's policy, no workaround)
   - Meta for Developers app (developers.facebook.com → create app)
   - **App Review** for the `instagram_content_publish` permission —
     this is a multi-day human review where Meta inspects your use case
     and may request a screencast demo. Approval is granted per-app.
   - Once approved, the API endpoints are simple:
     - `POST /{ig-user-id}/media` — upload media + caption (creates a container)
     - `POST /{ig-user-id}/media_publish` — publish the container
   - One image post = one container + one publish = two API calls
   - Posting limit: 100 IG posts per 24h per account (way more than we need)

   **Reels / Stories** require video assets (≥3 sec, vertical
   1080×1920) which the daily brief doesn't currently produce. Static
   feed posts are the only viable autonomous format unless we build
   a video pipeline.

   **Net assessment:** worth the App Review process IF Instagram is a
   significant target audience (likely younger readers). The brand's
   serious-news posture fits IG less naturally than X or Bluesky —
   but a daily 1200×1200 card with the lede + a hashtag set could
   work. Estimate: 1-2 weeks from start to first autonomous post,
   most of which is App Review wait time.

   **Suggested path:** start with manual Instagram posting + draft
   generation; if engagement justifies, then go through App Review
   for autonomous.

### X account naming
Currently posting to operator's personal `@SamadhiMaximus`. Could set
up dedicated `@briefernews` (or similar). Trade-off:
- Personal account: existing audience + activity, but mixes Briefer
  News content with operator's personal posts
- Dedicated account: clean brand presence, but starts from 0 followers

Discuss with operator before doing either; the X tokens currently
authenticate as `@SamadhiMaximus`.

### Engagement-data backfill
Posts go out but we don't collect engagement metrics yet. Build:
- `scripts/x_engagement_collector.py` — 6h + 24h after each post, fetch
  likes/reposts/replies, append to `logs/posts-YYYY-MM-DD.jsonl`
- Same for Bluesky once enabled
- Analyzer reads these for the weekly retro

### Manual-post logger
`scripts/log_post.py` — operator runs one liner after posting manually:
```bash
python3 scripts/log_post.py --channel hn --url "https://news.ycombinator.com/item?id=XXX"
```
Records to `logs/posts-YYYY-MM-DD.jsonl` so the analyzer sees manual
channels.

### Allied sourcing repair (NOT YOUR JOB, just FYI)
The brief's Allied Governments section is currently thin because
several scrapers are stale (Aus DFAT 26d, Japan MoFA 0 articles).
The dev Claude will fix this. If you see a thin Allied section in
the brief, that's why — not a marketing problem.

---

## Brand constraints (HARD RULES — DO NOT BREAK)

1. **Government sources only** in the brief itself. If you want to
   reference an outside source IN A SOCIAL POST, that's fine. But
   never edit the brief to cite a non-gov source.
2. **No editorialization** in any post. The brief is "no commentary;"
   distribution posts inherit that posture. Translate facts cleanly;
   don't add takes or framing.
3. **No clickbait.** "You won't believe what Xi said today" → no.
   "Xi awards Serbia's president the Friendship Medal" → yes.
4. **No fake accounts, no engagement farming, no bought followers,
   no follower-for-follower swaps.** The brand is built on credibility;
   anything that compromises that is forbidden.
5. **No discovery via Google News** — the brief's brand promise is
   primary government sourcing. A growth post citing Google News
   undermines the brand. If a growth post cites a non-gov source, it
   must be acknowledging external context — not as the brief's
   source.
6. **Use globally-recognized names only** when posting (Xi, Trump,
   Putin, Modi, Netanyahu). For lesser-known officials (Jaishankar,
   Vučić, Sharif, Lai), use country/institution instead. Same rule
   the brief uses internally — see `DEK.md`.
7. **No acronyms in distribution copy** unless universally understood
   (UN, NATO, G7, OK to use). Acronym-heavy copy = lower engagement +
   feels insider-y.

---

## Available credentials + APIs

All credentials live in `~/code/briefernewsapp/.env` (gitignored).

| Service | Key prefix | Notes |
|---|---|---|
| Cloudflare | `CLOUDFLARE_API_TOKEN` (cfat_…) + `CLOUDFLARE_DNS_EDIT_TOKEN` (cfut_…) + `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_ZONE_ID_BRIEFER` | Full-access (Analytics + DNS + Tunnels) — but DNS scope on the cfat_ token is glitchy; use cfut_ for DNS-only ops |
| AWS | `aws` (default profile) + `aws --profile registrar` | SES, S3, CloudFront, SNS, SQS in 462170975634; domain registrar in separate account |
| X / Twitter | `X_API_KEY` + `X_API_SECRET` + `X_ACCESS_TOKEN` + `X_ACCESS_TOKEN_SECRET` + `X_BEARER_TOKEN` | $25 credit on Basic tier; OAuth 1.0a User Context |
| Bluesky | `BLUESKY_HANDLE` + `BLUESKY_APP_PASSWORD` (empty) | Operator needs to generate at bsky.app/settings/app-passwords |
| Search Console | gcloud ADC | `gcloud auth application-default print-access-token` |
| AWS Cost Explorer | `aws ce get-cost-and-usage` | Read-only |

For services NOT in `.env` (e.g., Instagram, LinkedIn, Reddit), you'll
need to ask the operator to set them up. Instagram needs Meta App
Review (multi-day human flow); LinkedIn and Reddit have similar
multi-step OAuth flows.

---

## First 15 minutes in a fresh session

If you're a new Claude waking up to this project, do this in order:

1. **Read this whole file** (you just did)
2. **Skim `GROWTH.md`** — the full design doc for the autonomous loop
3. **Check today's brief**: `curl -s https://briefer.news/usa/ | head -200`
4. **Check today's research log**: `cat ~/code/briefernewsapp/research/loop/$(date +%Y-%m-%d)-morning.md`
5. **Check today's drafts**: `cat ~/code/briefernewsapp/logs/drafts-$(date +%Y-%m-%d).md`
6. **Check the latest analysis**: `ls -t ~/code/briefernewsapp/logs/analysis-*.md | head -1 | xargs cat`
7. **Check what's in last 7 days' posts log**: `cat ~/code/briefernewsapp/logs/posts-*.jsonl 2>/dev/null | tail -20`
8. **Run an X auth check** to confirm credentials are live:
   `cd ~/code/briefernewsapp && python3 scripts/x_post.py --check`
9. **Ask the operator what they want to focus on** — small
   experiments? Instagram setup? Engagement-data backfill? Allied
   sourcing recovery? Or just monitor the loop?

---

## What success looks like

In ranked priority:

1. **Real human page-loads grow** — Cloudflare RUM page-loads (humans
   only) per day. Baseline 2026-05-27: 1 page-load/week. Target: 10x
   by end of June; 100x by end of summer.
2. **Search Console clicks > 0/week** — first organic search clicks
   from outside the brand-name "briefer" query (currently 0% CTR on
   78 weekly impressions).
3. **Confirmed email subscribers > 1** — currently 1 (the operator).
   Target: 25 by end of June; 250 by end of summer. Growth comes
   from social posts + organic search.
4. **Repeat readers** — Cloudflare RUM session counts where the same
   IP returns. Hard to measure cleanly with cookieless analytics;
   secondary signal: archive page-loads.

What is NOT a success metric:
- Follower counts on X/Bluesky/IG (vanity)
- Total tweets/posts published (output, not outcome)
- Engagement on individual posts unless it correlates with site traffic

---

## Memory notes (cross-session context)

Recent operator-noted state for cross-session continuity:

- `project_sourcing_gaps.md` (in Claude memory) — allied scraper
  failures (Aus DFAT, Japan MoFA); health/tech sources just added
  but first scrape lands tomorrow 04:00 PT
- `project_marketing_credits.md` — $25 X credits; Instagram under
  consideration
- `feedback_no_deferral.md` — don't suggest stopping/waiting; surface
  next directions concretely

These memory files persist across Claude sessions — read them at the
start of each session via the global CLAUDE.md flow.
