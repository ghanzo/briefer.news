# Source Operational Notes

> Per-source debug notes, site history, and operational quirks.
> `SOURCES.md` is the at-a-glance status board. This file is the depth.
> Update an entry when a source breaks, restructures, gets onboarded, or
> reveals a non-obvious quirk worth remembering.

---

## Template

When adding a source, use this layout. Keep entries terse — these are debug
shortcuts, not docs.

```
## <Source Name (matches sources.yaml)>

- **URL:** <current>
- **Type:** rss | rss_translate | web_scrape (extractor: trafilatura | playwright)
- **Category / Tier:** <values>
- **Last verified:** YYYY-MM-DD via <test script path>
- **Discovery:** <typical stub count, link_pattern reasoning>
- **Extraction:** <avg chars, primary method>
- **Site history:** <URL changes, restructures, RSS deprecations, redirects>
- **Known quirks:** <rate limits, leak-through landing pages, encoding, JS render needs>
- **High-signal samples:** <2-3 examples of what good output looks like>
- **Low-signal noise:** <ceremonial / boilerplate that should filter out>
- **If it breaks:** <first debug step>
```

---

## White House — News

- **URL:** `https://www.whitehouse.gov/news/`
- **Type:** `web_scrape`, `extractor: playwright`
- **Category / Tier:** geopolitics / 1
- **Last verified:** 2026-05-05 via `research/test_html_scrape.py` + `research/show_wh_samples.py`
- **Discovery:** ~95 raw stubs from the listing page, filtered down to ~11 real articles by `link_pattern: "/202"`. The pattern is a substring match on the URL path that catches date-prefixed segments (`/2026/`, future `/2027/`, etc.). It excludes nav links (`/gallery/`, `/wire/`), section landing pages (`/briefings-statements/`, `/presidential-actions/`), and admin pages (`/administration/cabinet/`). Coverage spans 4 content sections: `briefings-statements`, `releases`, `presidential-actions`, `research`.
- **Extraction:** ~1.5–2s per article via Playwright. `playwright_trafilatura` handles ~90% cleanly. Article length ranges 2.5k–50k chars (year-in-review documents are huge). Avg ~3–18k chars on typical days.
- **Site history:**
  - **Pre-2026:** content was at `/briefing-room/`. WH had at one point published RSS feeds from this section, which is why the 2024 catalog and our pre-2026-05-05 yaml both used that URL.
  - **2026 (verified 2026-05-05):** site restructured. `/briefing-room/` now 301-redirects to `/news/`. Sub-sections live as siblings of `/news/`: `/briefings-statements/`, `/releases/`, `/presidential-actions/`, `/research/`, `/remarks/`, `/fact-sheets/`. The `/news/` hub aggregates from all of them.
  - **No public RSS at any point in 2026.** WH dropped feeds entirely. HTML scraping is the only path.
- **Known quirks:**
  - JS-rendered. Plain `httpx` returns mostly-empty page. Must use Playwright.
  - `link_pattern` in `discovery.py` is **substring match, not regex**. Pattern `/202` is a forward-compatible heuristic (works through 2029); it would need bumping to `/20` or `/2_` style logic if WH ever publishes content with `/202` in a non-year context (unlikely but possible).
  - Listing page returns 80+ navigation/footer links. Without the `/202` filter, `discover_web_scrape` yields a flood of noise URLs.
  - Section landing pages (`/presidential-actions/`, `/briefings-statements/`) get passed through if `link_pattern` is too loose. They extract thin/repetitive text (1–2.5k chars). Stage 1 Groq filter should catch these; if importance-scoring sees them they should rate ~0.0–0.1.
- **High-signal samples (2026-05-05 listing):**
  - Cuba IEEPA sanctions Executive Order (2026-05-01) — 13.4k chars, full sectoral freeze on energy/metals/finance, foreign-financial-institution secondary sanctions clause
  - Bridger Pipeline cross-border permit (2026-04-30) — 7.9k chars, 36-inch diameter crude pipeline at MT/Canada border
  - Drug Pricing Most-Favored-Nation policy savings analysis (2026-05-05, `/research/`) — economic data on policy effect
  - Congressional Bill S.723 signed into law (2026-05-05)
- **Low-signal noise (filter expected to catch):**
  - Heritage-month / anniversary / awareness-week proclamations (Jewish American Heritage, Physical Fitness, Hurricane Preparedness, Astronaut Day, etc.)
  - Section landing pages if they leak through
- **If it breaks:**
  1. Run `research/debug_whitehouse.py` — dumps full HTML, shows `<title>`, canonical URL, all link counts. The most common failure is a site restructure changing the URL or link patterns.
  2. Compare the canonical URL — if it doesn't match `https://www.whitehouse.gov/news/` or the original URL, the listing page has moved.
  3. Inspect the printed link path buckets — find which section paths still have date-prefixed entries.
  4. Update yaml `url` and `link_pattern`, re-run `test_html_scrape.py` to verify.
  5. Save fresh samples to `research/wh_samples/` for the next regression check.

---

## DOJ — Antitrust Press Room

- **URL:** `https://www.justice.gov/atr/press-room-0`
- **Type:** `web_scrape`, `extractor: playwright`
- **Category / Tier:** security / 1
- **Last verified:** 2026-05-05 via `research/test_html_scrape.py`
- **Discovery:** ~130 raw stubs from the page, filtered to ~11 real articles by `link_pattern: "/opa/"`. Article URLs split across 3 sub-paths: `/opa/pr/<slug>` (press releases, ~7), `/opa/speech/<slug>` (ATR speeches, ~3), `/opa/video/<slug>` (~1). The press-room page itself acts as the topic filter — anything linked from `/atr/press-room-0` is antitrust-relevant by construction even though `/opa/` is the shared DOJ-wide press path.
- **Extraction:** ~1.0–1.5s per article via Playwright. `playwright_trafilatura` handles all three URL types. Press releases extract ~2.5–3k chars cleanly (Press Release header, body, contact). Video pages extract ~1.1k chars of mostly boilerplate (no transcript on the page) — usable but lower signal. Speeches are full text.
- **Site history:** URL stable as of 2026-05-05. Note: we initially tried `/atr/news-feeds` (returned HTML feeds-index page → parse_error) and `/atr/news` (didn't exist). The actual press room slug is `/atr/press-room-0` — the trailing `-0` is a Drupal node-disambiguation artifact, not a typo.
- **Known quirks:**
  - URLs are **NOT date-prefixed** (unlike WH). The `/202` trick we use for WH won't work here. Don't expect `/YYYY/MM/` in the path.
  - `/opa/` is the shared DOJ-wide press path. Articles linked from `/atr/press-room-0` are antitrust-related, but if we ever scraped from a different /opa/ landing page (e.g., a different DOJ component's press room), `/opa/` would NOT be a sufficient topic filter on its own.
  - **Potential overlap with the existing "DOJ — Justice News (OPA)" RSS feed.** Both can produce the same `/opa/pr/<slug>` URL. The pipeline's `url_hash` dedupe handles this — a given press release is saved once regardless of source. Net effect: scraping both sources is redundant for press releases but adds ATR speeches + videos that the OPA RSS doesn't have.
  - 33 of the 130 raw stubs are pagination links to `/atr/press-room-0` itself. The link_pattern filter cuts these.
  - Video pages are thin (boilerplate only). Stage 1 filter or low importance score should drop them.
- **High-signal samples (2026-05-05 listing):**
  - **DOJ sues NY-Presbyterian Hospital** for anticompetitive contracts that increase prices (major hospital antitrust)
  - **Antitrust Division approves DOE Defense Production Act consortium voluntary agreement** — DOE + DPA + antitrust intersection, strategic-industry coordination
  - Acting AG Blanche announces antitrust investigations of meatpacking operations (food supply chain)
  - DOJ + FTC extend deadline for public comment on guidance on business collaborations (joint policy)
  - Fuel executive 5-year prison sentence for defrauding US military in fuel contract bid scam
  - Former Air Force member pleads guilty to multi-year bid rigging schemes
- **Low-signal noise (filter expected to catch):**
  - Video page boilerplate (no transcript content)
  - Routine ATR speech recaps when speech is ceremonial rather than policy-signaling
- **If it breaks:**
  1. Visit `https://www.justice.gov/atr/press-room-0` in a browser — confirm the page renders and lists article cards
  2. Re-run `test_html_scrape.py` with the existing `/opa/` link_pattern. If 0 stubs returned, the page structure has changed.
  3. Try a debug fetch — inspect what URL paths the page now links to. Maybe DOJ moved press releases to `/atr/pr/<slug>` or some new path; update `link_pattern` accordingly.
  4. Verify the URL itself didn't move — DOJ Drupal sites occasionally reroute. Try `/atr/press-releases` (plural, no `-0`), `/atr` (root) for redirects.
  5. Save fresh samples for next regression check.
- **Future mining (not yet activated, evaluated 2026-05-05):**
  DOJ has additional content-type-specific landing pages we could scrape as separate sources for non-press-release coverage. These were investigated but deferred — the existing OPA RSS + ATR Press Room cover the highest-signal content. Worth revisiting if/when we want broader DOJ coverage:
  - `https://www.justice.gov/news/speeches` — DOJ-wide speeches across all components. Often signals policy direction before formal enforcement action.
  - `https://www.justice.gov/news/videos` — press conferences and announcements (extraction may be thin without transcripts).
  - `https://www.justice.gov/news/blogs` — DOJ blog posts; mixed signal value.
  - Top-level `https://www.justice.gov/news` page itself was tested 2026-05-05 — mostly duplicates the OPA RSS feed (~10 `/opa/pr/` items, same content). Not worth adding as its own source.

---

## DOE — Newsroom

- **URL:** `https://www.energy.gov/newsroom`
- **Type:** `web_scrape`, `extractor: playwright`
- **Category / Tier:** energy / 1
- **Last verified:** 2026-05-05 via `research/test_html_scrape.py`
- **Discovery:** ~80 raw stubs from the page, filtered to ~16 real articles by `link_pattern: "/articles/"`. Articles live primarily at `/articles/<slug>` (main DOE press), with some at sub-office paths like `/hgeo/opr/articles/<slug>` (HGEO/Office of Petroleum Reserves) — the substring match catches both. Coverage: fact sheets, Secretary speeches/testimony, sub-office announcements, ICYMI items.
- **Extraction:** ~2.0–2.5s per article via Playwright. `playwright_trafilatura` handles all article paths cleanly. Article length ranges 2–8k chars; fact sheets are typically 5–8k chars (rich), targeted press releases (RFPs, sub-office announcements) ~2–3k chars.
- **Site history:** URL stable as of 2026-05-05. DOE is a Drupal site that's stayed at `/newsroom` as the listing page. The `/articles/` content path hasn't been observed to change recently. Sub-offices (HGEO, EM, NETL, etc.) sometimes have their own `/<office>/articles/` paths which fold into the master listing.
- **Known quirks:**
  - **Minor link_pattern leak:** `/cio/articles/vulnerability-disclosure-policy` matches `/articles/` substring. It's a one-off admin/policy page. If it slips through and gets summarized, Stage 1 filter or low importance score should drop it.
  - **No date prefix in URLs.** Don't expect `/YYYY/MM/` in the path. Rely on the article-page metadata (publish date) for chronology, captured by Stage 2.
  - **Sub-office articles** like `/hgeo/opr/articles/...` are linked from the main newsroom. They're high-signal (Strategic Petroleum Reserve activity in particular). Worth keeping captured.
  - **Heavy political tone** in current administration's content (2026). Stage 1 filter prompt is calibrated to keep enforcement actions, RFPs, testimony, and policy moves regardless of framing — the political language doesn't disqualify a source if the underlying action is real.
- **High-signal samples (2026-05-05 listing):**
  - **DOE issues RFP for emergency 92.5M-barrel Strategic Petroleum Reserve exchange** (HGEO/OPR, April 30) — direct lens-priority signal: physical energy substrate, supply stabilization
  - Secretary Wright signs LNG export agreements ("Trump Peace Pipelines") — US energy diplomacy
  - Wright delivers remarks alongside interim Venezuelan president Delcy Rodriguez — direct US/Venezuela energy positioning (lens calls this out specifically)
  - NESE Pipeline groundbreaking in NYC (Wright, Zeldin, Burgum) — energy infrastructure
  - Deputy Secretary Danly commends FERC large-load interconnection reform — grid + AI data center implications
  - Wright Senate Energy & Natural Resources testimony on FY2026 budget
  - Wright House Energy Subcommittee testimony
  - "ICYMI: Time to stop subsidizing solar and wind in perpetuity" — energy transition policy signal
- **Low-signal noise (filter expected to catch):**
  - Generic "fact sheet" titles that turn out to be political messaging without operational content
  - The `/cio/articles/vulnerability-disclosure-policy` admin leak
- **If it breaks:**
  1. Visit `https://www.energy.gov/newsroom` in a browser — confirm article cards render
  2. Re-run `test_html_scrape.py`. If 0 stubs returned with `/articles/` filter, the path format changed.
  3. Inspect the printed URL bucket distribution — find which path patterns the listing now links to.
  4. Update `link_pattern` accordingly. If DOE adopts date-prefixed URLs (like WH did), shift to `/202` style.
  5. Save fresh samples for next regression check.

---

## ARPA-E — News & Insights

- **URL:** `https://arpa-e.energy.gov/news-and-events/news-and-insights`
- **Type:** `web_scrape`, `extractor: playwright`
- **Category / Tier:** energy / 1
- **Last verified:** 2026-05-05 via `research/test_html_scrape.py` + `research/debug_arpae.py`
- **Discovery:** ~77 raw stubs from the page, filtered to ~15 real articles by `link_pattern: "/news-and-insights/"`. Article URLs are direct slugs at `/news-and-events/news-and-insights/<long-slug>`. The trailing slash in the pattern is **load-bearing** — it excludes the bare listing page (`/news-and-events/news-and-insights` with no trailing slash) which would otherwise leak.
- **Extraction:** ~3.0–3.1s per article via Playwright. `playwright_trafilatura` cleanly extracts publication date + headline + body. Article length 1.8–5.3k chars. Each article opens with `Publication Date:\n<MMM DD YYYY>` so date is reliable.
- **Site history:**
  - **Pre-2026:** original yaml URL was `https://arpa-e.energy.gov/news-and-media/press-releases` (carried over from earlier catalog work). That URL still loads but renders the same content as `/news-and-events/news-and-insights` — both work.
  - **2026 (verified 2026-05-05):** site is on a Drupal-style stack with React/JS for cards, but article URLs are inline in the rendered HTML — NOT lazy-loaded. Initial test bucketed wrong, masked the article URLs. They're there.
- **Known quirks:**
  - **Critical: `link_pattern` MUST have trailing slash.** Use `/news-and-insights/`, not `/news-and-insights`. Without the trailing slash, the listing root (no slug) leaks through and gets scraped, producing thin/nav-only text.
  - Initial debugging confusion: my test_html_scrape.py bucketing logic groups URLs by `/<seg1>/<seg2>` prefix. `/news-and-events/news-and-insights/<slug>` and the bare `/news-and-events/news-and-insights` both bucket as the same prefix. The display showed only one example, making it look like only the listing was returned. **Lesson: always grep the saved HTML before declaring a page broken.** See `research/debug_arpae.py` for the proper inspection.
  - The page's bucketed view in our test script may show a misleading "1 hit, 1 example" line; the actual returned stub list (Phase 1 first-10 output) is the source of truth.
  - URLs have no date prefix — slugs alone. Publication date comes from inside the article (extractor finds it).
- **High-signal samples (2026-05-05 listing — all P1 lens-relevant):**
  - **$135M fusion technology commitment** — largest fusion investment in agency history (Apr 8). Direct fusion R&D signal.
  - **$50M transuranic fuels for advanced reactors** (Apr 28) — nuclear fuel cycle, advanced reactor program
  - **$60M domestic critical mineral supply + magnet manufacturing** — critical minerals supply chain (lens priority #4 — materials)
  - **$25M critical minerals from wastewater** — alternative critical mineral sourcing
  - **$35M to triple US transmission capacity** — grid infrastructure
  - $37M quantum computing for chemistry & materials
  - $34M AI + autonomous labs for catalyst development
  - $30M baseload via superhot geothermal
  - SCALEUP Ready Program 2026 first projects
- **Low-signal noise (filter expected to catch):**
  - Routine "ARPA-E Energy Innovation Summit" recap announcements
  - Internal program kickoffs without funding details
- **If it breaks:**
  1. Check the saved `research/arpae_debug.html` — does it still contain `/news-and-insights/<slug>` hrefs?
  2. Run `research/debug_arpae.py` to fetch a fresh debug snapshot and see the link inventory.
  3. If 0 articles found in the HTML, the site has restructured. Check the canonical URL — may have moved.
  4. If articles are present but our test script shows 0 stubs, verify `link_pattern` is `/news-and-insights/` with the trailing slash.
  5. Save fresh samples for next regression check.

---

## DEFERRED — Atlanta Fed (and likely sister regional Fed banks)

**Status:** Investigated 2026-05-05, **not activated** (low signal + technical blocker).

**URLs tested:** `/news` (redirects to `/news-and-events`), `/news-and-events/press-room`, `/news-and-events/press-room/press-releases`, `/news-and-events/speeches`. All return 116-150KB HTML with NO article URLs — content is JS-rendered after page load.

**Two-layer problem:**
1. **Technical:** Playwright `networkidle` times out at 30s (perpetual background JS). Plain httpx returns the listing chrome but no articles. Fix would require modifying `scraper/browser.py` (e.g., `wait_until="domcontentloaded"` + `wait_for_selector` or extra `wait_for_timeout`). That's a real change affecting all 4 active web_scrape sources — risk to working scrapes.
2. **Editorial:** Press release cadence is **very low** — latest Apr 9, before that Feb 12 (~2/quarter). Doesn't pay back the scraper-enhancement work.

**Sister Fed banks (likely same blocker):** Chicago Fed (NFCI), Cleveland Fed, Richmond Fed, Boston Fed, Dallas Fed, San Francisco Fed — same Federal Reserve Drupal/JS platform. Several returned HTML index pages on RSS endpoints in our 2026-05-02 probe.

**What we DON'T lose:** NY Fed Liberty Street Economics (active RSS) covers the highest-signal regional Fed research. GDPNow itself is a single-page data tool, captured in the briefer/ DuckDB CLI's FRED catalog as series `GDPNOW`.

**To re-enable:** bundle with a generic Playwright `domcontentloaded` fallback + selector wait in `scraper/browser.py`, justified by 2-3 deferred sources blocked by the same issue, not just Atlanta Fed alone.

---

## ORNL — Oak Ridge News

- **URL:** `https://www.ornl.gov/news`
- **Type:** `web_scrape`, `extractor: playwright`
- **Category / Tier:** energy / 1
- **Last verified:** 2026-05-05 via `research/test_html_scrape.py`
- **Discovery:** ~117 raw stubs from page, filtered to ~17 by `link_pattern: "/news/"`. Of the 17, ~11 are real article slugs (multi-word hyphenated paths like `/news/how-mpex-will-accelerate-fusion-energy`); ~6 are sub-section landing pages (`/news/releases`, `/news/features`, `/news/researcher-profiles`, `/news/story-tips`, `/news/audio-spots`, `/news/honors-and-awards`) that leak through.
- **Extraction:** ~1.3–1.6s per article via Playwright. `playwright_trafilatura` extracts cleanly. Article length ~3.2–3.6k chars (research summary format).
- **Site history:** Stable. ORNL is one of the few DOE labs that didn't 403 our default User-Agent — it just works with Playwright. The 5 sister labs we tested (ANL, INL, PNNL, AMES, LANL) all failed: ANL+INL timeout on networkidle, PNNL was 404, LANL DNS-failed (subdomain wrong).
- **Known quirks:**
  - **Sub-section landing pages leak through.** Same issue as DOE Newsroom — 6 short-slug URLs (`releases`, `features`, etc.) get returned. They extract thin/repetitive list text. Stage 1 filter / low importance score should catch.
  - **No date prefix in URLs**, slugs only. Date comes from inside the article.
- **High-signal samples (2026-05-05 listing — lens-relevant R&D):**
  - **MPEX accelerates fusion energy** — fusion (P1)
  - **Quantum materials discovery via moiré atomic visualization** — quantum/materials
  - **Imaging innovation for nuclear materials qualification** — nuclear fuel cycle
  - **Microgrid research milestone — grid resilience** — grid
  - **Photon framework scales AI vulnerability discovery** — AI security
  - **Q&A on autonomous labs in materials research** — AI + materials
  - **Molten salt chemistry converts polymer waste to fuel** — energy chemistry
  - **Five medical radioisotopes + stable isotope rise** — isotope production
  - Neutron scattering for space exploration applications
- **Low-signal noise (filter expected to catch):**
  - Sub-section landing pages (releases, features, etc.)
  - Researcher-profile articles (Q&As without research substance)
  - Honors-and-awards items
- **If it breaks:**
  1. Visit `https://www.ornl.gov/news` in a browser — confirm article cards render
  2. Re-run `test_html_scrape.py` with `/news/` pattern. If 0 article-shaped stubs, ORNL site changed.
  3. Other DOE labs (LBNL, FNAL, SNL — already in held block, all on WordPress patterns) might be tried as alternatives if ORNL goes dark.
