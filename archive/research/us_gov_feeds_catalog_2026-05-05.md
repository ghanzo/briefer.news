# US Government RSS / Atom Feed Catalog

**Compiled:** 2026-05-05 for the Briefer daily intelligence-brief pipeline.
**Scope:** Federal sources only — Executive (cabinet + sub-agencies + indep. regulators + IC + military), Legislative, Judicial, Federal Reserve System, DOE national labs.
**Methodology:** Web research against agency RSS/feeds pages plus common pattern probing (`/rss`, `/feed.xml`, `/news/rss`). URLs marked `(unverified)` are pattern-derived best guesses; the testing phase will probe these. Verified URLs come from official agency RSS index pages or were confirmed in web fetches.

**Relevance flags (Briefer lens):**
- 🔴 HIGH — energy, US-China, financial-stress, security, supply-chain, regulatory shock signals
- 🟡 MEDIUM — general gov context, macro-data, policy actions
- ⚪ LOW — administrative, internal, niche

**Render flags:**
- `[RSS]` plain RSS/Atom feed (curl works)
- `[JS]` page is JS-rendered, may need Playwright
- `[GD]` GovDelivery email-only (no RSS, list for reference)

---

## 1. Executive — Cabinet Departments (not yet covered)

### 1.1 USDA — Agriculture
- ✓ in config: *(none)*
- **NASS — News & Coming Events** — `https://www.nass.usda.gov/Newsroom/rss/news.xml` (unverified) — releases, calendars — daily-weekly — [RSS] — 🔴 HIGH (crop reports move ag commodities)
- **NASS — Today's Reports** — `https://www.nass.usda.gov/Newsroom/rss/todaysreports.xml` (unverified) — major statistical releases — sporadic-monthly — [RSS] — 🔴 HIGH
- **NASS — Executive Briefings (Ag Statistics Board)** — `https://www.nass.usda.gov/Newsroom/Executive_Briefings/` (HTML, RSS unverified) — embargo briefings — monthly — [JS] — 🔴 HIGH
- **WASDE (Office of Chief Economist)** — `https://www.usda.gov/oce/commodity/wasde/rss.xml` (unverified) — World Ag Supply & Demand — monthly — [JS likely] — 🔴 HIGH
- **ERS — Economic Research Service** — `https://www.ers.usda.gov/rss/` (unverified) — outlook reports — weekly-monthly — [RSS] — 🟡 MEDIUM
- **FAS — Foreign Ag Service** — `https://www.fas.usda.gov/feed` (unverified) — export sales, GAIN reports — daily — [RSS] — 🔴 HIGH (China grain flows)
- **USDA Newsroom (top-level)** — `https://www.usda.gov/about-usda/news/feed` (unverified) — press releases — daily — [RSS] — 🟡

### 1.2 Department of Labor (DOL)
- **DOL News Releases** — `https://www.dol.gov/rss/releases.xml` — all DOL press — daily — [RSS] — 🟡 MEDIUM
- **BLS Major Economic Indicators** — `https://www.bls.gov/feed/bls_latest.rss` — CPI/PPI/JOLTS/jobs — weekly — [RSS] — 🔴 HIGH
- **BLS — News Releases (all)** — `https://www.bls.gov/feed/news_release.rss` (unverified) — full list — daily-weekly — [RSS] — 🔴 HIGH
- **BLS — Employment Situation (jobs report)** — `https://www.bls.gov/feed/empsit.rss` (unverified) — monthly — [RSS] — 🔴 HIGH
- **BLS — CPI** — `https://www.bls.gov/feed/cpi.rss` (unverified) — monthly — [RSS] — 🔴 HIGH
- **BLS — PPI** — `https://www.bls.gov/feed/ppi.rss` (unverified) — monthly — [RSS] — 🔴 HIGH
- **OSHA — News Releases** — `https://www.dol.gov/newsroom/releases/osha/feed` (unverified) — weekly — [RSS] — 🟡
- **ETA — Employment & Training** — `https://www.dol.gov/newsroom/releases/eta/feed` (unverified) — weekly initial claims press — weekly — [RSS] — 🟡

### 1.3 Department of Veterans Affairs (VA)
- **VHA Inside Veterans Health** — `https://www.va.gov/health/NewsFeatures/news.xml` — features — weekly — [RSS] — ⚪ LOW
- **VA OIG Reports** — `https://www.va.gov/oig/rss/reports-rss.asp` — IG reports — sporadic — [RSS] — 🟡
- **VA Press Room (news.va.gov)** — `https://news.va.gov/feed/` (unverified, WordPress pattern) — press — daily — [RSS] — 🟡

### 1.4 Department of Education
- **ED Press Releases** — `https://www.ed.gov/news/press-releases/feed` (unverified) — sporadic — [RSS] — ⚪ LOW
- **IES — Institute of Education Sciences** — `https://ies.ed.gov/rss/` (unverified) — research — sporadic — [RSS] — ⚪ LOW

### 1.5 Department of Housing & Urban Development (HUD)
- **HUD Press Releases** — `https://www.hud.gov/press/press_releases_media_advisories/feed` (unverified; canonical index at hud.gov/rss) — daily — [RSS] — 🟡
- **HUD USER (PD&R Research)** — `https://www.huduser.gov/portal/rss/feed.xml` (unverified) — weekly — [RSS] — ⚪ LOW
- **HUD OIG** — `https://hudoig.gov/newsroom/press-releases/feed` (unverified) — sporadic — [RSS] — ⚪ LOW

### 1.6 Department of Transportation (DOT)
- **DOT Newsroom (parent)** — `https://www.transportation.gov/rss/briefing-room` (unverified; index at transportation.gov/rss) — daily — [RSS] — 🟡
- **FAA News** — `https://www.faa.gov/news/rss` (unverified) — daily — [RSS] — 🟡 MEDIUM (aviation safety)
- **NHTSA Press Releases** — `https://www.nhtsa.gov/press-releases/feed` (unverified) — daily — [RSS] — 🟡
- **NHTSA — Vehicle Recalls (ODI)** — `https://www-odi.nhtsa.dot.gov/RSS/index.cfm` — daily-weekly — [RSS] — 🟡
- **FRA — Federal Railroad Admin** — `https://railroads.dot.gov/rss` (unverified) — sporadic — [RSS] — ⚪
- **FMCSA — Motor Carrier Safety** — `https://www.fmcsa.dot.gov/newsroom/rss` — sporadic — [RSS] — ⚪
- **FHWA — Federal Highway** — `https://www.fhwa.dot.gov/rss/index.htm` — sporadic — [RSS] — ⚪
- **MARAD — Maritime** — `https://www.maritime.dot.gov/rss` (unverified) — sporadic — [RSS] — 🟡 (port/supply-chain)
- **FTA — Federal Transit** — `https://www.transit.dot.gov/rss` (unverified) — sporadic — [RSS] — ⚪
- **PHMSA — Pipeline & Hazmat** — `https://www.phmsa.dot.gov/news/rss` (unverified) — sporadic — [RSS] — 🔴 HIGH (energy infra)

### 1.7 Department of the Interior
- **DOI Press Releases** — `https://www.doi.gov/news/feed` (unverified) — daily — [RSS] — 🟡
- **BLM RSS Feeds (index)** — `https://www.blm.gov/info/RSS-feeds` — multiple sub-feeds — daily — [RSS] — 🟡 (energy leasing)
- **NPS — Park News** — `https://www.nps.gov/orgs/news/feed.xml` (unverified) — daily — [RSS] — ⚪
- **FWS — Fish & Wildlife** — `https://www.fws.gov/news/feed` (unverified) — daily — [RSS] — ⚪
- **BIA — Indian Affairs** — `https://www.bia.gov/news/feed` (unverified) — sporadic — [RSS] — ⚪
- **BOEM — Ocean Energy Mgmt** — `https://www.boem.gov/newsroom/feed` (unverified) — sporadic — [RSS] — 🔴 HIGH (offshore leasing)
- **BSEE — Safety & Environmental Enforcement** — `https://www.bsee.gov/newsroom/feed` (unverified) — sporadic — [RSS] — 🟡

### 1.8 Department of Homeland Security (DHS)
- **DHS Press Releases** — `https://www.dhs.gov/news-releases/press-releases/feed` (unverified) — daily — [RSS] — 🔴 HIGH
- **TSA News** — `https://www.tsa.gov/news/rss` (unverified) — sporadic — [RSS] — 🟡
- **CBP News (top-level)** — `https://www.cbp.gov/rss.xml` — daily — [RSS] — 🔴 HIGH (trade/immigration)
- **CBP Newsroom — Media Releases** — `https://www.cbp.gov/newsroom/media-releases/all/feed` (unverified) — daily — [RSS] — 🔴
- **ICE Press Releases** — `https://www.ice.gov/news/feed` (unverified) — daily — [RSS] — 🟡
- **USCIS News** — `https://www.uscis.gov/news/rss` (unverified) — sporadic — [RSS] — 🟡
- **FEMA — Disaster Declarations** — `https://www.fema.gov/news/disasters_rss.fema` — daily-sporadic — [RSS] — 🔴 HIGH
- **FEMA — Press Releases** — `https://www.fema.gov/media-library/assets/rss.xml/rss.xml` — daily — [RSS] — 🟡
- **USCG News** — `https://www.news.uscg.mil/RSS/Headlines.aspx` (unverified path; index at news.uscg.mil/RSS/) — daily — [RSS] — 🟡

### 1.9 DOJ Sub-agencies (not yet covered)
- **DOJ Justice News (OPA)** — `https://www.justice.gov/news/rss?m=1` — daily — [RSS] — 🟡
- **DOJ — All US Attorneys** — `https://www.justice.gov/usao/rss` (parent index; sub-feeds per USAO) — daily — [RSS] — 🟡
- **DOJ — Antitrust Division** — `https://www.justice.gov/atr/news-feeds` — daily — [RSS] — 🔴 HIGH (M&A blocks)
- **FBI National Press Releases** — `https://www.fbi.gov/feeds/national-press-releases/RSS` — daily — [RSS] — 🔴 HIGH
- **FBI Top Stories** — `https://www.fbi.gov/feeds/fbi-top-stories/RSS` — daily — [RSS] — 🟡
- **FBI Congressional Testimony** — `https://www.fbi.gov/feeds/congressional-testimony/RSS` — sporadic — [RSS] — 🟡
- **DEA Press Releases** — `https://www.dea.gov/press-releases/feed` (unverified) — daily — [RSS] — 🟡
- **ATF Press Releases** — `https://www.atf.gov/news/press-releases/feed` (unverified) — daily — [RSS] — ⚪
- **USMS — US Marshals** — `https://www.usmarshals.gov/news/feed` (unverified) — sporadic — [RSS] — ⚪
- **BOP — Bureau of Prisons** — `https://www.bop.gov/resources/news/feed` (unverified) — sporadic — [RSS] — ⚪

### 1.10 Treasury Sub-agencies (not yet covered)
- **IRS Newsroom** — `https://www.irs.gov/newsroom/feed` (unverified; canonical at irs.gov/downloads/rss) — daily — [RSS] — 🟡
- **FinCEN News** — `https://www.fincen.gov/news/news-releases/feed` (unverified) — weekly — [RSS] — 🔴 HIGH (sanctions/AML)
- **TTB News & Events** — `https://www.ttb.gov/templates/ttb/news/ttb.xml` — weekly — [RSS] — ⚪
- **Treasury Press Releases (top-level)** — `https://home.treasury.gov/news/press-releases/feed` (unverified) — daily — [RSS] — 🔴 HIGH

### 1.11 Commerce Sub-agencies (not yet covered)
- **BEA — Bureau of Economic Analysis** — `https://apps.bea.gov/rss/rss.xml` — GDP, trade, PCE — weekly — [RSS] — 🔴 HIGH
- **Census Bureau News** — `https://www.census.gov/about/contact-us/feeds/news.xml` (unverified; index at census.gov/about/contact-us/feeds.html) — daily — [RSS] — 🟡
- **USPTO — PTAB Alert Notifications** — `https://developer.uspto.gov/ptab-feed/notifications.rss` — daily — [RSS] — ⚪ (note: retiring 2026-02-27, ODP replacement)
- **USPTO News & Updates** — `https://www.uspto.gov/about-us/news-updates/feed` (unverified) — sporadic — [RSS] — ⚪
- **ITA — International Trade Admin** — `https://www.trade.gov/rss/news.xml` (unverified) — sporadic — [RSS] — 🔴 HIGH (tariffs/CFIUS-adjacent)
- **NTIA** — already in config (broken SSL) — note that telecom policy releases also flow through Federal Register

### 1.12 DoD — Branches & Sub-Components (not yet covered)
- **DoD News — Releases** — `https://www.war.gov/News/Releases/feed` (unverified; index at war.gov/News/RSS/) — daily — [RSS] — 🔴 HIGH
- **DoD News — Transcripts** — `https://www.war.gov/News/Transcripts/feed` (unverified) — daily — [RSS] — 🟡
- **DoD News — Contracts** — `https://www.war.gov/News/Contracts/feed` (unverified) — daily — [RSS] — 🟡 (defense $)
- **Army News** — `https://www.army.mil/rss/` (unverified) — daily — [RSS] — 🟡
- **Navy News** — `https://www.navy.mil/Resources/Rss-Feeds/` (index page) — daily — [RSS] — 🟡
- **Air Force News** — `https://www.af.mil/News/RSS/` (unverified) — daily — [RSS] — 🟡
- **Marine Corps News** — `https://www.marines.mil/RSS/` (index) — daily — [RSS] — 🟡
- **Space Force News** — `https://www.spaceforce.mil/News/feed` (unverified) — sporadic-daily — [RSS] — 🔴 HIGH (China space)
- **Space Systems Command** — `https://www.ssc.spaceforce.mil/RSS` (index) — sporadic — [RSS] — 🔴 HIGH
- **DCSA — Defense Counterintelligence & Security Agency** — `https://www.dcsa.mil/news/feed` (unverified) — sporadic — [RSS] — 🟡
- **DTRA — Defense Threat Reduction Agency** — `https://www.dtra.mil/News/feed` (unverified) — sporadic — [RSS] — 🔴 HIGH (CBRN)
- **NSA Press Room** — `https://www.nsa.gov/Press-Room/Press-Releases-Statements/feed` (unverified — NSA generally lacks RSS, may need [JS] scraper) — sporadic — 🔴 HIGH

### 1.13 State Dept Sub-bureaus (only those with RSS likely)
Most State sub-bureau pages do not expose dedicated RSS — current State coverage in config (regional desks + briefings) captures the bulk. Worth probing:
- **DRL — Democracy, Human Rights, Labor** — `https://www.state.gov/bureaus-offices/under-secretary-for-civilian-security-democracy-and-human-rights/bureau-of-democracy-human-rights-and-labor/feed/` (unverified) — sporadic — [RSS] — 🟡
- **OES — Oceans, Environment, Science** — same pattern (unverified) — sporadic — 🟡

### 1.14 HHS Sub-agencies (not yet covered)
- **CMS Newsroom** — `https://www.cms.gov/newsroom/rss` (unverified; sample feed exists at cms.gov/rss/31836) — daily-weekly — [RSS] — 🔴 HIGH (Medicare/Medicaid policy moves markets)
- **CMS Internet-Only Manuals** — `https://www.cms.gov/rss/31836` — sporadic — [RSS] — 🟡
- **SAMHSA News** — `https://www.samhsa.gov/news/feed` (unverified) — sporadic — [RSS] — ⚪
- **HRSA News** — `https://www.hrsa.gov/about/news/feed` (unverified) — sporadic — [RSS] — ⚪
- **AHRQ News** — `https://www.ahrq.gov/news/rss.xml` (unverified) — weekly — [RSS] — ⚪
- **ACL — Admin for Community Living** — `https://acl.gov/news-and-events/feed` (unverified) — sporadic — [RSS] — ⚪

### 1.15 DOE Program Offices (not yet covered)
- **EERE — Energy Efficiency & Renewable Energy** — `https://www.energy.gov/eere/rss.xml` (unverified) — weekly — [RSS] — 🔴 HIGH
- **FECM — Fossil Energy & Carbon Mgmt** — `https://www.energy.gov/fecm/rss.xml` (unverified) — weekly — [RSS] — 🔴 HIGH
- **FE — Fossil Energy (legacy)** — sometimes redirects to FECM
- **NETL — National Energy Tech Lab** — `https://netl.doe.gov/rss/news.xml` (unverified) — weekly — [RSS] — 🔴 HIGH

### 1.16 DOE National Labs
| Lab | Likely RSS URL | Cadence | Render | Flag |
|---|---|---|---|---|
| **ORNL** Oak Ridge | `https://www.ornl.gov/news/feed` (unverified — index at ornl.gov/content/rss-feeds) | weekly | [RSS] | 🔴 |
| **LBNL** Lawrence Berkeley | `https://newscenter.lbl.gov/feed/` (WordPress) | weekly | [RSS] | 🔴 |
| **LLNL** Lawrence Livermore | `https://www.llnl.gov/news/feed` (unverified) | weekly | [RSS] | 🔴 (fusion/NIF) |
| **ANL** Argonne | `https://www.anl.gov/feed/news` (unverified) | weekly | [RSS] | 🔴 |
| **PNNL** Pacific Northwest | `https://www.pnnl.gov/news/feed` (unverified) | weekly | [RSS] | 🔴 |
| **INL** Idaho | `https://inl.gov/feed/` (unverified) | weekly | [RSS] | 🔴 (advanced reactors) |
| **SLAC** | `https://www6.slac.stanford.edu/news/feed` (unverified) | weekly | [RSS] | 🟡 |
| **FNAL** Fermilab | `https://news.fnal.gov/feed/` (WordPress) | weekly | [RSS] | 🟡 |
| **BNL** Brookhaven | `https://www.bnl.gov/newsroom/news.rss` (unverified) | weekly | [RSS] | 🟡 |
| **LANL** Los Alamos | `https://www.lanl.gov/discover/news-release/feed` (unverified) | weekly | [RSS] | 🔴 (national security) |
| **NREL** Renewable Energy | `https://www.nrel.gov/news/rss.xml` (unverified) | weekly | [RSS] | 🔴 |
| **SNL** Sandia | `https://newsreleases.sandia.gov/feed/` (unverified) | weekly | [RSS] | 🔴 |
| **PPPL** Princeton Plasma | `https://www.pppl.gov/news/feed` (unverified) | sporadic | [RSS] | 🟡 |
| **JLab** Jefferson | `https://www.jlab.org/news/feed` (unverified) | sporadic | [RSS] | ⚪ |
| **AMES** Ames | `https://www.ameslab.gov/news/feed` (unverified) | sporadic | [RSS] | 🟡 (rare earths) |
| **NETL** | listed above |

---

## 2. Independent Regulators / Agencies (not yet covered)

| Agency | Feed URL | Content | Cadence | Flag |
|---|---|---|---|---|
| **SSA** | `https://www.ssa.gov/news/press/releases/rss.xml` (unverified) | press | weekly | 🟡 |
| **SSA OIG** | `https://oig.ssa.gov/rss/` (index) | OIG reports | weekly | ⚪ |
| **SBA** | `https://www.sba.gov/about-sba/sba-newsroom/press-releases-media-advisories/feed` (unverified) | press | weekly | ⚪ |
| **OPM** | `https://www.opm.gov/rss/` (unverified) | personnel mgmt | sporadic | ⚪ |
| **GSA** | `https://www.gsa.gov/about-us/newsroom/rss-feeds` (index — sub-feeds for releases, speeches) | press | weekly | ⚪ |
| **NTSB** | `https://www.ntsb.gov/Pages/RSS.aspx` (index — accident, news, safety alerts) | safety | weekly | 🟡 |
| **CFPB** | `https://www.consumerfinance.gov/about-us/newsroom/feed/` (unverified — WordPress) | press | weekly | 🔴 HIGH |
| **PBGC** | `https://www.pbgc.gov/news/rss` (unverified) | sporadic | sporadic | 🟡 (pension stress) |
| **EXIM Bank** | `https://www.exim.gov/news/feed` (unverified) | sporadic | sporadic | 🟡 |
| **FMSHRC** Mine Safety Review | `https://www.fmshrc.gov/feed` (unverified) | rulings | sporadic | ⚪ |
| **NLRB Press Releases** | `https://www.nlrb.gov/rss/rssPressReleases.xml` | press | weekly | 🟡 |
| **NLRB Weekly Summaries** | `https://www.nlrb.gov/rss/rssWeeklySummaries.xml` | decisions | weekly | 🟡 |
| **NLRB Announcements** | `https://www.nlrb.gov/rss/rssAnnouncements.xml` | sporadic | sporadic | ⚪ |
| **National Mediation Board** | `https://www.nmb.gov/rss` (unverified) | sporadic | sporadic | ⚪ |
| **EEOC** | `https://www.eeoc.gov/newsroom/feed` (unverified) | press | weekly | ⚪ |
| **NARA — National Archives** | `https://www.archives.gov/news/rss` (unverified) | sporadic | sporadic | ⚪ |
| **Smithsonian Insider** | `https://insider.si.edu/feed/` (WordPress) | research | weekly | ⚪ |
| **Library of Congress** | `https://www.loc.gov/rss/` (index — multiple feeds) | press, blogs, In Custodia Legis | daily | 🟡 |
| **GPO** (beyond Fed Register) | feeds via `govinfo.gov/feeds` (see §5) | varied | varied | 🟡 |

---

## 3. Intelligence Community

| Agency | Feed | Notes | Flag |
|---|---|---|---|
| **ODNI** | `https://www.dni.gov/index.php/rss` (index — press, speeches) | sporadic | 🔴 HIGH |
| **CIA** | `https://www.cia.gov/news-information/rss` (unverified — historically limited) | sporadic / [JS] likely | 🔴 |
| **NSA / CSS** | No native RSS confirmed; use `https://www.nsa.gov/Press-Room/Press-Releases-Statements/` via [JS] scraper | sporadic | 🔴 |
| **DIA** | `https://www.dia.mil/News-Features/feed` (unverified) | sporadic / [JS] likely | 🔴 |
| **NRO** | `https://www.nro.gov/News-Press-Releases/feed` (unverified) | sporadic / [JS] likely | 🔴 |

---

## 4. Federal Reserve System — Regional Banks

Federal Reserve **Board of Governors** is already in config. The 12 regional banks below add deep research/speech coverage. Fed Board master list lives at `federalreserve.gov/feeds/feeds.htm` (already partly used). Cross-bank index: `https://www.fedinprint.org/rss`.

| Bank | Top RSS / index | Flag |
|---|---|---|
| **NY Fed** — Liberty Street Economics | `https://libertystreeteconomics.newyorkfed.org/feed/` (WordPress) | 🔴 HIGH |
| **NY Fed** — Press / speeches | `https://www.newyorkfed.org/rss/` (unverified — sub-feeds for press, speeches, EPR) | 🔴 |
| **NY Fed** — Economic Policy Review | `https://www.newyorkfed.org/medialibrary/media/research/rss/feeds/epr.xml` | 🟡 |
| **Boston Fed** | `https://www.bostonfed.org/feeds.aspx` (index) | 🟡 |
| **Philadelphia Fed** | `https://www.philadelphiafed.org/rss` (unverified) | 🟡 |
| **Cleveland Fed** | `https://www.clevelandfed.org/news-and-events/rss` (unverified) | 🔴 (inflation nowcast, financial stress) |
| **Richmond Fed** | `https://www.richmondfed.org/press_room/rss` (unverified) | 🟡 |
| **Atlanta Fed** | `https://www.atlantafed.org/RSS` (index — GDPNow, Macroblog, speeches) | 🔴 (GDPNow!) |
| **Chicago Fed** | `https://www.chicagofed.org/rss` (index — NFCI, speeches, blogs) | 🔴 (NFCI = financial stress) |
| **St. Louis Fed** | `https://www.stlouisfed.org/rss` (index); research at `https://research.stlouisfed.org/rss/` | 🔴 (FRED announcements) |
| **Minneapolis Fed** | `https://www.minneapolisfed.org/feeds` (unverified) | 🟡 |
| **Kansas City Fed** | `https://www.kansascityfed.org/about-us/rss/` (index) | 🟡 |
| **Dallas Fed** | `https://www.dallasfed.org/rss/` (index) | 🔴 (Texas energy, oil-state surveys) |
| **San Francisco Fed** | `https://www.frbsf.org/feed/` (unverified; subscriptions page at frbsf.org/subscriptions) | 🟡 |

---

## 5. Legislative Branch

### 5.1 GovInfo (verified — primary federal-publishing index)
`https://www.govinfo.gov/feeds`
- **Congressional Bills (new)** — `https://www.govinfo.gov/rss/bills.xml` — daily — 🔴
- **Bills Enrolled** — `https://www.govinfo.gov/rss/bills-enr.xml` — sporadic — 🔴
- **Public & Private Laws** — `https://www.govinfo.gov/rss/plaw.xml` — sporadic — 🔴
- **Congressional Hearings** — `https://www.govinfo.gov/rss/chrg.xml` — daily — 🟡
- **Congressional Reports** — `https://www.govinfo.gov/rss/crpt.xml` — weekly — 🟡
- **Congressional Record** — `https://www.govinfo.gov/rss/crec.xml` — daily — 🟡
- **Compilation of Presidential Documents** — `https://www.govinfo.gov/rss/dcpd.xml` — weekly — 🟡
- **GAO Reports / Comptroller Decisions** — `https://www.govinfo.gov/rss/gaoreports.xml` — weekly — 🟡 (you have GAO already; this is the parallel feed)
- **Federal Register** — `https://www.govinfo.gov/rss/fr.xml` — daily — 🟡
- **CFR** — `https://www.govinfo.gov/rss/cfr.xml` — sporadic — ⚪
- **Economic Indicators** — `https://www.govinfo.gov/rss/econi.xml` — monthly — 🟡

### 5.2 Congress.gov
- **Most-Viewed Bills** — `https://www.congress.gov/rss/most-viewed-bills.xml` (unverified) — daily — 🟡
- **Bills Presented to the President** — `https://www.congress.gov/rss/presented-to-president.xml` (unverified) — sporadic — 🔴
- **House Floor Today** — `https://www.congress.gov/rss/house-floor-today.xml` (unverified) — daily — 🟡
- **Senate Floor Today** — `https://www.congress.gov/rss/senate-floor-today.xml` (unverified) — daily — 🟡
- **In Custodia Legis (LOC blog)** — `https://blogs.loc.gov/law/feed/` — weekly — ⚪

### 5.3 CBO
- **CBO Publications** — `https://www.cbo.gov/publications/all/rss.xml` (unverified — accessible via "Stay Connected" footer) — weekly — 🔴 HIGH (budget scoring)

### 5.4 CRS — Congressional Research Service
CRS does not publish a public RSS. Reports are only accessible via congress.gov/crs-reports (no feed). [JS] scrape of `https://crsreports.congress.gov/` would be required if needed.

### 5.5 Committees with notable RSS (mostly need [JS] / probing)
Most House/Senate committees do NOT expose RSS by default; some use Drupal which auto-emits `?_format=rss`.
- **Senate Armed Services** — `https://www.armed-services.senate.gov/press-releases?_format=rss` (unverified) — sporadic — 🔴
- **Senate Foreign Relations** — `https://www.foreign.senate.gov/press/?_format=rss` (unverified) — sporadic — 🔴
- **Senate Select Intelligence** — `https://www.intelligence.senate.gov/press/?_format=rss` (unverified) — sporadic — 🔴
- **Senate Banking** — `https://www.banking.senate.gov/newsroom?_format=rss` (unverified) — sporadic — 🔴
- **Senate Finance** — `https://www.finance.senate.gov/chairmans-news?_format=rss` (unverified) — sporadic — 🔴
- **Senate Energy & Natural Resources** — `https://www.energy.senate.gov/press-releases?_format=rss` (unverified) — sporadic — 🔴
- **Senate Appropriations** — `https://www.appropriations.senate.gov/news/?_format=rss` (unverified) — sporadic — 🟡
- **House Armed Services** — `https://armedservices.house.gov/press-releases?_format=rss` (unverified) — sporadic — 🔴
- **House Foreign Affairs** — `https://foreignaffairs.house.gov/news?_format=rss` (unverified) — sporadic — 🔴
- **House Permanent Select Intelligence** — `https://intelligence.house.gov/news?_format=rss` (unverified) — sporadic — 🔴
- **House Financial Services** — `https://financialservices.house.gov/news/?_format=rss` (unverified) — sporadic — 🔴
- **House Judiciary** — `https://judiciary.house.gov/news/?_format=rss` (unverified) — sporadic — 🟡
- **House Energy & Commerce** — `https://energycommerce.house.gov/news?_format=rss` (unverified) — sporadic — 🔴

---

## 6. Judicial Branch

- **US Courts (top-level)** — `https://www.uscourts.gov/rss-feeds` (index) — sporadic — 🟡
- **Supreme Court — Opinions** — *no native RSS*. Closest: `https://www.supremecourt.gov/rss/orders.aspx` (unverified — historical existence). Reliable third-party: Cornell LII at `https://www.law.cornell.edu/supct/cert/RSS_Opinions_Bulletin.xml`. — sporadic — 🔴 HIGH
- **GovInfo — US Reports (SCOTUS official volumes)** — `https://www.govinfo.gov/rss/usreports.xml` — annual — ⚪
- **GovInfo — Courts of Appeals** (one feed per circuit, CA1–CA13 + CADC) — `https://www.govinfo.gov/rss/uscourts-ca[N].xml` patterns — daily — 🟡 (DC Circuit + 9th = highest-signal)
- **Court of International Trade** — `https://www.govinfo.gov/rss/uscourts-cit.xml` — sporadic — 🔴 (tariff rulings)
- **Court of Federal Claims** — `https://www.govinfo.gov/rss/uscourts-cofc.xml` — sporadic — 🟡
- **Judicial Panel on Multidistrict Litigation** — `https://www.govinfo.gov/rss/uscourts-jpml.xml` — sporadic — 🟡

---

## 7. Aggregators & Cross-Cutting Sources

- **Federal Register (govinfo)** — `https://www.govinfo.gov/rss/fr.xml` (already have specific subset feeds via Federal Register API; this is the consolidated)
- **Federal Register — Public Inspection** — `https://www.federalregister.gov/api/v1/public-inspection-documents.rss` (unverified path) — daily — 🔴 HIGH (next-day rules)
- **whitehouse.gov briefing room** — already in config
- **usa.gov press feed** — `https://www.usa.gov/feed/press-releases` (unverified) — sporadic — ⚪
- **GPO daily Federal Register summary** — `https://www.govinfo.gov/rss/fr-bulkdata.xml` — daily — 🟡
- **data.gov RSS index** — `https://catalog.data.gov/feeds/dataset.atom` (unverified) — daily — ⚪ (mostly admin/dataset adds)
- **Recalls.gov** — composite of NHTSA, CPSC, FDA, USDA-FSIS — `https://www.recalls.gov/rss.html` (HTML index) — daily — 🟡 (FSIS food recalls especially)
- **CPSC — Consumer Product Safety Commission** — `https://www.cpsc.gov/Newsroom/News-Releases/feed` (unverified) — daily — 🟡 (consumer recalls — overlaps recalls.gov)
- **USDA FSIS Food Recalls** — `https://www.fsis.usda.gov/recalls-alerts/feed` (unverified) — sporadic — 🟡

---

## 8. Top recommendations for first-pass test (highest-value additions, ranked)

These are the 15 feeds I'd add to the next test pass — heavy on macro signals, supply-chain stressors, and security ledgers, biased toward already-verified or well-known feeds to keep the testing yield high.

1. **BLS Major Economic Indicators** — `https://www.bls.gov/feed/bls_latest.rss` — jobs/CPI/PPI moves the entire macro picture. 🔴
2. **BEA Releases** — `https://apps.bea.gov/rss/rss.xml` — GDP, trade, PCE inflation. 🔴
3. **GovInfo — Congressional Bills** — `https://www.govinfo.gov/rss/bills.xml` — every introduced bill, daily. 🔴
4. **NY Fed Liberty Street Economics** — `https://libertystreeteconomics.newyorkfed.org/feed/` — top-tier macro/financial-stress research. 🔴
5. **Atlanta Fed RSS index → GDPNow** — `https://www.atlantafed.org/RSS` — real-time GDP nowcast. 🔴
6. **Chicago Fed RSS index → NFCI** — `https://www.chicagofed.org/rss` — National Financial Conditions Index, the canonical financial-stress series. 🔴
7. **DOJ Antitrust news** — `https://www.justice.gov/atr/news-feeds` — merger challenges, China-tech enforcement. 🔴
8. **FBI National Press Releases** — `https://www.fbi.gov/feeds/national-press-releases/RSS` — espionage cases, sanctions arrests. 🔴
9. **CBP top-level RSS** — `https://www.cbp.gov/rss.xml` — trade enforcement, border, UFLPA. 🔴
10. **FEMA Disaster Declarations** — `https://www.fema.gov/news/disasters_rss.fema` — disaster signals (insurance, supply-chain). 🔴
11. **DOL News Releases** — `https://www.dol.gov/rss/releases.xml` — initial claims press, wage decisions. 🟡→🔴 on jobs days
12. **CBO Publications** — `https://www.cbo.gov/publications/all/rss.xml` — fiscal scoring of major bills. 🔴
13. **GovInfo — Courts of Appeals (DC Circuit + 9th)** — `https://www.govinfo.gov/rss/uscourts-cadc.xml` and `uscourts-ca9.xml` — regulatory/admin-law rulings. 🔴
14. **DoD Contracts feed** — `https://www.war.gov/News/Contracts/feed` (unverified) — defense spending pulse. 🟡→🔴 for primes
15. **ODNI press** — `https://www.dni.gov/index.php/rss` — official IC posture, threat assessments. 🔴

**Honourable mentions (probe second-pass):**
- LBNL `newscenter.lbl.gov/feed/` and ORNL — energy R&D pipeline.
- CFPB newsroom — financial-services rulemaking.
- ITA — tariff/trade actions outside Federal Register.
- Liberty Street + St. Louis FRED Announcements together = Fed-research duo.
- USDA NASS Today's Reports — when Briefer needs commodity-aware coverage.

---

### Notes on probing strategy
- Most modern federal sites (.gov) running Drupal expose `?_format=rss` on listing pages — worth automating that test across the unverified URLs above.
- Many sites quietly dropped RSS in 2024-2025 (CISA's KEV/cyber alerts being a notable example — now GovDelivery email only). Expect 15-25% attrition on first probe.
- DoD, IC, and SCOTUS sites tend to be JS-rendered or use ASP.NET-style routes — flag for Playwright in the testing harness.
- For agencies without RSS, GovDelivery email subscriptions can be parsed via a dedicated mailbox rule (last-resort fallback for FBI-tier critical sources).
