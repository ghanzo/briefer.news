# Briefer — Source Status & Reliability

Last updated: 2026-05-05 (US-gov catalog + candidate probe — see `research/candidates_probe_2026-05-05.md`)
Previously updated: 2026-05-02 (initial live probe — see `research/probe_2026-05-02.md`)

## How this file works

Every source the pipeline can use is listed here with its **status**:
- **ACTIVE** — currently enabled in `pipeline/config/sources.yaml`, confirmed fresh
- **HELD** — tested and working, deliberately disabled this round
- **BLOCKED** — needs Playwright or other capability not in default scrape path
- **BROKEN** — feed exists but does not return usable content
- **REMOVED** — feed dead or duplicate; no entry in sources.yaml

Sources are defined in `pipeline/config/sources.yaml`. To enable a held source,
remove its `active: false` line.

---

## Active Sources (44)

25 confirmed fresh on 2026-05-02 + 14 added 2026-05-05 from the US-gov catalog probe + 5 HTML-scrape (White House, DOJ Antitrust, DOE Newsroom, ARPA-E, ORNL) added 2026-05-05.

### Mainstream news (5)

| Source | Type | Tier | Notes |
|---|---|---|---|
| BBC — World | rss | 2 | 39 entries / 39 fresh on probe day |
| Al Jazeera — World | rss | 2 | 25/25 fresh |
| Deutsche Welle — World | rss | 2 | 13/13 fresh |
| Yonhap — English | rss | 2 | 95/95 fresh |
| AllAfrica — Top Stories | rss | 2 | 30/30 fresh |

### US Federal — gov & regulators (15)

| Source | Type | Tier | Notes |
|---|---|---|---|
| State Dept — Press Releases | rss | 1 | Full text in `content:encoded` (bypass URL fetch) |
| State Dept — Collected Department Releases | rss | 1 | 10/10 fresh |
| Department of Defense — News | rss | 1 | 20 entries, ~12 fresh |
| Federal Reserve — Press Releases | rss | 1 | Low cadence; 2/20 fresh |
| U.S. Treasury — Press Releases | rss | 1 | Federal Register-routed |
| USTR — Press Releases | rss | 1 | 10/10 fresh — strong source |
| GAO — Reports & Testimonies | rss | 1 | 25 entries, 7 fresh |
| DOJ — National Security Division | rss | 1 | Federal Register-routed; 9 fresh |
| CISA — Alerts & Advisories | rss | 1 | 30/10 fresh — security signal |
| Federal Register — Executive Orders & Rules | rss | 1 | 200 entries, 49 fresh |
| **Federal Register — Public Inspection** | rss | 1 | NEW 2026-05-05. 200/200 fresh — next-day rules firehose |
| **CBP — News** | rss | 1 | NEW 2026-05-05. Trade enforcement, UFLPA, border |
| **DOJ — Justice News (OPA)** | rss | 1 | NEW 2026-05-05. 25/9 fresh — full DOJ press feed |
| **FBI — National Press** | rss | 1 | NEW 2026-05-05. 300 entries; espionage/sanctions arrests |
| **CFPB — Newsroom** | rss | 1 | NEW 2026-05-05. Financial-services regulation |

### US Federal — Macroeconomic data (4)

| Source | Type | Tier | Notes |
|---|---|---|---|
| **BLS — Major Economic Indicators** | rss | 1 | NEW 2026-05-05. CPI/PPI/jobs ground truth |
| **BEA — Releases** | rss | 1 | NEW 2026-05-05. 45 entries — GDP, trade, PCE |
| **CBO — Publications** | rss | 1 | NEW 2026-05-05. 30/2 fresh — fiscal scoring |
| **NY Fed — Liberty Street Economics** | rss | 1 | NEW 2026-05-05. 100 entries — top macro research |

### US Federal — Legislative & GovInfo (3)

| Source | Type | Tier | Notes |
|---|---|---|---|
| **GovInfo — Bills** | rss | 1 | NEW 2026-05-05. 100/56 fresh — daily Congressional bills |
| **GovInfo — Hearings** | rss | 1 | NEW 2026-05-05. 100/16 fresh |
| **GovInfo — Presidential Documents** | rss | 1 | NEW 2026-05-05. 100/12 fresh |

### US Federal — Judicial (2)

| Source | Type | Tier | Notes |
|---|---|---|---|
| **Court of Appeals — 9th Circuit** | rss | 1 | NEW 2026-05-05. 100/3 fresh — regulatory rulings |
| **Court of International Trade** | rss | 1 | NEW 2026-05-05. Tariff & trade rulings — high signal |

### International gov (3) — native-language preferred

| Source | Type | Tier | Notes |
|---|---|---|---|
| UK Government — Foreign Policy | rss | 1 | 20/20 fresh — atom feed |
| Kremlin — Russian (native) | rss_translate | 1 | Russian native; English version lags |
| TASS — Russian wire (native) | rss_translate | 2 | 100/100 fresh; English wire was 100/0 fresh |

### International institutions (3)

| Source | Type | Tier | Notes |
|---|---|---|---|
| UN — News | rss | 2 | 30 entries / 20 fresh |
| WHO — News | rss | 2 | 25 entries / 2 fresh |
| IAEA — News | rss | 2 | 15 entries / 2 fresh |

### Energy & resources (3)

| Source | Type | Tier | Notes |
|---|---|---|---|
| EIA — Today in Energy | rss | 2 | US energy data |
| OilPrice.com — News | rss | 2 | 15/15 fresh — strong daily flow |
| Mining.com — Critical Minerals | rss | 2 | 36 entries / 26 fresh — added Mar 2026 |

### Innovation signals (1)

| Source | Type | Tier | Notes |
|---|---|---|---|
| Hacker News — Best Stories | rss | 3 | 30/30 fresh |

---

## Held — known-working but disabled this round

These all parsed successfully on 2026-05-02 and are valid candidates for
future expansion. Held back to keep the active set lean.

### Additional State Dept regional desks (10)

`Secretary's Remarks`, `Department Press Briefings`, `East Asia & the Pacific`,
`Near East`, `Europe & Eurasia`, `South & Central Asia`, `Western Hemisphere`,
`Africa`, `Travel Advisories`, `Public Schedule`. All fresh or recent on probe.

### Additional US gov / regulators (~20)

`DARPA`, `OFAC`, `FTC PR`, `FTC Fed Reg`, `BIS`, `SEC`, `CFTC`, `FDIC`, `OCC`,
`FCC`, `NRC`, `FERC`, `Fed Speeches`, `NASA`, `NOAA`, `EPA`, `FDA`, `HHS`,
`USGS`, `NSF`, `NIST`, `Commerce`. Most fresh on probe; some (BIS, NIST, NSF,
FTC Fed Reg) were stale because the agency simply hadn't posted in 72h.

### Other international (12)

`Bank of England`, `Kremlin English`, `TASS English`, `Global Times`,
`African Union`, `South Africa Gov`, `Iran IRNA English`, `ASEAN`,
`Agência Brasil`, `BBC Tech`, `BBC Science`, `Anadolu`, `Times of India`.
The Kremlin English and TASS English entries are kept for reference but
the native-language versions are now the primary — Russian feeds were 100%
fresh while their English wires were 100% stale on the probe day.

### arXiv

`arXiv — Artificial Intelligence` works (322 entries/day). `arXiv — Machine
Learning` returns 0 entries despite identical URL pattern — needs URL-variant
research before enabling.

### Added 2026-05-05 from US-gov catalog probe (~24)

All confirmed working in `candidates_probe_2026-05-05.md`. Held off the active
set to keep daily volume manageable.

**BLS data series** (post monthly; high-signal when fresh): `BLS — Employment
Situation`, `BLS — CPI`, `BLS — PPI`

**FBI parallel feed**: `FBI — Top Stories` (sibling of National Press, partial overlap)

**DOE labs** (working RSS, mid-cadence): `LBNL — Lawrence Berkeley`, `FNAL —
Fermilab`, `SNL — Sandia`. Six other labs (ORNL, ANL, INL, PNNL, AMES, etc.)
returned 403 — see browser-UA probe results.

**US Federal additional**: `DOL — News Releases`, `VA — Press Room`, `FEMA —
Disaster Declarations`, `CMS — Internet-Only Manuals`

**GovInfo additional**: `Public Laws`, `Reports`, `Federal Register (firehose)`,
`Congressional Record`, `Bills Enrolled`, `Economic Indicators`

**Court of Appeals additional circuits**: `DC Circuit`, `5th Circuit`,
`2nd Circuit`, `Court of Federal Claims`

**Labor**: `NLRB — Press Releases`, `NLRB — Weekly Summaries`

**NY Fed**: `Economic Policy Review` (quarterly research)

---

## HTML-scrape sources (web_scrape via Playwright)

For per-source operational details, debug history, and quirks see **`SOURCE_NOTES.md`**.

### Active (5)

| Source | URL | Notes |
|---|---|---|
| **White House — News** | whitehouse.gov/news/ | ACTIVE 2026-05-05. Hub URL covering briefings-statements + releases + presidential-actions + research. `link_pattern: /202` matches date-prefixed article paths. Test: 11 stubs / 3 of 3 extractions / avg 18.7k chars. See SOURCE_NOTES.md. |
| **DOJ — Antitrust Press Room** | justice.gov/atr/press-room-0 | ACTIVE 2026-05-05. ATR press releases + speeches + videos. `link_pattern: /opa/` filters to article paths. Test: 11 stubs / 3 of 3 extractions / avg 2.2k chars. See SOURCE_NOTES.md. |
| **DOE — Newsroom** | energy.gov/newsroom | ACTIVE 2026-05-05. Main DOE + sub-office articles. `link_pattern: /articles/`. Test: 16 stubs / 3 of 3 / avg 5.3k chars. SPR RFP, LNG agreements, Venezuelan engagement, FERC grid reform. See SOURCE_NOTES.md. |
| **ARPA-E — News & Insights** | arpa-e.energy.gov/news-and-events/news-and-insights | ACTIVE 2026-05-05. Energy R&D funding announcements. `link_pattern: /news-and-insights/`. Test: 15 stubs / 3 of 3 / avg 3.2k chars. $135M fusion, $60M critical minerals, $50M advanced reactor fuels. See SOURCE_NOTES.md. |
| **ORNL — Oak Ridge News** | ornl.gov/news | ACTIVE 2026-05-05. National lab research announcements. `link_pattern: /news/`. Test: 17 stubs (~11 articles + 6 sub-section landing pages) / 3 of 3 / avg 3.3k chars. Fusion, quantum materials, nuclear, grid, AI security. See SOURCE_NOTES.md. |

### Held — needs Playwright probe

| Source | URL | Notes |
|---|---|---|
| Department of Energy — Newsroom | energy.gov/newsroom | P1 energy source — not yet tested |
| ARPA-E — News & Insights | arpa-e.energy.gov/news-and-media/press-releases | P2 — not yet tested |

---

## Broken (held in yaml but flagged)

| Source | Issue | Detected | Fix path |
|---|---|---|---|
| NTIA — News | SSL `CERTIFICATE_VERIFY_FAILED` | 2026-05-02 | Cert chain issue at ntia.gov; needs `verify=False` for that domain or updated CA bundle |
| GitHub Trending — Daily | Returns 9 entries with no published/updated dates | 2026-05-02 | Either accept as "always fresh" in discovery.py, or wrap with fetch-time fallback |
| NIH — News Releases | Returns 10 entries with no dates | 2026-05-02 | Same pattern as GitHub Trending |
| arXiv — Machine Learning | Returns 0 entries (`rss.arxiv.org/rss/cs.LG`) | 2026-05-02 | Try alternate URL; sibling cs.AI feed at same path returns 322 entries |
| CDC — Newsroom | Returns 1799-entry archive but no entry within 72h | 2026-05-02 | URL `tools.cdc.gov/api/v2/resources/media/132608.rss` may be all-time archive; find current newsroom feed |
| Global Times — World | 50 entries, all stale | persistent | English edition lags behind Chinese edition; consider Mandarin scrape |

---

## Removed (2026-05-02)

Dropped from `sources.yaml` entirely. See bottom of yaml for the audit list.

| Source | Why |
|---|---|
| Reuters — World News | DNS `getaddrinfo failed` — Reuters killed public RSS in 2023 |
| Associated Press — Top News | HTTP 404 — AP killed public RSS |
| NHK World — Top Stories | Connection hangs >20s; documented in Feb probe and confirmed in May probe |
| Google News — World (topic-ID URL) | HTTP 400 — `topics/CAAqJg…` format deprecated. Sibling `search?q=` variants still work and remain in yaml (held). |
| White House — Articles | Duplicate URL of Presidential Actions |
| White House — Fact Sheets | Duplicate URL of Presidential Actions |

---

## Google News — Why It Doesn't Work

Google News RSS feeds return article stubs with Google redirect URLs (e.g.,
`news.google.com/rss/articles/...`). To get the actual article URL:
1. Must follow redirect (HEAD request) — slow, ~1-2s per article
2. Many redirects fail or return consent pages
3. Even when URL resolves, trafilatura can't extract text (paywalls, JS-rendered
   pages, anti-bot measures)

**To fix:** Would need a dedicated scraper module that:
- Resolves Google News URLs via their `consent.google.com` redirect chain
- Uses headless browser (Playwright) for JS-heavy target sites
- Has per-site extraction rules for major outlets (NYT, WaPo, etc.)

This is a separate project-level effort, not a config change. The 9
Google-News topic feeds remain in `sources.yaml` as `active: false`.

---

## Scaling Guide

For **current production** (25 active sources):
- Expected ~150-300 articles/day raw
- Stage 2 capped at 30 articles → ~30 summarized/day
- Cost estimate: ~$0.01-0.05 per run depending on provider

For **expanded coverage** (enable 30-40 of the held set):
- Expected ~400-800 articles/day raw
- Groq Stage 1 filter becomes more important (free tier handles 1000/day)
- Stage 2 still capped at 30 — same cost ceiling
- Tradeoff: more breadth, requires tighter filter prompt

For **full coverage** (Reuters/AP/NYT-class outlets):
- Would need Google News redirect handler + Playwright extraction + per-site rules
- Out of scope for current pipeline.
