# Briefer — Coverage Scope

This document defines **what Briefer tracks and why**. Every source decision,
category label, and AI prompt should be anchored to the dimensions below.

The goal is not comprehensive news — it is a daily signal map for a reader
trying to understand which forces are reshaping the world at a civilizational
scale.

---

## Thematic Dimensions

### 1. Geopolitics & Power Structure
*The board the game is played on.*

What we track:
- US-China axis: trade war, chip war, Taiwan, South China Sea, tech decoupling
- Alliances shifting: NATO, BRICS expansion, Gulf states hedging, Africa pivot
- Sanctions and export controls as geopolitical weapons
- Espionage, cyber operations, influence campaigns
- UN, WTO, IMF as contested arenas
- Regional conflicts and their resource/migration implications

Primary sources: State Dept all feeds, White House, DoD, OFAC, DOJ National
Security, Chinese state media (Xinhua, People's Daily, CGTN, Global Times,
China Daily), Al Jazeera, Reuters World, BBC World, AP

---

### 2. AI & Technological Acceleration
*The speed of change in the tools of power.*

What we track:
- Foundation model releases and capability jumps (reasoning, agents, multimodal)
- AI applied to biology, chemistry, materials science, warfare
- Semiconductor supply chain: TSMC, ASML, Nvidia, Intel, SMIC
- Export controls on chips and AI models
- Robotics and physical AI (Boston Dynamics, Figure, Tesla Optimus)
- Quantum computing milestones
- Open-source vs. closed-source AI dynamics
- AI governance: EU AI Act, executive orders, international frameworks
- AGI timelines and safety debates

Primary sources: DARPA, IEEE Spectrum, MIT Technology Review, Ars Technica,
The Verge, Wired, arXiv (cs.AI), Google News topic feeds

---

### 3. Energy
*The constraint layer underneath everything else.*

What we track:
- **Nuclear fission**: plant openings/closures, SMR development, NRC decisions,
  global nuclear posture, nonproliferation
- **Fusion**: ITER, Commonwealth Fusion, NIF, milestone announcements
- **Solar & renewables**: cost curves, grid integration, storage breakthroughs,
  geopolitical dependencies (China's solar supply chain dominance)
- **Oil & gas**: OPEC+ decisions, strategic reserves, pipeline geopolitics,
  LNG as leverage (Russia-Europe, US-Asia)
- **Dwindling resources**: peak demand projections, resource nationalism,
  energy poverty
- **Grid infrastructure**: blackouts, resilience, electrification pace
- Energy as geopolitical weapon: sanctions on Russian energy, Iranian oil,
  Venezuela

Primary sources: EIA, DOE, NRC, IAEA, Google News topic feeds

---

### 4. Materials, Mining & Refining
*The physical substrate of technological civilization.*

What we track:
- Critical minerals: lithium, cobalt, nickel, manganese (battery supply chain)
- Rare earth elements: Chinese dominance, US/Australian alternatives
- Copper: electrification demand, mine output, Chile/Peru/DRC dynamics
- Semiconductor materials: silicon, germanium, gallium (China export controls)
- Refining chokepoints: who controls processing, not just mining
- Deep-sea mining developments and regulatory fights
- Resource nationalism and mine nationalization events
- US/EU critical mineral strategies and stockpiling

Primary sources: USGS, Google News topic feeds, Reuters Commodities

---

### 5. Ecosystem Health
*The biological life-support system.*

What we track:
- **Ocean health**: dead zones, acidification, coral bleaching, sea temperature
- **Fish stocks**: global fishery collapse indicators, IUU fishing, aquaculture
- **Wildlife & biodiversity**: species loss rates, habitat destruction, rewilding
- **Biomass & soil**: forest loss, agricultural soil degradation, carbon stocks
- **Pollution**: microplastics, forever chemicals (PFAS), heavy metals,
  air quality, water contamination
- **Pollution cleanup**: remediation tech, Superfund, international cleanup efforts
- **Invasive species** and ecosystem disruption

Primary sources: NOAA, EPA, WWF, Google News topic feeds, Nature/Science journals

---

### 6. Climate & Weather
*Not the politics — the physical signals and their downstream effects.*

What we track:
- Extreme weather events and their frequency/intensity trends
- **Migration drivers**: drought, flooding, crop failure, heat — not the politics
  but the physical forcing that moves people
- **Food security**: crop yields, price spikes, supply chain shocks
- **Water**: aquifer depletion, river system stress, water wars
- Arctic dynamics: ice loss, northern sea routes, Arctic sovereignty
- IPCC reports and climate data milestones
- Wildfire scope and economic damage

Note: Briefer is not a climate advocacy platform. Climate is tracked as a
driver of geopolitics, migration, resource competition, and ecosystem stress —
not as a political issue.

Primary sources: NOAA, WMO, IPCC, NASA Earth, Google News topic feeds

---

### 7. Social, Cultural & Civilizational
*How humans are reorganizing themselves — the emerging order.*

What we track:
- **Finance & macro**: Fed policy, dollar hegemony, de-dollarization moves,
  stablecoin/crypto as parallel financial rails, debt dynamics
- **Network states & governance innovation**: charter cities, startup societies,
  digital nations, DAOs as coordination experiments
- **Platform & social tech**: how AI and platforms reshape attention, identity,
  and political organization
- **Culture wars as signal**: not the content of culture wars but what they
  reveal about underlying social stress and reorganization
- **Social evolution**: changing family formation, fertility trends, urbanization,
  remote work, post-institutional trust
- **Longevity & health innovation**: not clinical trials but paradigm-level
  shifts (GLP-1, senolytics, longevity biomarkers)
- **Demographic shifts**: aging societies, immigration dynamics, population
  decline in key countries

Primary sources: Federal Reserve speeches, IMF, World Bank, Google News topic
feeds, Hacker News, The Atlantic, Axios

---

## Category Labels (used in sources.yaml and AI prompts)

| Label        | Covers                                              |
|-------------|------------------------------------------------------|
| geopolitics  | Power, conflict, diplomacy, sanctions, alliances     |
| technology   | AI, semiconductors, robotics, cyber, quantum         |
| energy       | Nuclear, fusion, solar, oil/gas, grid, EV            |
| materials    | Critical minerals, rare earths, mining, refining     |
| ecosystem    | Ocean, fish, wildlife, biomass, pollution, cleanup   |
| climate      | Weather events, migration drivers, food, water, fire |
| social       | Finance, network states, culture, demographics, tech |
| health       | Public health, longevity, innovation (macro-level)   |
| science      | Breakthrough science that crosses multiple dimensions |
| finance      | Markets, macro, dollar, central banks, trade         |

---

## Scraping Strategy by Source Type

### Type A: RSS with full content:encoded (best)
Government sites like state.gov embed full article HTML in the RSS feed's
`content:encoded` field. **Do not fetch the article URL** — it is JS-rendered
and returns boilerplate. Extract directly from the RSS entry.

Applies to: all state.gov feeds, whitehouse.gov, some DOE/NRC feeds

### Type B: RSS with stub + URL fetch
Standard RSS with title/summary only. Must fetch article URL to get full text.
Use trafilatura first, BeautifulSoup fallback.

Applies to: Reuters, BBC, Ars Technica, The Verge, most tier-2 sources

### Type C: Google News RSS redirect
Google News RSS URLs return redirect links (googlenews.com/articles/...).
Must resolve redirect via HTTP HEAD to get canonical URL, then fetch.

Applies to: all google_news type sources

### Type D: Federal Register / structured data
Federal Register articles are deeply structured. Title + summary often
sufficient; full text via URL fetch when needed.

### Type E: Social/aggregator (future)
Hacker News, Reddit, X — requires API or custom scraper. Not yet implemented.

---

## What We Deliberately Exclude

- Daily crime, celebrity, sports, entertainment
- Climate policy advocacy (covered as geopolitics only)
- Individual company earnings (unless systemic signal)
- Retail politics / election horse-race coverage
- Pure opinion / punditry without factual news hook
- Anything behind a hard paywall with no RSS fallback

---

## Signal Hierarchy for AI Prioritization

When Claude scores article importance, it should weight by:

1. **Systemic stability signals** — anything that could destabilize a major
   government, financial system, or military alliance
2. **Phase transitions** — tech breakthroughs, policy pivots, ecosystem
   tipping points that are hard to reverse
3. **US-China axis moves** — any action by either power that reveals strategy
4. **Resource chokepoints** — control or disruption of critical supply chains
5. **Long-run demographic/ecological forcing** — slower signals that compound

Low weight: daily market moves, routine statements, incremental policy tweaks

---

*Last updated: 2026-02-21*
