# Browser-UA Re-probe of Blocked Sources — 2026-05-05

> Re-probe of the 35 HTTP 403 candidates from `candidates_probe_2026-05-05.md`
> using browser-like headers (Chrome 121 / Win11 + full Accept + Sec-Fetch).
> Goal: unlock sources that were rejected for User-Agent fingerprint reasons.
>
> Raw: `blocked_probe_2026-05-05.json`. Script: `probe_blocked.py`.

## Headline

**0 fresh unlocks.** Browser headers got past the WAF on most sites but revealed that 28 of the 35 "blocked" URLs were never RSS feeds in the first place — they were HTML pages or non-existent paths. The HTTP 403 was the WAF rejecting our default User-Agent before serving the content; with browser UA we get the *truthful* response, which mostly turns out to be 404 or HTML.

| Outcome | Count | What it means |
|---|---|---|
| parse_error (HTML) | 10 | URL exists, returns 200 OK with browser UA, but content is HTML not RSS |
| HTTP 404 | 18 | URL doesn't exist — pattern guess was wrong |
| HTTP 403 (still) | 6 | Stronger bot protection — Cloudflare-class |
| NET (DNS fail) | 1 | DTRA — host doesn't resolve |

## The 10 "soft unlocks" — URL exists but isn't RSS

These pages return real content with browser UA, but it's HTML, not RSS. The agency may have RSS at a different URL.

- **war.gov family**: DoD Contracts, DoD Transcripts — RSS exists somewhere on war.gov (we successfully use `defense.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1...`) but not at `/News/Releases/feed`
- **Military .mil branches**: Navy News index, Marine Corps News index, Air Force News index, Space Force News index, Space Systems Command — these are RSS *index* pages listing the actual feed URLs. Each branch likely has 1-5 real feeds we'd need to discover.
- **DOT family**: USCG News, FMCSA Motor Carrier, NHTSA Vehicle Recalls

## The 18 confirmed 404s

URLs that simply don't exist. Our pattern matching missed.

DoD Releases, Army News, FAA News, NHTSA Press, FRA, FTA, MARAD, PHMSA, DOT Newsroom, USDA FAS, USDA FSIS Recalls, ATF Press, DEA Press, USMS News, NRO Press, DIA News, HRSA News, SSA Press Releases, DCSA Counterintelligence

The real RSS for some of these *does* exist — just not at the URL we guessed. Each would need a manual research pass.

## The 6 still-blocked sources

These reject browser UA too — likely Cloudflare-tier bot protection. To probe these we'd need Playwright + stealth headers, or cloudscraper.

| Source | Notes |
|---|---|
| ORNL — Oak Ridge | DOE lab; DOE labs commonly behind Cloudflare |
| ANL — Argonne | DOE lab |
| INL — Idaho | DOE lab |
| PNNL — Pacific Northwest | DOE lab |
| AMES — Ames | DOE lab |
| FEMA — Press Releases | FEMA Disaster Declarations feed worked unauthed; this one didn't |

## The 1 NET fail

DTRA (Defense Threat Reduction Agency) — `dtra.mil/News/feed` returns DNS getaddrinfo failed. The hostname or path doesn't resolve at all.

## What this tells us

1. **Pattern-derived URL guessing has a low ceiling.** The agent's catalog gave us ~159 candidates; only ~12% were immediately usable, and the browser-UA retry yielded zero additional new RSS feeds.
2. **WAF 403s are often masking 404s.** When a default scraper UA hits a federal site, the WAF returns 403 *before* checking if the path exists. That hides real signal — we thought 35 sources were "blocked but maybe recoverable" when in fact 18 of them have no feed at that path at all.
3. **DOE national labs have meaningfully tougher bot protection** than other federal sites. ORNL, ANL, INL, PNNL, AMES all blocked even with full browser headers. This isn't surprising — these are research orgs holding sensitive data.
4. **To actually get DoD/military/DOT RSS, the path forward is manual discovery** — visit each agency's actual "RSS Feeds" page (most have one), copy the real feed URLs, add to yaml. There's no shortcut.

## Recommended actions

- **Drop from consideration entirely**: the 18 confirmed-404 URLs and DTRA. They were guesses and they're wrong.
- **Manual research pass** (separate task, not today): visit `navy.mil/Resources/Rss-Feeds/`, `af.mil/News/RSS/`, `marines.mil/RSS/`, `spaceforce.mil/News/`, `war.gov/News/RSS/`, find the actual feed URLs by reading the index page. Same for USCG `news.uscg.mil/RSS/`.
- **DOE labs**: try Playwright with stealth + delays as a Phase B research task. Lower priority — LBNL, FNAL, SNL already work, so we have lab coverage.
- **No yaml changes from this probe.** No sources to add.

## Probe yield summary across both probes

| Probe | Candidates | Fresh adds | Held adds |
|---|---|---|---|
| 2026-05-02 sources.yaml refresh | 94 (existing) | 24 (already in config, flipped to active) | — |
| 2026-05-05 catalog probe | 159 (new) | 14 (added active) | ~24 (added held) |
| 2026-05-05 blocked re-probe | 35 (retry) | **0** | 0 |
| **Total now in sources.yaml** | | **39 active** | **87 inactive** |
