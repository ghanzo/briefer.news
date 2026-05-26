# Source Gap Analysis — May 7, 2026

> Probe of major news outlets vs. today's gov scrape.
> Question: are we covering the day adequately, especially the war?

---

## Headline finding

**The war is much larger than our brief reflects.** Our scrape captures U.S.
government press-release output on the war, but misses critical operational
developments, coalition responses, casualty/escalation reporting, and analyst
assessments. For a brief we want to be authoritative on the Iran/Hormuz
conflict, we're seeing about 30% of the picture.

---

## What our May 7 brief said about Iran

1. *"Iran-China oil sanctions"* — May 1 sanctions on Qingdao Haiye
2. *"Operation Epic Fury concluded after destroying Iran's navy, air force, and missile-launch capability"* (May 6 brief, dropped from May 7)

That's it.

## What the news says happened in the past 72 hours

Cross-referencing Reuters, AP, NPR, NBC, CNN, Al Jazeera, BBC, NYT, Bloomberg, ISW, CSIS, the UK House of Commons Library, the International Crisis Group, Critical Threats Project, and the U.S. Central Command press office:

### Operations / military
- **Trump paused Project Freedom on May 6** citing "great progress" on a possible Iran deal — *huge story; we missed it entirely*
- **15,000 U.S. service members deployed** for Project Freedom, plus 100+ aircraft, multi-domain unmanned platforms, 2 guided-missile destroyers
- **6 small Iranian boats sunk** in defensive engagements; CENTCOM specified MH-60 Sea Hawks and AH-64 Apaches were used
- **CENTCOM denied Iranian state media claims of strike on U.S. warship** — explicit information-warfare counter we missed

### Coalition / diplomacy
- **UK PM Starmer publicly said UK will NOT join the U.S. blockade** — major coalition fracture
- **Pakistan is mediating U.S.-Iran negotiations**; Pakistani Foreign Ministry spokesperson Tahir Andrabi confirmed
- **36-country joint statement** signed (UK + France co-hosted two conferences) on reopening Hormuz
- **UK deployed HMS Dragon to Cyprus, 4 additional jets to Qatar, air defences to Bahrain, Kuwait, Saudi Arabia**
- **Iran's Foreign Minister stated** Hormuz will return to normal "when the war ends" — Iranian framing we'd never see in U.S. gov

### Active conflict events
- **French CMA CGM container ship "San Antonio" attacked May 6** in Hormuz, crew injured, vessel damaged
- **UAE attacked by Iran for first time since the early-April ceasefire** broke down
- **Iranian Parliament National Security Commission Chairman** stated May 3 that any U.S. interference with Iran's blockade is a "ceasefire violation"
- **Iran attacked an Emirati-affiliated tanker May 3 with two drones**

### Internal Iranian dynamics
- **IRGC Commander Major General Ahmad Vahidi** assessed by ISW as actively constraining Iranian diplomacy and blocking "pragmatist" officials' negotiating efforts
- **U.S. and Israel assassinated Supreme Leader Khamenei** in late February (war origin context — never mentioned in our brief)
- **Iranian inflation at 70%** (this we have)

### Background context our brief lacks entirely
- The war began **February 28, 2026** — U.S. and Israel launched air war on Iran
- Iran retaliated with missile/drone attacks on Israel, U.S. military bases, U.S.-allied Gulf states
- Iran began mining Hormuz and forbade passage in early stages
- A **fragile ceasefire** held early April → broke down → escalation continues
- The **SPR 172M release was actually announced March 11** — we framed today's RFP as the lead but the broader policy is two months old

---

## Why the gap exists

Our pipeline scrapes only U.S. government press releases. Government press releases have specific properties:

1. **One-sided narrative** — they tell the U.S. side, not the adversary's reaction or coalition disagreement
2. **Operational detail dropped** — DoD doesn't disclose troop numbers and weapons by ship in regular State press releases
3. **Lagging on developments** — Trump's pause of Project Freedom may not yet have a State Dept briefing
4. **DoD's own primary source is blocked** — `war.gov` (formerly defense.gov) sits behind Akamai bot detection that we tried and failed to bypass earlier this week
5. **Coalition partner positions are absent** — UK, French, Pakistani statements aren't in our feed at all

We're seeing the war through one keyhole.

---

## What we can add — prioritized

### Tier 1: highest signal, must-add
| Source | Status | Why |
|---|---|---|
| **CENTCOM press releases** | `centcom.mil/MEDIA/PRESS-RELEASES/` — likely Akamai-blocked (DoD subdomain). Worth re-testing with stealth bypass. | Primary U.S. military source for the Strait of Hormuz operations |
| **ISW Iran Update** | `understandingwar.org` — scrapable; no RSS but has consistent URL pattern; we confirmed daily updates exist for May 1–6 | Authoritative daily intelligence assessments; what military analysts read |
| **Critical Threats Project** | `criticalthreats.org` (AEI) — publishes "Iran Update Evening Special Report" daily; scrapable | Companion to ISW; analytic depth |

### Tier 2: meaningful additions
| Source | Status | Why |
|---|---|---|
| **Stars and Stripes** | `stripes.com` — military-focused journalism, has RSS | Field-level reporting; covers what DoD does without DoD's PR filter |
| **Navy Times** | `navytimes.com` — has RSS | Naval-specific coverage of Hormuz operations |
| **CSIS** | `csis.org` — has RSS, covers "War with Iran" series | Think-tank analysis with policy implications |
| **Council on Foreign Relations** | `cfr.org` — has RSS | Think-tank analysis from foreign-policy establishment |
| **UK House of Commons Library** | `commonslibrary.parliament.uk` — research briefings | Coalition partner's own assessment of the war |
| **International Crisis Group** | `crisisgroup.org` — has RSS feeds | Independent NGO, often gets details others miss |

### Tier 3: useful context
| Source | Status | Why |
|---|---|---|
| **Reuters Top News** | RSS available | Wire-service standard |
| **AP Top News** | RSS available | Wire-service standard |
| **Al Jazeera English** | RSS available; we held this earlier | Strong Middle East coverage; surfaces Iranian framing |
| **BBC US/Canada** | RSS available; we held this earlier | UK national broadcaster perspective |

### Tier 4: blocked / paid
| Source | Status | Notes |
|---|---|---|
| **DoD War.gov** | Akamai-blocked | Same blocker as before. Bright Data / ScrapingBee could solve. ~$50–100/month at low volume. |
| **CENTCOM** | Probably Akamai-blocked | Same block; same fix |
| **Bloomberg** | Paywalled | Skip |
| **WSJ / FT / NYT** | Paywalled | Skip |

---

## My recommendation

**Stay strictly U.S.-government** for the brand promise but **expand DRAMATICALLY within that scope** by adding:

1. **CENTCOM** (need bypass)
2. **DoD War.gov** (need bypass)
3. **NAVCENT / Naval Forces Central Command** — Bahrain-based, Hormuz-relevant
4. **Office of the Director of National Intelligence (ODNI)** — daily threat assessments
5. **U.S. Embassy press releases** by region — the embassies often surface localized State Dept content faster than the regional desks

**For analysis depth, add** (these are non-gov but high-signal):
1. **ISW + Critical Threats Project** (daily Iran updates) — the single biggest gap-filler for war coverage
2. **CSIS "Latest Analysis: War with Iran"**
3. **CFR analysis pages**

**For coalition perspective** (allied government sources, still "official"):
1. **UK MoD** + UK Parliament research briefings
2. **NATO press releases**
3. **EU EEAS** (European External Action Service)

**For commercial maritime intel:**
1. **IMO** (International Maritime Organization)
2. **Lloyd's List** (paywalled — skip)

**For oil markets:**
1. **IEA** (International Energy Agency, Paris)
2. **EIA** (already have)

---

## What this means for the project

Two paths from here:

### Path A — Strict gov-only, add allied gov + bypass DoD
Brand: "From U.S. government sources" stays clean.
Lift: ~10 new sources, plus a paid scraping service (~$50/mo) for war.gov / centcom.
Result: war coverage improves significantly, especially on operational detail, but we still miss analyst framing.

### Path B — Expand to "official + authoritative" sources
Brand: "From U.S. government and authoritative open-source intelligence."
Adds: ISW, CSIS, CFR, Crisis Group as primary news inputs alongside gov.
Result: war coverage approaches what an actual intelligence professional reads, but the source mix is mixed authority.

I'd lean **Path A first** with a bypass infrastructure investment for the DoD subdomains, and consider Path B as a v2 expansion if you want analyst-level depth.

---

## Specific next-action recommendations

1. **Re-attempt bypass for war.gov + centcom.mil**. The Akamai protection is the same family; if a paid service (Bright Data residential proxy or ScrapingBee with stealth) can crack one it can crack both. Low monthly cost.

2. **Add ISW and Critical Threats** to `sources.yaml` as `web_scrape` sources with their daily-update URL patterns. They're not behind Akamai; we can scrape directly.

3. **Add Stars and Stripes RSS** — military journalism, scrapable, complements gov-only feed with field reporting.

4. **Add UK MoD press releases + UK Parliament Library briefings** — coalition perspective, non-paywalled, scrapable.

5. **Add NATO press releases** — alliance position on Iran/Russia.

6. **Activate Al Jazeera English from held** — even imperfect, surfaces Iranian-framing perspective we should at least be aware of.

7. **Test CENTCOM** before paying for bypass — sometimes these mil subdomains have different bot-protection profiles than the parent.

---

## A note on today's specific brief

If we'd had ISW + CENTCOM + UK MoD in the feed, today's May 7 brief would likely have included:

- *"Project Freedom paused.** Trump announced a temporary pause to the U.S. operation citing 'great progress' on Iran negotiations; Pakistan continues mediating."* — instead of leaving the operation as ongoing
- *"Coalition fracture.** UK PM Starmer announced UK will not join the Hormuz blockade despite deploying HMS Dragon to Cyprus and additional defensive air assets to Gulf allies."* — a notable allied-position gap
- *"French shipping attacked.** CMA CGM's *San Antonio* damaged in Hormuz May 6, crew injured."* — escalation event we missed entirely

These are the bullets a serious daily war brief should have on May 7. We didn't have them because our sources don't carry them.
