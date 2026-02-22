# Briefer — Aims, Interpretive Framework & Predictions

> This document defines what the product is trying to do and why.
> It is the source of truth for editorial decisions: what to prioritize,
> how to interpret events, and what outputs to produce.
>
> It works alongside `lens.md` (which gives the interpretive stance)
> and `PLAN_PROCESSING.md` (which describes the technical pipeline).
> Last updated: Feb 2026.

---

## Part 1 — What We Are Trying to Understand

Briefer is not a news aggregator. It is an intelligence tool for people who want to
understand the world as a system — not to consume more information, but to develop
better models of how things work and where they are heading.

### The core question behind every briefing

**What is the state of civilization today, and which direction is it moving?**

This decomposes into five persistent questions, revisited every day:

---

### Q1 — Is the system stable?

Large complex systems (financial markets, international order, ecological balance,
democratic institutions) can fail suddenly after long periods of apparent stability.
The early warning signals are often visible before the failure — if you know what to
look for.

We are tracking:
- **Financial stress:** Are credit markets, sovereign debt, currency markets, or banking
  systems showing stress? Early indicators: inverted yield curves, rising credit default
  swap spreads, central bank emergency actions, bank failures, capital controls.
- **Geopolitical fracturing:** Are the institutions that manage interstate conflict
  (UN, NATO, WTO, international courts) functioning, degraded, or being bypassed?
  Are agreements being honored or violated?
- **Ecological thresholds:** Are climate systems approaching or crossing tipping points?
  Are food, water, or biodiversity systems under acute stress?
- **Social cohesion:** Are democratic institutions, rule of law, and civil society
  strengthening or weakening? What is the quality of governance in major powers?

**Output type:** Stability signals — short weekly or daily indicators showing
which systems look stable vs. stressed.

---

### Q2 — Where is power moving?

Power shifts slowly and then all at once. The daily news captures the "all at once"
moments but misses the slow shifts. We want to track both.

We are tracking:
- **US-China power balance:** Who is winning the technology competition?
  Who is building more alliances? Who is more economically resilient?
  Where is decoupling accelerating vs. stalling?
- **Energy power:** Who controls critical energy infrastructure?
  How is the transition from fossil fuels to clean energy redistributing
  geopolitical leverage?
- **Financial power:** Is the dollar's reserve currency status weakening?
  Which central banks are accumulating gold? Who is building alternative
  payment systems?
- **Technology power:** Who controls the key chokepoints in AI, semiconductors,
  biotech, and quantum? Export controls and supply chain decisions are power moves.
- **Demographic power:** Which countries are growing, aging, or declining?
  Demography is a slow-moving but deterministic force.

**Output type:** Power flow narratives — weekly synthesis of which actors
gained or lost leverage.

---

### Q3 — What is accelerating?

Certain forces compound — they get faster, not slower. Understanding what is
accelerating (and what is decelerating) is how you anticipate the next decade.

We are tracking:
- **AI capability:** Model releases, benchmark improvements, deployment at scale,
  regulatory responses. The rate of change matters more than any individual event.
- **Energy transition:** Solar/wind/battery cost curves, grid infrastructure investment,
  EV adoption. Non-linear adoption means the transition happens faster than forecasts.
- **Biotech:** Gene editing, synthetic biology, longevity research, pandemic
  preparedness. Dual-use risk accelerates alongside benefit.
- **Weaponization of technology:** Drones, autonomous systems, AI-enabled ISR,
  cyberweapons. Technology asymmetry reshapes deterrence.
- **Surveillance and control:** State and corporate surveillance infrastructure
  expanding in ways that shift the power balance between institutions and individuals.

**Output type:** Acceleration tracker — which technologies/trends moved faster or
slower this week than the prior trend suggested.

---

### Q4 — What is the world signaling about the next 6-24 months?

Some events are noise. Some are leading indicators of something coming.
The job is to distinguish between them.

Leading indicators we watch for:
- **Policy changes** that take 6-18 months to flow through to visible effects
  (rate decisions → housing market; export controls → supply chain realignment;
  farm bill changes → food prices 18 months later)
- **Diplomatic positioning** ahead of negotiations, elections, or military actions
- **Regulatory enforcement waves** that signal a shift in political economy
- **Infrastructure investment patterns** that reveal 10-year strategic priorities
- **Corporate and government procurement** as a leading indicator of where
  technology and industrial capacity is being directed

**Output type:** Leading indicator alerts — events flagged specifically because
they predict something in 6-24 months, not because they are important today.

---

### Q5 — What are we consistently wrong about?

Most news interpretation assumes continuity — that tomorrow will look like today.
The most consequential events are discontinuities.

We want to track:
- **Narrative consensus and where it might be wrong** — what does everyone assume
  that hasn't been stress-tested recently?
- **Black swan precursors** — events that don't fit the dominant model but should
  not be dismissed; accumulate them
- **Reversals** — where a trend that looked durable reversed; why; what it implies

**Output type:** Contrarian flags — periodic challenge to the current dominant
narrative in each major theme area.

---

## Part 2 — The Interpretive Framework

### The five lenses (in priority order)

These are defined in detail in `lens.md`. Summary:

1. **Systemic stability** — Is the global system holding or cracking?
2. **US-China axis** — The defining contest of the era; shapes everything else
3. **Technological acceleration** — Tech is changing faster than governance can adapt
4. **Economic and financial currents** — Money flows reveal power; track the data
5. **Scientific and environmental signals** — Long-term signals that shape the century

When two stories compete for prominence in the briefing, the higher lens wins.
A Federal Reserve emergency rate cut (Lens 1 + Lens 4) outranks an AI model release
(Lens 3) which outranks a routine diplomatic communiqué (Lens 2, low signal).

### How to read sources

**Government sources** — primary value is in what they *do*, not what they *say*.
A regulatory action, an indictment, a sanctions designation, a trade restriction —
these are acts with real-world consequences. Press releases often spin; the
underlying action is the signal.

**State media** (Xinhua, TASS, Kremlin, Saudi SPA) — read as deliberate narrative
management. Value is in: (a) what the government wants the world to believe,
(b) the gap between the claim and observed behavior, (c) shifts in tone that
signal internal change.

**Economic data** (FRED, BLS, EIA, Treasury) — primary signal, not interpretation.
A yield curve inversion or a CPI surprise is a fact. The story is what it implies.
Data should be tracked as time series, not one-off events.

**Research and analysis** (IMF, OECD, Brookings, RAND) — useful for framing and
long-term context but already filtered through an institutional lens. Use for
calibration, not as primary signal.

### What good interpretation looks like

The meta story is an answer to: **What is the world saying today?**

Not: "Here are the things that happened."
But: "Here is what today reveals about the underlying forces at work."

Good interpretations:
- Name the force, not just the event ("Beijing is accelerating capital outflow
  restrictions, which typically precedes a devaluation" vs. "China took new
  currency measures")
- Connect events across categories ("The same week the Fed held rates, Treasury
  yield spreads widened and two regional banks reported deposit outflows —
  the market is not believing the Fed's stable narrative")
- Note when the consensus is probably wrong ("The dominant view is X; three
  data points this week challenge that")
- Flag leading indicators explicitly ("This is not a big story today, but it
  suggests Y in 6-12 months")

---

## Part 3 — Predictions We Want to Make

The product has two modes: **descriptive** (what happened and why) and
**predictive** (what is likely to happen next). The predictive layer is
what makes the product genuinely useful vs. any other news summary.

### Prediction types

**Type 1 — Policy trajectory predictions**
"Given current trajectory, the Fed will cut in Q3 2026 unless employment data
reverses in the next two releases."
Source: FRED, BLS, Fed speeches, market pricing
Horizon: 3-6 months
Confidence threshold: only publish if evidence is consistent across 3+ indicators

**Type 2 — Geopolitical flashpoint probability**
"Taiwan Strait tension is elevated; probability of an incident in the next 90 days
is higher than baseline."
Source: US DoD posture changes, China MFA rhetoric shifts, semiconductor export
control escalations, naval movements (via DoD/State Dept signals)
Horizon: 30-90 days
Expressed as: directional (elevated/reduced/baseline), not numerical probability

**Type 3 — Regulatory/enforcement waves**
"SEC enforcement against crypto custody is accelerating — expect 3-5 major actions
in the next 60 days based on current pipeline signals."
Source: SEC press releases, Federal Register proposed rules, GAO reports, DOJ
coordination signals
Horizon: 30-90 days
Confidence threshold: requires enforcement action + proposed rulemaking signal

**Type 4 — Technology milestone proximity**
"Based on rate of model capability improvement and announced timelines, AGI-adjacent
system demonstrations are likely in 2026-2027."
Source: Research announcements, compute procurement signals, regulatory urgency signals
Horizon: 6-24 months
Expressed as: ranges with explicit uncertainty

**Type 5 — Economic leading indicators**
"Yield curve inversion + declining JOLTS openings + weakening PMI is the pattern
that has preceded recession 8 of the last 9 times this combination appeared."
Source: FRED, BLS, ISM (to add), Treasury
Horizon: 6-18 months
Expressed as: "pattern X is present; historically associated with outcome Y"

**Type 6 — Supply chain disruption signals**
"Taiwanese export restrictions on advanced packaging + Chinese gallium/germanium
export controls = semiconductor supply tightening in 6-12 months."
Source: BIS export control actions, USGS mineral supply data, EIA energy disruptions
Horizon: 3-12 months

### What predictions are NOT

- Not point forecasts ("the S&P will be at X by Y")
- Not recommendations to buy or sell anything
- Not political endorsements or advocacy
- Not speculative extrapolation beyond what the evidence supports

When confidence is low, say so explicitly. "The signals are mixed" is more
useful than false precision.

---

## Part 4 — Output Architecture

Different outputs serve different parts of the interpretive goal.

| Output | Purpose | Length | Audience facing? |
|--------|---------|--------|-----------------|
| Global meta story | Answer: what is the world saying today? | ~400 words | Yes — homepage hero |
| Category summaries | Answer: what happened in [domain] today? | ~150 words | Yes — category pages |
| Topic briefs | Answer: what's the latest on [specific thread]? | ~100 words | Yes — topic pages |
| Stability signals | Dashboard: which systems are under stress? | Structured data | Yes — dashboard |
| Leading indicator alerts | Flags: what today predicts for 6-24 months | 1-3 sentences | Yes — alert feed |
| Article summaries | Factual compression of each source article | ~120 words | Internal → feeds Stage 3 |
| Headline summaries | One-sentence per article | 1 sentence | Yes — feeds, email |

### Stage 3 should produce, in this order:
1. Article importance scores (already in Stage 2 output)
2. Category summaries — one per active category with articles today
3. Global meta story — interpretive synthesis across all categories
4. Leading indicator alerts — flagged from articles with high importance + forward signal
5. Topic briefs — triggered when ≥5 articles share a subcategory in one day

---

## Part 5 — What Success Looks Like

A reader finishes the daily briefing and has:

1. **A clear model update** — one or two things they now understand differently
   than they did yesterday. Not just "new information" but a revision to their
   mental model of how something works.

2. **An accurate sense of the signal level** — is today a high-signal day
   (multiple converging events) or a low-signal day (routine activity, no
   inflection points)?

3. **One or two things to watch** — specific leading indicators or developing
   stories that will become more important in the next weeks or months.

4. **Calm** — not anxiety or information overload. The briefing should make the
   world feel more legible, not more chaotic. Precision and calm are the same thing.

### Anti-goals (what the product is NOT)

- Not a breaking news ticker — we are not competing on speed
- Not a political opinion column — interpretive but not advocacy
- Not comprehensive — we curate ruthlessly; incompleteness is a feature
- Not alarming — the world is complex and dangerous; that is not news.
  The job is to be clear-eyed, not to amplify anxiety.

---

## Part 6 — Source Prioritization Principles

When deciding what to add or prioritize, apply these filters in order:

1. **Primary vs. secondary** — prefer the primary source (government, institution,
   central bank) over coverage of it (journalists, analysts). Primary sources
   contain more signal and less noise.

2. **Action vs. statement** — an enforcement action, a rule change, a data release
   carries more weight than a press conference statement. Events > words.

3. **Data vs. narrative** — quantitative data (BLS, FRED, EIA) provides ground
   truth that narrative can't overwrite. Prioritize sources that produce data.

4. **Non-US perspective** — given the US-centric nature of current sources,
   any high-quality non-US primary source has outsized value until global
   coverage is balanced.

5. **Cross-lens relevance** — a source that touches multiple lenses (e.g., OFAC
   sanctions data touches geopolitics, finance, AND US-China simultaneously)
   is worth more than a source that feeds only one lens.
