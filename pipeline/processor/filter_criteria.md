# Groq Filter — Criteria Document

> This document is injected into the Stage 1 Groq prompt.
> It defines what gets filtered out and why.
> Edit here to tune the filter — treat this like code.
> Last updated: Feb 2026.

---

## Who this filter serves

The reader of this intelligence briefing is trying to understand the world as a system —
power, resources, technology, stability. They are not looking for news summaries.
They are looking for signal.

Your job is to separate signal from noise before any expensive processing happens.
Be conservative. When in doubt, keep.

---

## Always keep — never filter these out

### Enforcement actions
Any indictment, arrest, extradition, sanctions designation, consent order, civil penalty,
regulatory enforcement action, or asset seizure. These are acts with real-world consequences —
they are always signal, regardless of how routine they appear in the title.

### Policy changes that move through the economy
Rate decisions, proposed rules, final rules, regulatory guidance, executive orders,
presidential actions, trade restrictions, export controls, tariffs.
Even proposed rules matter — they signal where policy is heading.

### Foreign policy and diplomatic actions
Any statement, press conference, communiqué, or announcement involving:
- US-China relations, Taiwan, South China Sea
- Russia, Ukraine, NATO, Eastern Europe
- Middle East, Iran, Saudi Arabia, Gulf states
- India, Pakistan, Africa, Latin America
- Multilateral institutions (UN, WTO, G7, G20, BRICS)

### Research and scientific findings
Papers, studies, clinical trials, preprints, academic findings in:
- Energy, climate, materials science, biology, AI, medicine, physics

### Economic data releases
CPI, PCE, jobs reports, GDP, trade balance, manufacturing data, PMIs,
central bank decisions, yield curve moves, banking sector stress signals.

### White House and presidential
Any White House release, presidential action, executive order, or statement
by the President or cabinet members. All of these are signal.

### Energy and resource events
Oil production data, rig counts, pipeline decisions, field developments,
mineral supply chain events, refinery issues, LNG deals.

### Technology milestones
Major model releases, chip export decisions, semiconductor production news,
quantum computing progress, breakthrough research.

### State media
Xinhua, Global Times, TASS, Kremlin, Saudi SPA, IRNA, RT — these are primary
sources for understanding what those governments want the world to believe.
Always keep. The gap between their claim and observed behavior is the signal.

---

## Filter these out — with examples

### Routine travel advisories (keep if escalation, filter if routine)
FILTER: "Level 2 Advisory: Exercise Increased Caution in Indonesia"
FILTER: "Travel Warning Update: Minor Security Situation in [city]"
KEEP: "Level 4 Advisory: Do Not Travel to [country]" — level 4 is escalation signal
KEEP: Any travel advisory for a country that is NOT already under a standing advisory

### Secretary's daily schedule and routine logistics
FILTER: "Secretary Blinken's Schedule for February 22"
FILTER: "Secretary's Public Schedule — [date]"
FILTER: "Administrator [X] to Attend [routine conference]"
KEEP: Any speech or policy statement at such events (the event title ≠ the statement)

### Routine FOIA and administrative notices
FILTER: "Notice of FOIA Request Backlog Reduction Plan Update"
FILTER: "Agency Information Collection Activity — comment period extension"
FILTER: "Form XYZ-123 Revision Notice"
KEEP: Any FOIA release that reveals substantive policy content

### Minor awards, personnel, and ceremonial items
FILTER: "[Agency] Selects New Contracting Officer"
FILTER: "Administrator Attends Ribbon-Cutting at [facility]"
FILTER: "Agency Announces Employee Wellness Month"
KEEP: Senior leadership changes (agency heads, deputy heads, key positions)

### Routine grant announcements with no strategic significance
FILTER: "$500K Grant for [local community] Flood Mitigation"
FILTER: "USDA Announces $2M for [state] Agricultural Research"
KEEP: Any grant that reveals strategic priorities ($1B+ infrastructure, tech, defense)
KEEP: Any grant that involves China, Russia, Taiwan, or critical minerals

### Comment period announcements with no substance
FILTER: "EPA Opens 60-Day Comment Period on [routine rule]"
KEEP: Comment periods for rules that would affect: AI, energy, export controls, finance

---

## Edge cases — lean toward keeping

These categories are borderline. The default is KEEP, not filter:

- Regulatory announcements that sound minor but touch energy, tech, or finance
- Scientific funding decisions (who gets the grant reveals strategic priorities)
- Local events that involve a foreign-controlled company or government (e.g., Chinese
  company opening a facility in a US state — that is a signal)
- Any item from a non-US source that involves the US, China, or Russia

---

## Bias statement

A false negative (dropping a real story) is much worse than a false positive
(keeping a junk article that Gemini briefly summarizes at minimal cost).

Gemini is cheap. The cost of filtering out a real story is high.
Set your threshold accordingly: filter aggressively only for obvious waste.
