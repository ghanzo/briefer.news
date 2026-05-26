# Candidate Source Probe — 2026-05-05

> Live probe of 159 candidate US-gov RSS URLs from `us_gov_feeds_catalog_2026-05-05.md`.
> Methodology: same as `probe_2026-05-02.md` — httpx fetch (20s timeout) + feedparser.
> Raw: `candidates_probe_2026-05-05.json`. Script: `probe_candidates.py`.

## Headline result

| Status | Count | What it means |
|---|---|---|
| **fresh** | **19** | Working RSS, ≥1 entry within 72h — usable today |
| stale | 25 | Working RSS, no entries within 72h (cadence-dependent) |
| http_404 | 51 | URL doesn't exist — bad pattern guess |
| http_403 | 35 | Site blocks our User-Agent — potentially recoverable with browser headers |
| parse_error | 24 | Returned 200 OK but HTML, not RSS |
| http_503 | 1 | Service unavailable |
| http_406 | 1 | Not acceptable |
| empty | 2 | Valid RSS with 0 entries |
| timeout | 1 | Hung past 20s |

**Net yield: 44/159 (28%) returned a parseable RSS feed.** Only 19 (12%) were
immediately fresh. The catalog's `(unverified)` URLs were largely pattern guesses;
the agent's "expect 15-25% attrition" estimate was significantly optimistic.

---

## FRESH (19) — all confirmed today/yesterday

| # | Source | Flag | Entries / Fresh | URL |
|---|---|---|---|---|
| 1 | **GovInfo — Bills** | 🔴 | 100 / 56 | `https://www.govinfo.gov/rss/bills.xml` |
| 2 | **Federal Register — Public Inspection** | 🔴 | 200 / 200 | `https://www.federalregister.gov/api/v1/public-inspection-documents.rss` |
| 3 | **BLS — Major Economic Indicators** | 🔴 | 1 / 1 | `https://www.bls.gov/feed/bls_latest.rss` |
| 4 | **BEA — Releases** | 🔴 | 45 / 1 | `https://apps.bea.gov/rss/rss.xml` |
| 5 | **CBO — Publications** | 🔴 | 30 / 2 | `https://www.cbo.gov/publications/all/rss.xml` |
| 6 | **NY Fed — Liberty Street Economics** | 🔴 | 100 / 1 | `https://libertystreeteconomics.newyorkfed.org/feed/` |
| 7 | **CBP — News** | 🔴 | 10 / 1 | `https://www.cbp.gov/rss.xml` |
| 8 | **GovInfo — Court of Appeals 9th** | 🔴 | 100 / 3 | `https://www.govinfo.gov/rss/uscourts-ca9.xml` |
| 9 | **GovInfo — Court of Appeals 5th** | 🟡 | 100 / 15 | `https://www.govinfo.gov/rss/uscourts-ca5.xml` |
| 10 | **GovInfo — Court of Federal Claims** | 🟡 | 100 / 19 | `https://www.govinfo.gov/rss/uscourts-cofc.xml` |
| 11 | **GovInfo — Federal Register** | 🟡 | 99 / 3 | `https://www.govinfo.gov/rss/fr.xml` |
| 12 | **GovInfo — Hearings** | 🟡 | 100 / 16 | `https://www.govinfo.gov/rss/chrg.xml` |
| 13 | **GovInfo — Congressional Record** | 🟡 | 100 / 12 | `https://www.govinfo.gov/rss/crec.xml` |
| 14 | **GovInfo — Presidential Documents** | 🟡 | 100 / 12 | `https://www.govinfo.gov/rss/dcpd.xml` |
| 15 | **GovInfo — Public Laws** | 🟡 | 99 / 1 | `https://www.govinfo.gov/rss/plaw.xml` |
| 16 | **GovInfo — Reports** | 🟡 | 100 / 1 | `https://www.govinfo.gov/rss/crpt.xml` |
| 17 | **DOJ — Justice News (OPA)** | 🟡 | 25 / 9 | `https://www.justice.gov/news/rss?m=1` |
| 18 | **DOL — News Releases** | 🟡 | 10 / 5 | `https://www.dol.gov/rss/releases.xml` |
| 19 | **VA — Press Room** | ⚪ | 30 / 7 | `https://news.va.gov/feed/` |

---

## STALE (25) — feed parses, no entry in last 72h (cadence-normal)

These are real RSS feeds; they just hadn't published in the 72-hour window. Many
post on monthly cadence (BLS data series), or post sporadically (FBI, NLRB).
All worth enabling — they'll produce content when the agency publishes.

| Source | Entries | Newest ago | URL |
|---|---|---|---|
| BLS — Employment Situation | 12 | 4 days | `https://www.bls.gov/feed/empsit.rss` |
| BLS — CPI | 12 | ~weeks | `https://www.bls.gov/feed/cpi.rss` |
| BLS — PPI | 12 | ~weeks | `https://www.bls.gov/feed/ppi.rss` |
| FBI — National Press | 300 | 4 days | `https://www.fbi.gov/feeds/national-press-releases/RSS` |
| FBI — Top Stories | 300 | 4 days | `https://www.fbi.gov/feeds/fbi-top-stories/RSS` |
| FEMA — Disaster Declarations | 10 | varies | `https://www.fema.gov/news/disasters_rss.fema` |
| CFPB — Newsroom | 25 | recent | `https://www.consumerfinance.gov/about-us/newsroom/feed/` |
| CMS — Internet-Only Manuals | 25 | recent | `https://www.cms.gov/rss/31836` |
| LBNL — Lawrence Berkeley | 12 | recent | `https://newscenter.lbl.gov/feed/` |
| FNAL — Fermilab | 10 | recent | `https://news.fnal.gov/feed/` |
| SNL — Sandia | 10 | recent | `https://newsreleases.sandia.gov/feed/` |
| NY Fed — EPR | 1 | quarterly | `https://www.newyorkfed.org/medialibrary/media/research/rss/feeds/epr.xml` |
| San Francisco Fed | 10 | recent | `https://www.frbsf.org/feed/` |
| GovInfo — Bills Enrolled | 100 | sporadic | `https://www.govinfo.gov/rss/bills-enr.xml` |
| GovInfo — Court of Intl Trade | 99 | sporadic | `https://www.govinfo.gov/rss/uscourts-cit.xml` |
| GovInfo — JPML | 100 | sporadic | `https://www.govinfo.gov/rss/uscourts-jpml.xml` |
| GovInfo — Court of Appeals DC | 100 | sporadic | `https://www.govinfo.gov/rss/uscourts-cadc.xml` |
| GovInfo — Court of Appeals 2nd | 100 | sporadic | `https://www.govinfo.gov/rss/uscourts-ca2.xml` |
| GovInfo — Economic Indicators | 99 | monthly | `https://www.govinfo.gov/rss/econi.xml` |
| NLRB — Press Releases | 10 | recent | `https://www.nlrb.gov/rss/rssPressReleases.xml` |
| NLRB — Weekly Summaries | 10 | recent | `https://www.nlrb.gov/rss/rssWeeklySummaries.xml` |
| NLRB — Announcements | 10 | recent | `https://www.nlrb.gov/rss/rssAnnouncements.xml` |
| Smithsonian Insider | 1483 | massive backlog | `https://insider.si.edu/feed/` |
| TTB — News | 401 | recent | `https://www.ttb.gov/templates/ttb/news/ttb.xml` |
| VA — VHA Inside Veterans Health | 712 | recent | `https://www.va.gov/health/NewsFeatures/news.xml` |

---

## HTTP 403 (35) — bot-blocked, may be recoverable

These returned HTTP 403 with the default `Mozilla/5.0 (compatible; BrieferBot/1.0; +https://briefer.news) Feedparser/6.0` User-Agent. Many federal sites
fingerprint that string as a scraper. **Browser-like UA + Accept headers may unlock most of these.**

Notable high-value 403s:
- **DoD Releases / Transcripts / Contracts** (war.gov)
- **All military branches**: Army, Navy, Air Force, Marines, Space Force, Space Systems Command, DCSA, DTRA
- **IC**: NRO, DIA
- **USDA FAS, FSIS** (food/ag — high-signal supply-chain)
- **DOT family**: DOT Newsroom, FAA, NHTSA Press, NHTSA Recalls, FRA, FMCSA, MARAD, FTA, PHMSA
- **DOE labs**: ORNL, ANL, INL, PNNL, AMES
- **DEA, ATF, USMS** (DOJ enforcement)
- **FEMA Press Releases, USCG**
- **SSA Press Releases**

A second probe with browser-headers should be run before declaring any of these dead.

---

## HTTP 404 (51) — bad URL guesses, drop or rediscover

Most were `(unverified)` pattern-derived URLs that don't exist. Exhaustive list in JSON; no action besides dropping from consideration unless we crawl each agency's actual RSS index page.

Examples: USDA NASS feeds, ERS, WASDE, BLS All News (different path needed), VA OIG, FAA News, multiple DOI sub-agencies (DOI Press, BIA, NPS, FWS, BOEM, BSEE), DHS Press, ICE, USCIS, BOP, IRS, Census, USPTO News, ITA, multiple HHS sub-agencies (CMS Newsroom, SAMHSA, HRSA, AHRQ, ACL), NREL, LANL, BNL, JLab, PPPL, SLAC, SBA, NARA, EEOC, EXIM, PBGC, CIA, Treasury Press Releases, FinCEN, Cleveland Fed, Philadelphia Fed, Richmond Fed, Minneapolis Fed, House Armed Services, Senate Energy.

Several of these likely DO have RSS, just not at the URL we guessed.

---

## Parse error (24) — returned HTML instead of RSS

Mostly Drupal sites where `?_format=rss` was a hopeful trick that didn't work, or RSS index pages that we hit instead of a specific feed.

Affected: Education, OSHA, ETA (all DOL pages); FHWA; BLM index; DOJ Antitrust news-feeds (HTML index of their feeds); LLNL; ODNI; **regional Fed banks** (Atlanta, Chicago, St. Louis Research, Dallas, Boston, Kansas City — all returned their HTML "feeds" listing pages, not actual RSS); **Senate committees** (Banking, Finance, Armed Services, Foreign Relations, Select Intelligence — Drupal didn't honor `?_format=rss`); **House committees** (Financial Services, Permanent Select Intel); US Courts top-level; CPSC; OPM.

These all have *some* RSS available — we'd just have to drill into each agency's RSS index page to find the actual feed URLs. That's a manual research pass per site.

---

## Recommended actions

### 1. Activate now (Tier 1, 7 sources)

Add to `sources.yaml` as `active: true`:

- GovInfo — Bills (`govinfo.gov/rss/bills.xml`)
- Federal Register — Public Inspection (`federalregister.gov/api/v1/public-inspection-documents.rss`)
- BLS — Major Economic Indicators (`bls.gov/feed/bls_latest.rss`)
- BEA — Releases (`apps.bea.gov/rss/rss.xml`)
- CBO — Publications (`cbo.gov/publications/all/rss.xml`)
- NY Fed — Liberty Street Economics (`libertystreeteconomics.newyorkfed.org/feed/`)
- CBP — News (`cbp.gov/rss.xml`)

### 2. Activate now (Tier 2, 7 sources — fresh today, lower priority)

- GovInfo — Hearings, Congressional Record, Presidential Documents
- DOJ — Justice News (OPA)
- DOL — News Releases
- GovInfo — Court of Appeals 9th
- VA — Press Room

### 3. Add as held in yaml (will produce when agency posts, ~17 sources)

- BLS Employment Situation, CPI, PPI
- FBI National Press, Top Stories
- LBNL, FNAL, SNL (DOE labs that work)
- CFPB, CMS Internet-Only Manuals
- NLRB (3 feeds)
- GovInfo: Public Laws, Reports, Federal Register, Court of Intl Trade, JPML, Court of Appeals DC + 2nd + 5th, Court of Federal Claims, Bills Enrolled, Economic Indicators
- NY Fed EPR, San Francisco Fed
- FEMA Disaster Declarations

### 4. Investigation: re-probe the 35 blocked sources with browser headers

High likelihood of unlocking DoD branches, military, USDA FAS, DOT family, DOE labs, IC. Separate script.

### 5. Drop or skip without further work

- The 51 HTTP 404 URLs — bad guesses, would need fresh per-agency rediscovery
- The 24 parse errors — would need to find specific feed URLs per agency

---

## What this run cost vs delivered

- 159 URLs probed in ~25 seconds wall-clock
- 19 immediately usable additions identified
- ~17 stale-but-valid additions identified
- 35 high-value targets queued for browser-UA retry
- ~75 URLs eliminated as bad pattern guesses or HTML pages

For ~30 minutes of agent + script work, we have a verifiable map of US-gov RSS reality circa May 2026.
