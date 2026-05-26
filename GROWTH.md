# GROWTH.md — Researcher / Drafter / Analyzer loop

> **Status: in progress.** Foundation shipping 2026-05-26. Bluesky
> autonomous-posting wires up once user provides `BLUESKY_APP_PASSWORD`.
> X / Twitter wires up once user purchases API credits.

The growth loop is three autonomous agents that run on the same Mac mini
that does the daily scrape + synth, and use the same headless Claude
(Max plan — $0 token cost). They:

1. **Research** what's driving traffic + what channels work for the brand.
2. **Draft** posts for every channel and **auto-post** wherever the
   platform allows it without a human in the loop.
3. **Analyze** weekly: what got engagement, what didn't, what to try next.

The user's explicit direction: prefer channels that can be posted
autonomously (no human paste-in). Manual channels (HN, Reddit) get drafts
written to a file for one-click copy-paste — better than nothing, but
not the goal.

---

## Cadence

| Agent | Trigger | Mechanism |
|---|---|---|
| Researcher | 09:00 PT + 18:00 PT daily | LaunchAgent |
| Drafter    | 09:30 PT daily            | LaunchAgent (after Researcher AM) |
| Analyzer   | 10:00 PT Sunday weekly    | LaunchAgent |

Drafter runs 30 min after Researcher so it sees fresh research. Analyzer
on Sunday looks at the previous week of drafts + posts + traffic.

---

## Channels

| Channel | Autonomy | Driver | Format |
|---|---|---|---|
| Email digest | full | existing daily-send pipeline | HTML email at 08:30 PT |
| RSS | full | existing build_feeds.py | feed.xml per edition |
| Bluesky | full | `bluesky_post.py` — atproto API + app password | post (300-char limit) |
| X / Twitter | full *(once tokens land)* | TBD — X API v2 OAuth 2.0 | tweet (280-char limit) |
| Mastodon | full *(opt-in)* | TBD — fediverse API | toot (500-char default) |
| HN | manual | drafter writes to file | one-line title + URL |
| Reddit | manual | drafter writes to file | title + body |
| LinkedIn | manual | drafter writes to file | long-form post |
| Threads | manual | drafter writes to file | post |

Manual channels get drafts in `logs/drafts-YYYY-MM-DD.md`.

---

## File layout

```
briefernewsapp/
├── scripts/
│   ├── researcher.py        # daily research → research/loop/YYYY-MM-DD.md
│   ├── drafter.py           # daily drafts → logs/drafts-YYYY-MM-DD.md
│   ├── analyzer.py          # weekly retro → logs/analysis-YYYY-MM-DD.md
│   ├── bluesky_post.py      # atproto post client (importable + CLI)
│   └── log_post.py          # operator helper: log a manual post we did
├── research/loop/            # researcher output
│   └── YYYY-MM-DD.md
├── logs/
│   ├── drafts-YYYY-MM-DD.md   # drafter output
│   ├── posts-YYYY-MM-DD.jsonl # one line per autonomous post (channel, id, ts)
│   └── analysis-YYYY-MM-DD.md # analyzer output (Sundays)
└── launchd/
    ├── news.briefer.researcher.plist
    ├── news.briefer.drafter.plist
    └── news.briefer.analyzer.plist
```

---

## Environment (.env additions)

```
# Bluesky
BLUESKY_HANDLE=briefernews.bsky.social         # or custom domain handle
BLUESKY_APP_PASSWORD=<get from bsky.app/settings/app-passwords>
BLUESKY_ENABLED=false                          # flip true once creds set

# X / Twitter (pending — user is working on X tokens)
X_API_KEY=
X_API_SECRET=
X_BEARER_TOKEN=
X_ACCESS_TOKEN=
X_ACCESS_TOKEN_SECRET=
X_ENABLED=false

# Drafter
DRAFTER_DRY_RUN=false                          # if true, draft but don't post
```

The drafter checks each `*_ENABLED` flag — if false, writes that
channel's content to the draft file instead of posting.

---

## Researcher contract

The Researcher's job is to feed the Drafter useful context. Each run
produces a markdown file in `research/loop/YYYY-MM-DD-{morning|evening}.md`
with the following structure:

```
# Research log — 2026-05-26 morning

## Traffic snapshot (last 7d)
- Top pages: …
- Top referrers: …
- Search Console: top queries, position changes
- Cloudflare Analytics: unique visitors, page views

## What worked
- (Things that drove measurable upticks)

## What stalled
- (Channels or formats that didn't move the needle)

## Today's hooks
- (3-5 angles in today's brief most likely to land per channel)

## Channel ideas
- (New posting cadences, audiences, formats to test)
```

The Drafter reads this verbatim as context.

---

## Drafter contract

The Drafter renders a post per channel. Per-channel character limits
and tone are baked into its prompt. It outputs to a single file per day:

```
# Drafts — 2026-05-26

## Bluesky [POSTED at_uri://… 09:31:14 PT]
<300-char post>

## X / Twitter [PENDING — X_ENABLED=false]
<280-char post>

## HN (manual paste)
Title: <title>
URL: https://briefer.news/usa/

## Reddit r/geopolitics (manual paste)
Title: <title>
Body: <body>

## LinkedIn (manual paste)
<long-form post>
```

Posted-channel header gets a `[POSTED ...]` marker once the API call
returns success. The `logs/posts-YYYY-MM-DD.jsonl` is the authoritative
log of every autonomous send for the Analyzer.

---

## Analyzer contract

Weekly Sunday 10:00 PT. Reads:
- The past 7 days of `logs/drafts-*.md`
- The past 7 days of `logs/posts-*.jsonl`
- Traffic delta week-over-week (via `traffic_report.py`)
- Search Console position changes (via `search_report.py`)
- Bluesky engagement (likes / reposts / replies) per post

Writes `logs/analysis-YYYY-MM-DD.md`:

```
# Weekly analysis — week ending 2026-05-31

## Traffic
- WoW unique visitors: …
- Top growth source: …

## Posted this week
- Bluesky: N posts, M engagement
- X: N posts, M engagement

## Hits
- (Specific posts that outperformed)

## Misses
- (Specific posts that underperformed)

## Next week
- (3-4 concrete experiments to run)
```

The Analyzer's output feeds back into next week's Researcher prompt
(prior-week findings are loaded as context).

---

## Cost

- Claude tokens: $0 — all agents run via Claude Max plan headless.
- Bluesky: $0 — free API, app password.
- X: ~$100/mo (X API v2 Basic tier) once user opts in.
- AWS infra: covered by existing budget.

Total ongoing: $0 today, ~$100/mo if X turns on.

---

## What I should NOT do

- **No black-hat tactics** — no fake accounts, no engagement farming, no
  comment spam, no buying followers. The brand promise is "primary
  government sources only." Same standard applies to growth: only
  channels and tactics that survive scrutiny.
- **No mutating site code from growth agents.** The Researcher/Drafter/
  Analyzer never touch `pipeline/` or `scripts/synthesize*.sh` or the
  prototypes. If a growth idea requires a site change, the Analyzer
  flags it as a next-week task for human review — doesn't ship it.
- **No "schedule a bunch of posts" backlog.** Same-day only. The brief
  is the day's news; posts about the brief should ship the day of.
- **No discovering via Google News.** Brand-promise constraint: all
  sourcing from government. Same applies to growth content — if a post
  cites a non-gov source, it should be the BRIEF citing it (not the
  growth agent fabricating it).
