# Sources Matrix — Regional Coverage

> Living document. Update when sources are added, confirmed, or deprecated.
> Last updated: Feb 2026.
>
> Rating scale:
> ★★★★★ Excellent — comprehensive, high-signal, current
> ★★★★  Good      — solid coverage, minor gaps
> ★★★   Adequate  — functional but notable gaps
> ★★    Weak      — sparse or indirect only
> ★     Minimal   — token coverage
> ○     None      — no sources at all

---

## Coverage Heatmap (quick reference)

| Region          | Geopolitics | Finance | Technology | Health | Climate/Eco | Overall |
|-----------------|-------------|---------|------------|--------|-------------|---------|
| United States   | ★★★★★      | ★★★★   | ★★★★      | ★★★★  | ★★★        | ★★★★   |
| Europe          | ★          | ○       | ○          | ○      | ○           | ★       |
| China           | ○          | ○       | ○          | ○      | ○           | ○       |
| Russia          | ○          | ○       | ○          | ○      | ○           | ○       |
| Middle East     | ★          | ○       | ○          | ○      | ○           | ★       |
| Asia (non-CN)   | ○          | ○       | ○          | ○      | ○           | ○       |
| India           | ○          | ○       | ○          | ○      | ○           | ○       |
| Africa          | ○          | ○       | ○          | ○      | ○           | ○       |
| South America   | ○          | ○       | ○          | ○      | ○           | ○       |

**Honest summary:** We have excellent US government coverage and almost nothing else.
The product currently reflects the US government's worldview by default — not independent
global analysis. This is the most important structural limitation to fix.

---

## United States

### Active Sources

| Source | Type | Lens | Signal Value |
|--------|------|------|-------------|
| State Dept (22 feeds) | RSS | Geopolitics, diplomacy, all regions | ★★★★★ |
| White House (3 web_scrape) | web_scrape | Executive actions, policy | ★★★★★ |
| Department of Defense | RSS | Military, security | ★★★★ |
| DARPA / ARPA-E | RSS | Defense tech, energy R&D | ★★★★ |
| Federal Reserve (speeches + PR) | RSS | Monetary policy, financial stability | ★★★★★ |
| U.S. Treasury | RSS | Fiscal policy, financial regulation | ★★★★ |
| OFAC | RSS | Sanctions, asset freezes | ★★★★★ |
| SEC | RSS | Markets, enforcement, disclosure | ★★★★ |
| CFTC | RSS | Derivatives, market oversight | ★★★ |
| FDIC / OCC | RSS | Banking system stability | ★★★★ |
| BLS | RSS | Employment, CPI, PPI data releases | ★★★★★ |
| USTR | RSS | Trade policy, tariffs | ★★★★ |
| BIS (export controls) | RSS | Semiconductor/tech export controls | ★★★★★ |
| FTC | RSS | Antitrust, consumer protection | ★★★ |
| Federal Register (EO + Rules) | RSS | Regulatory changes, executive orders | ★★★★ |
| DOJ — National Security | RSS | Espionage, enforcement, indictments | ★★★★ |
| CISA | RSS | Cybersecurity threats, advisories | ★★★★ |
| GAO | RSS | Government accountability, audits | ★★★ |
| FCC | Fed Register RSS | Telecom, spectrum policy | ★★★ |
| FERC | Fed Register RSS | Energy grid, pipeline regulation | ★★★★ |
| EIA (Today + Natural Gas) | RSS | Energy production, prices, forecasts | ★★★★★ |
| DOE Newsroom | web_scrape | Energy policy, R&D | ★★★★ |
| NRC | RSS | Nuclear safety, licensing | ★★★ |
| IAEA | RSS | International nuclear | ★★★★ |
| NASA | RSS | Space, Earth observation | ★★★ |
| NOAA | RSS | Climate, weather, oceans | ★★★★ |
| EPA | RSS | Environment, pollution, climate | ★★★ |
| NIH | RSS | Medical research, funding | ★★★★ |
| CDC | RSS | Public health, disease | ★★★★ |
| FDA (press + drugs + devices) | RSS | Drug approvals, safety, devices | ★★★★ |
| HHS | Fed Register RSS | Health policy, ACA, CMS | ★★★ |
| USGS | RSS | Geology, minerals, natural hazards | ★★★ |
| NSF / NIST | RSS | Science policy, standards, AI | ★★★ |
| Commerce Dept | Fed Register RSS | Trade, tech policy coordination | ★★★ |
| NTIA | RSS | Broadband, internet governance | ★★★ |

### US Coverage Rating: ★★★★

**Strong:** Financial regulation, geopolitics (US perspective), executive actions,
monetary policy, energy data, public health.

**Gaps:**
- No economic data APIs yet (FRED, BLS API, EIA API, Treasury yields) — planned in PLAN_PROCESSING.md
- Social cohesion signals thin (no Supreme Court, DOJ civil rights, EEOC)
- No direct corporate/private sector signals (SEC filings are a proxy)
- Ecosystem/climate underweight relative to its stated priority in lens.md
- USDA missing — food prices, crop reports, agriculture are commodity/security signals

---

## China

### Active Sources

| Source | Type | Lens | Signal Value |
|--------|------|------|-------------|
| *(none active)* | — | — | ○ |

*Xinhua, People's Daily, Global Times, CGTN, China Daily all disabled — RSS feeds went stale
(last entries 2017-2018). Coverage of China currently comes entirely from US government
framing (State Dept, OFAC, BIS) — which is antagonistic by nature.*

### China Coverage Rating: ○

**This is the most critical gap in the entire source list.**
The lens identifies US-China as the defining geopolitical axis. We hear only one side.

**Recommended additions:**

| Source | Type | Why | Status |
|--------|------|-----|--------|
| MFA China — English press briefings | web_scrape | Primary source for Chinese foreign policy positions | Not built |
| Xinhua — English wire | web_scrape or API | Official Chinese state narrative on all topics | RSS stale; needs scraper |
| State Council — announcements | web_scrape | Economic policy, regulatory changes | Not built |
| MOFCOM — trade/commerce news | web_scrape | Trade policy, tariffs, investment rules | Not built |
| NDRC — economic planning | web_scrape | Five-year plan updates, economic targets | Not built |
| People's Bank of China | web_scrape | Monetary policy, RMB management | Not built |
| CSRC — securities regulator | web_scrape | Chinese market regulation | Not built |

**Note on source use:** Chinese state media is propaganda by design, but it remains the
primary signal for what Beijing *wants the world to think it is doing*. The gap between
official statements and observed behavior is itself analytically meaningful.
Read as signal, not as truth.

---

## Europe

### Active Sources

| Source | Type | Lens | Signal Value |
|--------|------|------|-------------|
| BBC World (disabled tier-2) | RSS | Broad news | — |
| Reuters World (disabled tier-2) | RSS | Broad news | — |

*All EU institutional sources missing. No ECB, European Commission, NATO, EU Parliament,
Council of Europe, or national government sources.*

### Europe Coverage Rating: ★ (indirect only, via disabled tier-2)

Europe is the second-largest gap. The EU is a major regulatory and geopolitical actor —
the AI Act, GDPR, digital markets regulation, ECB policy, and NATO all have direct
implications for the lens themes.

**Recommended additions:**

| Source | Type | Why | Status |
|--------|------|-----|--------|
| European Commission — Press releases | RSS | EU policy, regulation, trade | RSS available |
| ECB — Press releases | RSS | Eurozone monetary policy; global financial stability | RSS available |
| ECB — Economic Bulletin | RSS | Deeper macro analysis | RSS available |
| NATO — News & Press | RSS | Alliance posture, defense coordination | RSS available |
| European Parliament — News | RSS | Legislative process, geopolitics | RSS available |
| Council of the EU — Press | RSS | Member state decisions | RSS available |
| UK Government (gov.uk) | RSS | Post-Brexit policy, defense | RSS available |
| Eurostat — Key indicators | data_api | EU-wide economic statistics | API available |
| OSCE — News | RSS | Eastern Europe, conflict monitoring | RSS available |

---

## Russia

### Active Sources

| Source | Type | Lens | Signal Value |
|--------|------|------|-------------|
| *(none)* | — | — | ○ |

### Russia Coverage Rating: ○

Russia is a major actor on energy markets, European security, and the broader contest
between authoritarian and democratic governance models. Zero direct sources means
Russia only appears in our data as seen through US government statements (OFAC sanctions,
State Dept press briefings, DOJ indictments).

**Recommended additions:**

| Source | Type | Why | Status |
|--------|------|-----|--------|
| Kremlin.ru — English | RSS | Primary source for Kremlin signaling and framing | RSS available |
| MFA Russia — English | RSS | Foreign policy positions | RSS available |
| TASS — English | RSS | State wire service; broadest official coverage | RSS available |
| Central Bank of Russia | web_scrape | Monetary policy, sanctions response, ruble | Not built |

**Note:** Russian state sources must be read as deliberate narrative management.
Value is in tracking *what Russia claims*, *what Russia signals*, and the
*gap between claim and action* — not in taking statements at face value.

---

## Middle East

### Active Sources

| Source | Type | Lens | Signal Value |
|--------|------|------|-------------|
| State Dept — Near East | RSS | US policy toward region | ★★★ (US framing only) |
| Al Jazeera World (disabled) | RSS | Regional perspective | — |

### Middle East Coverage Rating: ★

The region is geopolitically critical: energy supply, Iran nuclear program, Israel-Gaza,
Gulf state normalization, and US military posture. Currently only heard through the US
State Dept Near East bureau — a single, antagonist perspective.

**Recommended additions:**

| Source | Type | Why | Status |
|--------|------|-----|--------|
| Al Jazeera — World (enable tier-2) | RSS | Best English-language regional perspective | Disabled, ready |
| Saudi Press Agency (SPA) | RSS | Gulf policy, OPEC+ signaling, Saudi official positions | RSS available |
| Israel MFA | RSS | Israeli foreign policy, security statements | RSS available |
| UAE — WAM News Agency | RSS | Gulf economic and diplomatic signals | RSS available |
| Iran — IRNA (English) | web_scrape | Iranian state positions on nuclear, regional | Limited RSS |
| Arab League | RSS/web_scrape | Pan-Arab institutional positions | Sparse |
| Gulf Cooperation Council | web_scrape | Gulf economic integration, policy | Not built |

---

## Asia (Non-China)

### Active Sources

| Source | Type | Lens | Signal Value |
|--------|------|------|-------------|
| *(none direct)* | — | — | ○ |

*Japan, South Korea, Southeast Asia, Singapore, Indonesia — all absent. These are critical
actors in semiconductor supply chains, US alliance architecture, and regional economic
integration.*

### Asia (Non-China) Coverage Rating: ○

**Recommended additions:**

| Source | Type | Why | Status |
|--------|------|-----|--------|
| Japan MFA | RSS | Japan-US alliance, China stance, regional security | RSS available |
| Japan Cabinet Office | RSS | Domestic policy, economic strategy | RSS available |
| Bank of Japan | RSS | Monetary policy; yen movements affect global finance | RSS available |
| South Korea MFA | RSS | Peninsula security, semiconductor policy | RSS available |
| Singapore PM Office | RSS | Belt & Road, ASEAN posture, financial hub signals | RSS available |
| MAS Singapore | RSS | Financial regulation, digital assets | RSS available |
| ASEAN Secretariat | web_scrape | Regional integration, South China Sea | Not built |
| Taiwan MFA / Government | RSS | Cross-strait tensions; primary flashpoint source | RSS available |

**Taiwan specifically:** Given that Taiwan is the most likely near-term geopolitical
flashpoint on the lens's US-China axis, having no Taiwanese government source at all
is a meaningful gap.

---

## India

### Active Sources

| Source | Type | Lens | Signal Value |
|--------|------|------|-------------|
| *(none)* | — | — | ○ |

### India Coverage Rating: ○

India is the world's most populous country, a major tech and pharmaceutical power,
the center of a contested border dispute with China, and a key non-aligned swing state
in the US-China competition. Completely absent from our data.

**Recommended additions:**

| Source | Type | Why | Status |
|--------|------|-----|--------|
| PIB India (Press Information Bureau) | RSS | Official government announcements | RSS available |
| MEA India (Ministry of External Affairs) | RSS | Foreign policy, China/Pakistan/US relations | RSS available |
| Reserve Bank of India | RSS | Monetary policy, financial stability | RSS available |
| SEBI | RSS | Securities regulation | RSS available |

---

## Africa

### Active Sources

| Source | Type | Lens | Signal Value |
|--------|------|------|-------------|
| *(none)* | — | — | ○ |

### Africa Coverage Rating: ○

Africa is relevant to critical minerals supply chains (cobalt, lithium, rare earths),
Chinese Belt & Road investment, food security, and demographic trends (the continent
holds 60% of global arable land and will be home to 40% of humanity by 2100).

**Recommended additions:**

| Source | Type | Why | Status |
|--------|------|-----|--------|
| African Union — News | RSS/web_scrape | Pan-continental policy, peace & security | RSS sparse |
| African Development Bank | RSS | Economic development signals, Chinese debt | RSS available |
| South Africa Government | RSS | Regional power, BRICS member | RSS available |
| Nigeria — NAN (state wire) | RSS | Most populous African nation | RSS available |

**Note:** RSS landscape is genuinely sparse for Africa. Google News topic feeds
(critical minerals, African development, China Africa) are likely the most practical
near-term coverage expansion.

---

## South America

### Active Sources

| Source | Type | Lens | Signal Value |
|--------|------|------|-------------|
| *(none)* | — | — | ○ |

### South America Coverage Rating: ○

Relevant primarily for: critical minerals (lithium triangle — Chile, Argentina, Bolivia),
Amazon deforestation, food supply, Chinese investment, and US policy in the hemisphere.

**Recommended additions:**

| Source | Type | Why | Status |
|--------|------|-----|--------|
| Agência Brasil (Brazilian gov wire) | RSS | Brazil — largest economy, Amazon policy | RSS available |
| ECLAC/CEPAL (UN Econ Commission) | RSS | Economic data and analysis | RSS available |
| OAS (Organization of American States) | RSS | Hemispheric security, democracy | RSS available |
| Brazil Central Bank | web_scrape | Monetary policy, BRL movements | Not built |
| Mercosur Secretariat | web_scrape | Trade bloc integration | Sparse |

---

## International Institutions (Cross-Regional)

These transcend any single region but are critical for the "systemic stability" lens.
Currently all absent or disabled.

| Source | Type | Lens | Priority | Status |
|--------|------|------|----------|--------|
| IMF — News & Press | RSS | Global financial stability, debt crises | High | Disabled (tier-3) |
| World Bank — News | RSS | Development, sovereign debt, poverty signals | Medium | Disabled (tier-3) |
| UN — News | RSS | Geopolitical order, conflict, institutions | High | Not added |
| NATO — News | RSS | Alliance posture, European security | High | Not added |
| WTO — News | RSS | Trade rules, dispute settlement | Medium | Not added |
| BIS (Basel) — Press | RSS | International banking stability | High | Not added |
| OECD — News | RSS | Advanced economy policy coordination | Medium | Not added |
| WHO — News | RSS | Global health emergencies | High | Not added |
| IPCC | RSS/web_scrape | Climate science updates, reports | Medium | Not added |

**Note:** IMF and World Bank are in sources.yaml as disabled tier-3. Both should be
promoted to tier-1 and enabled — they are primary sources, not analysis.

---

## Data Sources (Economic Indicators)

Currently absent. Planned in PLAN_PROCESSING.md as `data_api` type (not yet implemented).

| Source | Type | What it provides | Key series | Status |
|--------|------|-----------------|------------|--------|
| FRED (St. Louis Fed) | data_api | US macro time series | Fed funds rate, CPI, yield curve, unemployment | API key needed |
| BLS API | data_api | US employment/price data | CPI-U, PPI, JOLTS, NFP | Free (v1 keyless) |
| EIA API | data_api | US energy data | WTI price, gas supply, storage levels | Free key |
| Treasury Yield Curve | data_api | Daily yield rates (XML) | 2yr, 10yr, spread | Keyless, confirmed |
| ECB Data Portal | data_api | Eurozone rates, inflation | EURIBOR, HICP | Free API |
| World Bank API | data_api | Global development indicators | GDP, debt/GDP, gini | Free API |
| IMF Data API | data_api | Global macro | WEO forecasts, reserves | Free API |
| USDA NASS / ERS | RSS + data_api | Agriculture data | Crop estimates, food prices | Free API |

---

## Phased Build-Out Recommendation

### Phase A — Quick wins (RSS sources, <1 day)
Enable/add: IMF, World Bank, UN, NATO, WHO, ECB, European Commission,
Japan MFA, Taiwan MFA, Saudi Press Agency, Al Jazeera (enable tier-2)

### Phase B — Moderate effort (web_scrape, <1 week)
China MFA, Xinhua, Kremlin, ASEAN, Israel MFA, UAE WAM, PIB India

### Phase C — Data infrastructure (requires data_api type in pipeline)
FRED, BLS API, EIA API, Treasury yields, ECB Data, USDA

### Phase D — Deep regional (research + build)
Full Chinese government suite, Russian central bank, African sources,
South American central banks, Belt & Road tracking
