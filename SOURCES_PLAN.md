# Sources Plan — Authoritative Build Specification

> This document defines **what we want** to scrape, in what language, using what tool.
> It is the spec. Probing happens after this document is written, against these specific URLs.
> Probing results and confirmed status are tracked in `SOURCES_MATRIX.md`.
>
> Last updated: Feb 2026.
> Regional priority order: US → China → Europe → India → Asia → Russia → Middle East → South America → Africa

---

## Language & Translation Strategy

The central principle: **go to the source in its native language.**

English RSS feeds from non-English institutions are almost always:
- Stale (updated less frequently than the native feed)
- Curated (PR-filtered, omitting the operationally important content)
- Incomplete (English press releases ≠ full news output)
- Broken (most have been abandoned as institutions moved to JS-rendered sites)

The right approach is to scrape the authoritative native-language source and translate
during Stage 2 summarization. Gemini Flash (the Stage 2 model) reads Chinese, Japanese,
Korean, Arabic, Russian, Portuguese, Spanish, and French natively. Translation is free —
it happens inside the summarization call.

**Pipeline change required:** One line in the Stage 2 prompt:
> *"The article below may be in any language. Summarize it in English."*

That is the entire translation infrastructure. No separate translation API, no extra cost,
no extra latency. The multilingual capability is already in the model.

**Language detection:** Add `langdetect` to requirements.txt. Tag each article stub with
`language` at discovery time. Use this for logging, filtering, and prompt selection.

---

## Tool Classification

| Tool | When to use | Capability status |
|---|---|---|
| `rss` | Feed is valid RSS/Atom, feedparser parses it | Built ✓ |
| `rss_translate` | Valid RSS but content in non-English | Built ✓ (add lang tag) |
| `web_scrape` | Static HTML, no JS required | Built ✓ |
| `playwright` | JS-rendered page, no bot blocking | Built ✓ |
| `playwright_translate` | JS-rendered + non-English content | Built ✓ |
| `playwright_cloudflare` | Cloudflare-protected — needs stealth headers/delays | Not built — Phase B |
| `data_api` | JSON/XML data endpoint | Not built — Phase C |
| `pdf` | Monthly reports distributed as PDF | Not built — Phase D |

**Cloudflare note:** IEA, OPEC, OECD, and several others return 403 with Cloudflare
challenge pages. Playwright alone does not bypass Cloudflare — it requires additional
headers, delays, and sometimes a residential proxy. This is a Phase B capability.
For now, Google News queries are the practical fallback for Cloudflare-blocked sources.

---

## Priority Scale

| Priority | Meaning |
|---|---|
| P1 | Must have — directly feeds the primary analytical questions |
| P2 | High value — fills a significant gap in the framework |
| P3 | Useful — adds breadth or redundancy |
| P4 | Future — worth building toward but not urgent |

---

## 1 — United States

**Language:** English
**Status:** Well-covered. See `SOURCES_MATRIX.md` for full active list.
**Remaining gaps to address:**

| Source | Institution | URL | Tool | Access | Priority |
|--------|-------------|-----|------|--------|----------|
| USDA — NASS crop reports | Dept of Agriculture | usda.gov/media/press-releases/rss | rss | likely_open | P2 |
| USDA — World Agricultural Supply | Dept of Agriculture | usda.gov/oce/commodity/wasde/ | web_scrape | open | P2 |
| Supreme Court — Opinions | SCOTUS | supremecourt.gov | web_scrape | open | P2 |
| DOJ — Civil Rights | Dept of Justice | justice.gov/rss/civil-rights.xml | rss | likely_open | P2 |
| FRED — Economic data API | St. Louis Fed | api.stlouisfed.org/fred | data_api | free key needed | P1 |
| BLS — Data API | Bureau of Labor Statistics | api.bls.gov/publicAPI/v2 | data_api | free key needed | P1 |
| EIA — Data API | Energy Info Admin | api.eia.gov/v2 | data_api | free key needed | P1 |
| Treasury — Yield Curve | US Treasury | home.treasury.gov (XML) | data_api | open (keyless) | P1 |
| Baker Hughes — Rig Count | Baker Hughes | rigcount.bakerhughes.com | web_scrape | likely_open | P2 |

**Notes:**
- Baker Hughes weekly rig count is the leading indicator for Permian production trajectory.
  EIA also publishes rig count data — try EIA API first as we will have the key anyway.
- FRED, BLS, EIA data APIs are P1 because economic data is ground truth, not narrative.
- USDA WASDE report (monthly World Agricultural Supply and Demand Estimates) is one of the
  most market-moving reports in the world — food prices, crop forecasts, supply signals.

---

## 2 — China

**Language:** Mandarin (Simplified Chinese) — primary. English versions are stale or filtered.
**Scrape strategy:** Playwright on Chinese-language sites. Most Chinese gov sites are
accessible from outside China — the Great Firewall restricts inbound, not outbound.
**Translation:** Stage 2 Gemini Flash handles Chinese natively.

### Government & Policy

| Source | Institution | URL | Tool | Access | Priority |
|--------|-------------|-----|------|--------|----------|
| MFA press briefings (外交部) | Ministry of Foreign Affairs | fmprc.gov.cn/wjdt/zbdhd/ | playwright_translate | likely_open | P1 |
| MFA spokesperson statements | MFA | fmprc.gov.cn/wjbxw/ | playwright_translate | likely_open | P1 |
| State Council — policy releases | State Council | gov.cn/zhengce/ | playwright_translate | likely_open | P1 |
| Xinhua wire (新华社) | Xinhua | xinhua.net/silkroad/ | playwright_translate | likely_open | P1 |
| People's Daily front page | People's Daily | people.com.cn | playwright_translate | likely_open | P2 |
| MOFCOM — trade news | Ministry of Commerce | mofcom.gov.cn/article/ae/ | playwright_translate | likely_open | P1 |
| NDRC — policy announcements | Natl Development & Reform Commission | ndrc.gov.cn/xwdt/ | playwright_translate | likely_open | P2 |
| MIIT — tech/industry news | Ministry of Industry & Info Tech | miit.gov.cn/xwdt/ | playwright_translate | likely_open | P2 |
| SASAC — state enterprise news | State Assets Supervision | sasac.gov.cn/n2588025/ | playwright_translate | likely_open | P3 |

### Finance & Economic Data

| Source | Institution | URL | Tool | Access | Priority |
|--------|-------------|-----|------|--------|----------|
| PBOC — policy statements | People's Bank of China | pbc.gov.cn/goutongjiaoliu/ | playwright_translate | likely_open | P1 |
| NBS — statistics releases | National Bureau of Statistics | stats.gov.cn/sj/zxfb/ | data_api + playwright | likely_open | P1 |
| CSRC — securities regulation | China Securities Regulatory Comm | csrc.gov.cn/csrc/c101954/ | playwright_translate | likely_open | P2 |
| SAFE — foreign exchange | State Admin of Foreign Exchange | safe.gov.cn/safe/whxw/ | playwright_translate | likely_open | P2 |

### Media (state — read as narrative management)

| Source | Institution | URL | Tool | Access | Priority |
|--------|-------------|-----|------|--------|----------|
| Global Times (环球时报) | Global Times | huanqiu.com | playwright_translate | likely_open | P2 |
| CCTV News | CCTV | news.cctv.com | playwright_translate | likely_open | P3 |

**Note:** We currently have Global Times English RSS (50 entries, Feb 2026) as the only
active Chinese source. This is the fallback until the Mandarin scraping pipeline is built.
Chinese state media should always be labeled as such in the article metadata.

---

## 3 — Europe

**Language:** English for EU institutions and UK. German, French, Italian for national sources.
EU institutions publish authoritatively in English — this is not a translated fallback.
**Status:** ECB publications and UK Gov confirmed working. Commission, NATO, Parliament
all returned broken URLs — need correct URLs before probing again.

### EU Institutions

| Source | Institution | URL | Tool | Access | Priority |
|--------|-------------|-----|------|--------|----------|
| European Commission — Press | European Commission | ec.europa.eu/commission/presscorner/home/en | playwright | js_rendered | P1 |
| EC — Newsroom RSS (find correct URL) | European Commission | ec.europa.eu/newsroom/index.cfm?do=rss | rss | unknown | P1 |
| ECB — Publications | European Central Bank | ecb.europa.eu/press/pr/date/2026/html/rss.xml | rss | open ✓ | P1 |
| ECB — Economic Bulletin | ECB | ecb.europa.eu/pub/economic-bulletin/html | playwright | likely_open | P1 |
| NATO — News | NATO | nato.int/cps/en/natohq/news.htm | playwright | js_rendered | P1 |
| European Parliament — News | EU Parliament | europarl.europa.eu/news/en/agenda/briefing | playwright | likely_open | P2 |
| Council of EU — Press | Council of EU | consilium.europa.eu/en/press/press-releases | playwright | likely_open | P2 |
| OSCE — News | OSCE | osce.org/whatistheosce/factsheets | web_scrape | unknown | P2 |
| Eurostat — Key indicators | Eurostat | ec.europa.eu/eurostat/web/main/data/database | data_api | open | P2 |

### National (High Priority)

| Source | Institution | Language | URL | Tool | Access | Priority |
|--------|-------------|----------|-----|------|--------|----------|
| UK Gov — Foreign Policy | UK Government | English | gov.uk/search/news-and-communications.atom?subtopic[]=foreign-policy | rss | open ✓ | P1 |
| Bank of England — News | Bank of England | English | bankofengland.co.uk/rss/news | rss | likely_open | P1 |
| Bundesbank — Press | German Central Bank | German/English | bundesbank.de/en/press | web_scrape | likely_open | P2 |
| Banque de France — News | French Central Bank | French | banque-france.fr/actualites | web_scrape | likely_open | P3 |

---

## 4 — India

**Language:** English (official language, used across all central government communications).
India has strong English-language institutional publishing — we do not need translation.
**Problem:** PIB and MEA both returned 403 on our probe. Need correct RSS URLs.

| Source | Institution | URL | Tool | Access | Priority |
|--------|-------------|-----|------|--------|----------|
| PIB — Press releases | Press Information Bureau | pib.gov.in/newsite/erelease.aspx | web_scrape | 403 (find RSS) | P1 |
| PIB — RSS (find correct URL) | Press Information Bureau | pib.gov.in/RssMain.aspx | rss | 403 | P1 |
| MEA — Press releases | Ministry of External Affairs | mea.gov.in/press-releases.htm | web_scrape | 403 (find RSS) | P1 |
| RBI — Press releases | Reserve Bank of India | rbi.org.in/scripts/BS_PressReleaseDisplay.aspx | web_scrape | likely_open | P1 |
| RBI — Monetary Policy | RBI | rbi.org.in/scripts/BS_ViewMasDirections.aspx | web_scrape | likely_open | P1 |
| SEBI — Press releases | Securities & Exchange Board | sebi.gov.in/sebiweb/home/HomeDsp.jsp | playwright | likely_open | P2 |
| Ministry of Commerce | Dept of Commerce | commerce.gov.in/press-release | web_scrape | likely_open | P2 |
| MOSPI — Statistics | Ministry of Statistics | mospi.gov.in | data_api | likely_open | P2 |
| Ministry of Finance | Finance Ministry | finmin.nic.in/press-room | web_scrape | likely_open | P2 |

**Notes:**
- PIB 403 is likely a User-Agent block, not Cloudflare — try with a browser User-Agent string.
- India is the critical swing state in the US-China competition. MEA statements on China,
  Russia, and the US are high-signal. India's non-aligned positioning is itself a daily signal.

---

## 5 — Asia (Non-China)

### Japan

**Language:** Japanese primary. English sections exist but are incomplete.
**Scrape strategy:** Playwright on Japanese-language pages, translate in Stage 2.

| Source | Institution | URL | Tool | Access | Priority |
|--------|-------------|-----|------|--------|----------|
| MFA Japan — Press (外務省) | Ministry of Foreign Affairs | mofa.go.jp/press/release/ | playwright_translate | 403 on RSS, try scrape | P1 |
| Cabinet Secretariat (官邸) | PM's Office | kantei.go.jp/jp/tyoukanpress/ | playwright_translate | likely_open | P1 |
| Bank of Japan (日本銀行) | BOJ | boj.or.jp/announcements/ | playwright_translate | likely_open | P1 |
| METI — Trade & Industry | Ministry of Economy, Trade & Industry | meti.go.jp/press/ | playwright_translate | likely_open | P2 |
| JETRO — Trade news | Japan External Trade Org | jetro.go.jp/biznews/ | playwright_translate | likely_open | P2 |
| FSA Japan — Financial | Financial Services Agency | fsa.go.jp/news/ | playwright_translate | likely_open | P2 |

### South Korea

**Language:** Korean primary.

| Source | Institution | URL | Tool | Access | Priority |
|--------|-------------|-----|------|--------|----------|
| MFA Korea (외교부) | Ministry of Foreign Affairs | mofa.go.kr/eng/brd/m_5674/list.do | web_scrape | returned HTML | P1 |
| Bank of Korea (한국은행) | BOK | bok.or.kr/portal/cmmn/file/pvwFileDown.do | web_scrape | likely_open | P1 |
| MOTIE — Trade | Ministry of Trade, Industry, Energy | motie.go.kr | playwright_translate | likely_open | P2 |
| KISA — Cybersecurity | Korea Internet & Security Agency | kisa.or.kr | playwright_translate | likely_open | P3 |

### Taiwan

**Language:** Traditional Chinese + English.
**Why P1:** Taiwan is the most likely near-term geopolitical flashpoint. Having no Taiwanese
government source is a material gap in US-China analysis.

| Source | Institution | URL | Tool | Access | Priority |
|--------|-------------|-----|------|--------|----------|
| MFA Taiwan (外交部) | Ministry of Foreign Affairs | mofa.gov.tw/en/ | web_scrape | returned HTML | P1 |
| Office of the President | President's Office | president.gov.tw/en/ | playwright | likely_open | P1 |
| Mainland Affairs Council | MAC | mac.gov.tw/en/ | web_scrape | likely_open | P1 |
| MOEA — Trade/Economy | Ministry of Economic Affairs | moea.gov.tw/Mns/english/ | web_scrape | likely_open | P2 |
| MOFA — Press releases feed | MFA | mofa.gov.tw/en/News_PressRelease.aspx | playwright | returned HTML | P1 |

### Singapore

**Language:** English.

| Source | Institution | URL | Tool | Access | Priority |
|--------|-------------|-----|------|--------|----------|
| Singapore PM Office | PMO | pmo.gov.sg/Newsroom | playwright | 404 (find correct) | P2 |
| MAS — Monetary Authority | MAS | mas.gov.sg/news | playwright | 404 (find correct) | P2 |
| MTI — Trade & Industry | MTI | mti.gov.sg/Newsroom | web_scrape | likely_open | P2 |

### ASEAN

| Source | Institution | URL | Tool | Access | Priority |
|--------|-------------|-----|------|--------|----------|
| ASEAN Secretariat | ASEAN | asean.org/news/ | playwright | returns empty RSS | P2 |

---

## 6 — Russia

**Language:** Russian primary. The Russian-language feeds are current and complete.
English versions are either broken (MFA) or lag behind.
**Scrape strategy:** Use Russian-language RSS where available. Translate in Stage 2.
**Note:** All Russian state sources should be labeled as state media in article metadata.

| Source | Institution | URL (Russian) | Tool | Access | Priority |
|--------|-------------|---------------|------|--------|----------|
| Kremlin — Russian feed | President's Office | kremlin.ru/events/all/feed | rss_translate | open ✓ (use HTTP) | P1 |
| MFA Russia — Press (МИД) | Ministry of Foreign Affairs | mid.ru/press_service/spokesman/briefings/ | playwright_translate | likely_open | P1 |
| MFA Russia — Statements | MFA | mid.ru/foreign_policy/news/ | playwright_translate | likely_open | P1 |
| TASS — Russian wire | TASS | tass.ru/mezhdunarodnaya-panorama | rss_translate | likely_open | P1 |
| TASS — English wire | TASS | tass.com/rss/v2.xml | rss | open ✓ | P1 |
| Bank of Russia — News | Central Bank | cbr.ru/press/pr/ | playwright_translate | likely_open | P2 |
| Rosstat — Economic data | Federal Statistics Service | rosstat.gov.ru/bgd/free/ | data_api | likely_open | P3 |
| Ministry of Energy — News | Minenergo | minenergo.gov.ru/node/news | playwright_translate | likely_open | P2 |

**Note on RT:** RT English (100 entries, confirmed current) is an option but is internationally
recognized as a foreign influence operation and is banned/restricted in the EU and UK.
Including it would require prominent labeling and careful use. Recommend skipping RT and
sourcing TASS + Kremlin instead — same information, clearer provenance.

---

## 7 — Middle East

**Language:** Arabic primary. English versions often JS-blocked or incomplete.
**Translation:** Stage 2 Gemini Flash handles Arabic natively.

### Gulf States

| Source | Institution | Language | URL | Tool | Access | Priority |
|--------|-------------|----------|-----|------|--------|----------|
| Saudi Press Agency (وكالة الأنباء) | SPA | Arabic | spa.gov.sa/ar/pressreleases | playwright_translate | js_blocked | P1 |
| Saudi MFA | Saudi MFA | Arabic | mofa.gov.sa/ar/ | playwright_translate | likely_open | P2 |
| UAE WAM — Arabic | WAM News Agency | Arabic | wam.ae/ar | playwright_translate | bot_blocked (F5) | P2 |
| UAE MFA | UAE MFA | Arabic/English | mofaic.gov.ae/en/mediahub | playwright | likely_open | P2 |
| Qatar QNA | Qatar News Agency | Arabic/English | qna.org.qa/en-US/news | web_scrape | likely_open | P2 |
| Kuwait KUNA | Kuwait News Agency | Arabic/English | kuna.net.kw/rss | rss | likely_open | P2 |

### Regional

| Source | Institution | Language | URL | Tool | Access | Priority |
|--------|-------------|----------|-----|------|--------|----------|
| Iran IRNA — Press | IRNA | Farsi | irna.ir/rss | rss_translate | likely_open | P1 |
| Iran Tasnim — English | Tasnim | English | tasnimnews.com/en/rss | rss | likely_open | P2 |
| Israel MFA | MFA Israel | English/Hebrew | mfa.gov.il/mfa/pressroom | playwright | 403/SSL failure | P1 |
| Turkish MFA | Turkish MFA | Turkish/English | mfa.gov.tr/site/english | web_scrape | likely_open | P2 |
| Anadolu Agency — English | Anadolu | English | aa.com.tr/en/rss/default?cat=politics | rss | open ✓ | P2 |
| Al Jazeera — World | Al Jazeera | English | aljazeera.com/xml/rss/all.xml | rss | open ✓ | P2 |
| Arab League | Arab League | Arabic/English | lasportal.org/en | playwright | timeout | P3 |

### Energy (regional)

| Source | Institution | Language | URL | Tool | Access | Priority |
|--------|-------------|----------|-----|------|--------|----------|
| OPEC — Press releases | OPEC | English | opec.org/opec_web/en/press_room/24.htm | playwright_cloudflare | cloudflare 403 | P1 |
| OAPEC | Arab Petroleum Exporting Countries | Arabic/English | oapecorg.org | web_scrape | unknown | P2 |

---

## 8 — South America

**Language:** Portuguese (Brazil), Spanish (Argentina, Chile, Colombia, Venezuela, Peru).
**Translation:** Stage 2 Gemini Flash handles both natively.

### Brazil (highest priority — largest economy, Amazon, lithium, oil)

| Source | Institution | Language | URL | Tool | Access | Priority |
|--------|-------------|----------|-----|------|--------|----------|
| Agência Brasil | Gov wire service | Portuguese | agenciabrasil.ebc.com.br/en | web_scrape | 404 (try pt URL) | P1 |
| Agência Brasil — Portuguese | Gov wire service | Portuguese | agenciabrasil.ebc.com.br/geral | playwright_translate | likely_open | P1 |
| Brazil MFA (Itamaraty) | Foreign Affairs | Portuguese | gov.br/mre/pt-br/assuntos/noticias | playwright_translate | likely_open | P1 |
| Brazil Central Bank | BCB | Portuguese/English | bcb.gov.br/en/pressandcommunication/notes | web_scrape | likely_open | P2 |
| IBGE — Statistics | Statistics Institute | Portuguese | ibge.gov.br/explica/inflacao.php | data_api | likely_open | P2 |
| ANP — Oil regulator | Natl Petroleum Agency | Portuguese | anp.gov.br/noticias/ | playwright_translate | likely_open | P2 |

### Regional/South America

| Source | Institution | Language | URL | Tool | Access | Priority |
|--------|-------------|----------|-----|------|--------|----------|
| Chile MFA | Chilean Foreign Affairs | Spanish | minrel.gob.cl/noticias | playwright_translate | likely_open | P2 |
| Banco Central Chile | Chilean Central Bank | Spanish/English | bcentral.cl/en/web/guest/home | web_scrape | likely_open | P2 |
| Argentina MFA | Argentine Foreign Affairs | Spanish | cancilleria.gob.ar/es/noticias | playwright_translate | likely_open | P2 |
| PDVSA — Venezuela | Venezuelan state oil | Spanish | pdvsa.com | web_scrape | unknown | P2 |
| Venezuela MFA | Venezuelan Foreign Affairs | Spanish | mppre.gob.ve | playwright_translate | unknown | P2 |
| ECLAC/CEPAL | UN Econ Commission | English/Spanish | cepal.org/en | web_scrape | 404 (find URL) | P2 |
| OAS | Organization of American States | English/Spanish | oas.org/en/media_center/ | playwright | broken RSS | P2 |

**Venezuela note:** Venezuela holds the world's largest proven oil reserves (heavy crude).
It is currently a strategic chess piece between the US and China. MFA and PDVSA signals
are P2 despite the access uncertainty — worth building toward.

---

## 9 — Africa

**Language:** English (most official African institutions), French (Francophone Africa), Swahili.
**Status:** African Union, South Africa Gov, AllAfrica all confirmed working.

| Source | Institution | Language | URL | Tool | Access | Priority |
|--------|-------------|----------|-----|------|--------|----------|
| African Union | AU | English/French | au.int/en/rss.xml | rss | open ✓ | P1 |
| South Africa Gov | GCIS | English | gov.za/rss.xml | rss | open ✓ | P1 |
| AllAfrica — Top Stories | AllAfrica | English | allafrica.com/tools/headlines/rdf/latest/headlines.rdf | rss | open ✓ | P2 |
| African Dev Bank | AfDB | English/French | afdb.org/en/news | playwright | cloudflare 403 | P2 |
| Nigeria NAN | News Agency of Nigeria | English | nan.ng | web_scrape | unknown | P2 |
| Ghana News Agency | GNA | English | ghananewsagency.org | web_scrape | likely_open | P3 |
| Egypt MENA | Middle East News Agency | Arabic/English | mena.org.eg | web_scrape | unknown | P2 |
| DRC Mining news | Various | French | minesdrc.net | web_scrape | unknown | P3 |

**Notes:**
- AllAfrica is an aggregator covering 130+ African news sources — high breadth, variable depth.
- DRC (Congo) is worth tracking specifically for cobalt and coltan mining dynamics.
  Congo produces ~70% of the world's cobalt. No clean RSS exists; Google News is fallback.

---

## Cross-Regional: Energy Industry

**Why tier-1:** Per `AIMS.md`, energy resources are Layer 0 — the physical substrate
beneath all geopolitical analysis. IEA and OPEC are the two most authoritative sources.

| Source | Institution | Language | URL | Tool | Access | Priority |
|--------|-------------|----------|-----|------|--------|----------|
| IEA — News | Intl Energy Agency | English | iea.org/news | playwright_cloudflare | cloudflare 403 | P1 |
| IEA — Oil Market Report | IEA | English | iea.org/reports/oil-market-report | pdf | cloudflare 403 | P1 |
| OPEC — Press releases | OPEC | English | opec.org/opec_web/en/press_room/24.htm | playwright_cloudflare | cloudflare 403 | P1 |
| OPEC — Monthly Market Report | OPEC | English | opec.org/opec_web/en/publications/338.htm | pdf | cloudflare 403 | P1 |
| Baker Hughes — Rig Count | Baker Hughes | English | bakerhughes.com/company/news/rig-counts | web_scrape | timeout | P1 |
| EIA — Rig Count (via API) | US EIA | English | api.eia.gov/v2/drilling/rigs | data_api | free key | P1 |
| OilPrice.com | OilPrice | English | oilprice.com/rss/main | rss | open ✓ | P2 |
| Reuters — Energy | Reuters | English | reuters.com/business/energy | playwright | paywalled | P2 |
| S&P Global Commodity Insights | S&P | English | spglobal.com/commodityinsights | playwright | paywalled | P3 |
| Wood Mackenzie | Wood Mac | English | woodmac.com/news | playwright | paywalled | P4 |

**Interim fallback for IEA/OPEC:** Google News queries can surface their press releases
without hitting Cloudflare directly. E.g.:
- `"IEA" site:iea.org press release` via Google News RSS
- `"OPEC" press release` via Google News RSS

---

## Cross-Regional: Critical Minerals

| Source | Institution | Language | URL | Tool | Access | Priority |
|--------|-------------|----------|-----|------|--------|----------|
| Mining.com | Mining.com | English | mining.com/feed/ | rss | open ✓ | P1 |
| USGS — Minerals | US Geological Survey | English | usgs.gov/news | rss (have it) | open ✓ | P1 |
| USGS — Mineral Commodity Summaries | USGS | English | usgs.gov/centers/national-minerals-information-center | web_scrape + pdf | open | P1 |
| Mining Weekly | Mining Weekly | English | miningweekly.com/rss | rss | likely_open | P2 |
| Reuters — Metals | Reuters | English | reuters.com/markets/commodities | playwright | paywalled | P2 |
| DRC Mines Ministry | Ministry of Mines, DRC | French | mines.gouv.cd | web_scrape | unknown | P3 |
| Chile Cochilco | Copper Commission Chile | Spanish | cochilco.cl/noticias/ | playwright_translate | likely_open | P2 |
| Lithium Triangle tracker | Bolivia, Chile, Argentina mining news | Spanish | Multiple | Google News | N/A | P2 |

---

## Cross-Regional: International Institutions

| Source | Institution | Language | URL | Tool | Access | Priority |
|--------|-------------|----------|-----|------|--------|----------|
| UN — All News | United Nations | English | news.un.org/feed/subscribe/en/news/all/rss.xml | rss | open ✓ | P1 |
| UN — Security Council | UNSC | English | news.un.org/feed/subscribe/en/news/topic/security-council/rss.xml | rss | returned empty — find correct | P1 |
| WHO — News | World Health Organization | English | who.int/rss-feeds/news-english.xml | rss | open ✓ | P1 |
| IMF — News | IMF | English | imf.org/en/News/rss | rss | returned HTML (JS) — find correct | P1 |
| IMF — WEO Data | IMF | English | imf.org/external/datamapper | data_api | open | P2 |
| World Bank — News | World Bank | English | worldbank.org/en/news/all.rss | rss | 404 — find correct | P2 |
| World Bank — Data API | World Bank | English | api.worldbank.org/v2 | data_api | open (keyless) | P2 |
| NATO — News | NATO | English | nato.int/cps/en/natohq/news.htm | playwright | js_rendered | P1 |
| WTO — News | WTO | English | wto.org/english/news_e/news_e.htm | playwright | js_rendered | P2 |
| BIS Basel — Press | Bank for Intl Settlements | English | bis.org/press/index.htm | playwright | js_rendered | P2 |
| OECD — News | OECD | English | oecd.org/newsroom/ | playwright_cloudflare | cloudflare 403 | P2 |
| G7 — Statements | G7 Presidency | English | g7germany.de or rotating | web_scrape | unknown | P2 |

---

## Cross-Regional: Innovation Signals

| Source | Institution | Language | URL | Tool | Access | Priority |
|--------|-------------|----------|-----|------|--------|----------|
| Hacker News — Best | Y Combinator | English | hnrss.org/best | rss | open ✓ | P1 |
| GitHub Trending | GitHub (unofficial) | English | mshibanami.github.io/GitHubTrendingRSS/daily/all.xml | rss | open ✓ | P1 |
| arXiv — AI (cs.AI) | arXiv | English | rss.arxiv.org/rss/cs.AI | rss | verify (old URL failed) | P1 |
| arXiv — Machine Learning | arXiv | English | rss.arxiv.org/rss/cs.LG | rss | verify | P1 |
| arXiv — Quantum Physics | arXiv | English | rss.arxiv.org/rss/quant-ph | rss | verify | P2 |
| arXiv — Materials Science | arXiv | English | rss.arxiv.org/rss/cond-mat.mtrl-sci | rss | verify | P2 |
| Product Hunt — Daily | Product Hunt | English | producthunt.com/feed | rss | open ✓ | P3 |
| IEEE Spectrum | IEEE | English | spectrum.ieee.org/feeds/feed.rss | rss | have it (disabled) | P2 |
| YC — Company launches | Y Combinator | English | news.ycombinator.com/launches | playwright | js_rendered | P2 |

---

## Build Sequence

### Now — Zero new capability required

All of these use tools we already have (rss, web_scrape, playwright):
- Fix and verify arXiv URLs (`rss.arxiv.org` not `arxiv.org/rss`)
- Kremlin Russian feed (`http://en.kremlin.ru` for English, `kremlin.ru` for Russian)
- UK Gov confirmed — already added
- ECB confirmed — already added
- UN, WHO confirmed — already added
- Try PIB India + MEA India with browser User-Agent (403 may be UA block not Cloudflare)
- Try Japan MFA with Playwright instead of RSS
- Try Taiwan MFA with Playwright

### Phase A — Multilingual pipeline (1-2 days)

- Add `langdetect` to requirements.txt
- Add `language` field to article stub and articles table
- Update Stage 2 prompt: "The article may be in any language. Summarize in English."
- Add `rss_translate` and `playwright_translate` as recognized extractor values in sources.yaml
- Test with Kremlin Russian feed and one Chinese source

### Phase B — Cloudflare bypass (1 week)

- Research: does Playwright with realistic headers + delays bypass Cloudflare for IEA/OPEC?
- If yes: implement stealth mode in browser.py
- If no: implement Google News fallback queries for IEA, OPEC, OECD press releases
- Add `playwright_cloudflare` source type

### Phase C — Data APIs (1-2 weeks)

- Implement `data_api` source type in discovery.py
- Wire in FRED, BLS, EIA, Treasury yield curve (US — free keys needed)
- Wire in World Bank API (keyless)
- Wire in IMF Data API

### Phase D — Deep build (ongoing)

- Chinese government sites (MFA, State Council, MOFCOM) via Playwright + translate
- Russian MFA (Russian language scrape)
- India PIB/MEA if UA fix doesn't work → Playwright
- Japan MFA, BOJ via Playwright + translate
- PDF extraction for IEA/OPEC monthly reports
- South American central banks
- Venezuela PDVSA
