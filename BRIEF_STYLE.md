# Briefer News — Brief Style Guide

> This is the editorial style guide for the daily brief. Point Stage 3
> (the synthesizer) at this document. Edit this file to tune output.
>
> Written: 2026-05-07, after the May 6 brief landed cleanly and the
> May 7 first draft drifted. The May 6 patterns are the target;
> the May 7 v1 anti-patterns are documented below as warnings.

---

## What the brief is

A single-page daily brief on official U.S. government output. The reader
is a well-informed generalist who wants to know **what the day was** in
three minutes. They are not breaking-news customers; they are people
who want a clean, sourced, model-updating summary of what the
American federal government did today.

Every claim in the brief is linked to a public .gov source. No
opinion. No editorial. Facts, voices, and citations.

---

## Audience reach — international by default

The reader is not necessarily American. Briefer News covers what the U.S.
government does because the U.S. is consequential globally — but the audience
is a **global readership** of generalists who want to understand U.S.
government action *as it relates to the world*.

This means American-domestic items must clear a **higher bar** to take a
slot in the brief. When choosing between two stories of similar scale, the
one with international stakes wins.

### What counts as "international stakes"
- Affects foreign actors directly (sanctions, treaties, designations, export
  controls, foreign-investment rules)
- Affects globally-traded markets or commodities (energy, food, semiconductors,
  finance, currency)
- Affects global cybersecurity or critical infrastructure (actively-exploited
  CVEs in widely-deployed products, supply-chain coordination)
- Sets precedent for non-U.S. systems (U.S. court rulings affecting global
  contracts, regulatory frameworks other countries copy)
- Is a major U.S. policy or event with intrinsic global newsworthiness
  (presidential addresses, major executive orders, summit calendars)

### What is "purely domestic"
- State-vs-federal constitutional disputes whose stakes are entirely U.S.
- Local infrastructure projects (a pipeline serving one U.S. region, a
  city-specific antitrust action) — unless the project changes global
  market structure
- U.S.-specific cultural or symbolic items (national-day proclamations,
  domestic fitness-month declarations)
- Procurement rules whose effect is internal to the U.S. federal contracting
  ecosystem (FCC consumer-broadband rules, generic procurement adjustments)

### Cap on purely-domestic items
**No more than 3 of 9 bullets** should be purely domestic with no
international stake. If you find more than 3, demote the weakest to make
room for international stories that didn't fit.

### When you do include a domestic item, frame its global relevance
A U.S. antitrust action against a major hospital system can be framed as
"an early signal of the administration's healthcare-cost strategy."
A state-versus-federal 2A case is "the first DOJ action by the Civil
Rights Division's new Second Amendment Section."

If a domestic item has no plausible international frame, that's a sign it
shouldn't be in today's brief — drop it.

---

## Page structure (in order)

1. **Masthead** — `BRIEFER NEWS` + tagline `A daily brief from U.S. government sources`. Small monochrome flag glyph above title.
2. **Date stamp** — small, mono caps, top-right of body column. Format: `MAY 7, 2026`.
3. **Headline** — one short sentence framing the day.
4. **Voices** — three (occasionally four) pull-quotes from named officials or documents.
5. **Significant items** — 9 bullets in priority order. Each with bold lead, citation, and date · agency tag.
6. **Sources** — numbered bibliography with full citation and link.
7. **Footer** — brand, nav, theme toggle.

---

## Headline rules

### Target
**12–16 words**, **two clauses** (separated by colon, semicolon, or "as/while"), each clause action-led, each clause anchored to a concrete fact (named actor, number, or named event).

### Good ✓
- "On Iran: U.S. drafts UN resolution; oil release reaches 172 million barrels." *(13w, two clauses, both anchored to specifics)*
- "Cuba sanctions framework lands; DOJ opens enforcement fronts against UCLA, Colorado, and NY-Presbyterian." *(13w, two clauses, names defendants)*
- "U.S. moves on Iran with UN resolution as global oil release widens to 400 million barrels." *(15w, single thought)*

### Bad ✗
- "The U.S. coordinates a 400-million-barrel global oil release and presses a UN Security Council resolution against Iran's Strait of Hormuz blockade as a Trump–Xi summit approaches." *(28w — wire copy, not a headline)*
- "Today's Brief: Several Important Government Developments" *(empty calories — no specifics)*
- "DOJ Files Multiple Enforcement Actions" *(category, not event)*

### Construction patterns that work
- **`On X: Y; Z.`** — colon introduces theme, two clauses do the work.
- **`X lands; Y opens fronts on A, B, C.`** — sequencing two arcs of the day.
- **`X as Y`** — concurrent or causal framing.

### Avoid
- Conjunctive overload ("...and...as...with...").
- Naming people without context ("Rubio, Lavrov, and Wadephul met").
- Throat-clearing ("In a major development...", "Today saw...").

---

## Voices rules

### Target
**Three voices**, occasionally four. Each quote **12–30 words**.

### Composition
Aim for a **mix of registers**:
1. **Moral / sharp** — short, declarative, rhetorical. Rubio's *"What is an act of war? Putting mines in the water."* is the archetype.
2. **Technical / bureaucratic** — substantive policy language, longer. Quote text that ANCHORS a specific item in the bullets.
3. **Political / ideological** — administration framing, often longer. Reveals the day's posture.

If a fourth voice is included, it should be **a fourth register** (e.g., a document or court speaking, not a fourth person).

### Good ✓
- *"What is an act of war? Putting mines in the water."* — 12w, rhetorical, sharp.
- *"Racism in admissions is both illegal and anti-American, and this Department will not allow it to continue."* — 18w, declarative.
- *"America is producing as much natural gas as Russia, China and Iran combined."* — 13w, fact-anchored.

### Bad ✗
- *"These actions hold accountable U.S. nationals who enabled North Korea's illicit efforts to infiltrate U.S. networks and profit on the back of U.S. companies. The National Security Division will continue to pursue those who, through deception and cyber-enabled fraud, threaten our national security."* — 38w, two sentences, generic enforcement boilerplate.
- *"UCLA's admissions process has been focused on racial demographics at the expense of merit and excellence — allowing racial politics to distract the school from the vital work of training great doctors. Racism in admissions is both illegal and anti-American, and this Department will not allow it to continue."* — 47w, the second sentence carries the punch; the first sentence is preamble. Cut the preamble.

### Cite format
`[Title] [Name], [Affiliation] · [Date][^N]`

Examples:
- `Sec. of State Marco Rubio · May 5¹`
- `AAG Harmeet K. Dhillon, DOJ Civil Rights · May 6⁵`
- `Executive Order 14404 · May 1¹`

### Cardinal sin
**Never invent a quote.** Quotes must come verbatim from the source article. Truncate with `[brackets]` to clarify subject if needed (e.g., `"[The Cuban government's policies] are repugnant…"`), but never paraphrase inside quotation marks.

---

## Bullet rules

### Target
**9 bullets per brief**, ordered by significance (highest first, lowest near the bottom). Ruthless curation — 9 items the reader should know, no padding.

Each bullet:
- **23 ± 10 words** (most should land in the 18–35 word range).
- **One sentence preferred. Two sentences max.** No three-sentence bullets.
- **Bold lead-in**: 2–4 words, noun phrase, period.
- **Action-led description**: name actors, name numbers, state what happened.
- **Citation** linking to .gov URL: `<sup><a class="cite" href="…">N</a></sup>`
- **Date · Agency tag**: `<span class="when">May 7 · DOJ</span>`

### Bold lead-in pattern

The bold lead is a **topic marker**, not a sentence. Short noun phrase, period.

### Good ✓
- **`Project Freedom.`** *(named operation)*
- **`Trade deficit.`** *(noun, the subject)*
- **`DOJ v. UCLA.`** *(case caption)*
- **`Trump–Xi summit.`** *(named event)*
- **`SPR exchange.`** *(named program)*
- **`CISA KEV.`** *(named catalog action)*

### Bad ✗
- **`The Department of Justice today announced…`** *(this is the description, not the lead)*
- **`UCLA Medical School Race Discrimination Investigation Determination.`** *(too long, reads as legalese)*
- **`Justice Department investigation determines UCLA's medical school discriminated based on race in admissions.`** *(a sentence, not a topic marker)*

### Description body

After the bold lead, write **one tight sentence** that states the action and names actors / numbers.

### Good ✓ (May 6, ~23 words)
> **DOJ v. Minnesota.** Federal-preemption complaint filed against Minnesota's state-court suits against energy companies — the fifth such filing.

> **SPR exchange.** DOE issued an April 30 RFP for an emergency exchange of up to 92.5 million barrels — part of a coordinated 400-million-barrel IEA release, the largest in the Reserve's 50-year history.

### Bad ✗ (May 7 v1, ~70 words — corrected to ~30 in v2)
> **Cuba sanctions framework.** Executive Order 14404 — published May 7, signed May 1 — imposes a full sanctions regime on Cuban officials and on persons operating in Cuba's energy, defense, metals, financial services, or security sectors. The order reaches material supporters, those responsible for human rights abuse or corruption, and adult family members of designated persons; foreign financial institutions transacting for designated persons can have U.S. correspondent accounts cut off.

The bad version explains *the legal architecture*. The good version states *what happened*.

### Compression rules

When you have a long source paragraph, ask:
1. **What did someone do?** (action verb + actor)
2. **Against whom or what?** (object)
3. **At what scale?** (number, magnitude)
4. **Under what authority?** (only if non-routine)

Drop everything else. Mechanism, legal architecture, agency org charts, foreign-financial-institution penalty subclauses — all of that lives in the source link, not the bullet.

### Anti-pattern checklist

Cut any sentence that:
- Explains the legal authority chain (cite IEEPA, don't define IEEPA).
- Lists every sub-clause of a sanctions order ("reaches X, reaches Y, reaches Z, reaches W").
- Restates information already in the bold lead.
- Uses passive voice when active is available ("was filed by X" → "X filed").
- Begins with a participial phrase or subordinate clause ("In response to growing concerns…").

---

## Date · Agency tag

Format: `[Date] · [Agency]` — small, mono caps, end of bullet.

### Date attribution
Use the **event date**, not the source-publication date, when they differ.

| Event | Tag with | Not |
|---|---|---|
| RFP issued April 30 | `Apr 30` | scrape date |
| EO signed May 1, published May 7 | `May 1` | `May 7` |
| Hearings May 5–8 | `May 5–8` | a single day |
| Future event (summit week of May 11) | `Wk of May 11` | the announcement date |

### Agency tag — short forms

Standardize to these abbreviations:

| Source | Tag |
|---|---|
| State Department | `State` |
| Department of Justice | `DOJ` |
| Department of Energy | `DOE` |
| Department of the Treasury / OFAC | `Treasury` (or `OFAC` for OFAC-specific) |
| Department of Commerce / BEA | `BEA` |
| USTR | `USTR` |
| White House (presidential statement / WH research) | `WH` |
| Federal Register | `Fed. Reg.` |
| CISA | `CISA` |
| FBI | `FBI` |

---

## Sources section

Numbered footnotes matching `<sup>` references in the body. Format:

```
[N]. <span class="pub">Publisher</span>, "Title," date.
     <a href="full URL">domain.tld/…/short-slug</a>
```

The displayed URL should be a **shortened readable form** (e.g., `state.gov/releases/…/rubio-remarks-9`), not the full URL. The actual `href` is the full URL.

---

## What goes in / what stays out

### Always include
- Executive orders and presidential actions (with EO number).
- Sanctions designations (named entities/individuals).
- DOJ enforcement actions (cases filed, sentences imposed).
- Federal Register final rules with policy substance.
- Major economic data releases with the headline number.
- Diplomatic moves with named counterparts and concrete outcomes.
- CISA cyber advisories actively exploited.

### Usually skip
- Air quality plans, airspace amendments, salable-quantity allotments. (Unless unusual.)
- Routine national-day greetings (unless tied to a substantive announcement).
- Repeat publication of older items via RSS catch-up. Use the original event date and only include if substantively recent.
- Treasury secondary-market or technical bulletins.
- Speech announcements (without substantive content).

### Cap on DOJ
DOJ tends to publish many enforcement actions per day. Cap at **2 DOJ items per brief** unless DOJ is the day's dominant story. Pick the **most consequential** by:
1. Defendant size / market impact
2. Constitutional or precedential novelty
3. National-security stakes
4. Dollar amount of settlement or sentence

Drop the rest. False Claims Act settlements under $50M, prosecutor-policy notification letters, and routine-pattern-enforcement cases are usually droppable.

---

## Item ordering

Within the bullet list, order by significance:
1. **Structural/foreign-policy moves** that shape multi-month trajectory (sanctions frameworks, treaties, summit calendars).
2. **Enforcement actions of national significance** (precedential DOJ cases, major sanctions designations).
3. **Cyber / national-security incidents** with active exploitation.
4. **Economic and procurement rules** with broad effect (DFARS, FCC).
5. **Specific energy / infrastructure actions** (pipelines, plants, RFPs).
6. **Diplomatic engagements with named outcomes**.
7. **Standalone administrative items** (national-day proclamations, routine continuations).

The reader should be able to stop reading at any point and have already absorbed the most important items of the day.

---

## What good days look like

| Day | Signature |
|---|---|
| **Foreign-policy day** | State Department dominates; multiple regional desks reporting; one or two diplomatic principals named; treasure trove of voice-quotable statements. |
| **Enforcement day** | DOJ dominates; Federal Register publishes new rule(s); CISA may layer in. Use 3–4 DOJ slots, drop the rest. |
| **Energy day** | DOE publishes; Federal Register publishes related rule; international energy summit may anchor a hero piece. |
| **Quiet day** | <8 substantive items. Rather than padding to 16, **publish 8.** A short brief is honest. |

---

## Voice & tone

The brief is written in the voice of a **clear-eyed analyst** with no incentive to alarm or reassure. Like a senior correspondent who has read all of today's federal output and distilled it. Calm. Specific. Sourced. Patient with the reader, ruthless with words.

**Sounds like**
- *"State and Treasury sanctioned Qingdao Haiye Oil Terminal — a China-based facility that handled tens of millions of barrels of sanctioned Iranian crude — plus three Iranian currency-exchange houses moving billions annually."*
- *"Federal suit filed against Colorado's standard-capacity firearms-magazine ban, alleging the law is unconstitutional under Heller (2008)."*

**Does not sound like**
- *"In a major development today…"*
- *"Authorities say…"*
- *"This action represents the latest in a series of…"*
- *"It remains to be seen whether…"*
- *"Critics argue / supporters say…"*

---

## Synthesizer checklist

Before publishing, the synthesizer should verify:

- [ ] Headline is one sentence, ≤16 words, anchored to specifics.
- [ ] 3 voice quotes (occasionally 4). Each between 12–30 words. Mix of registers.
- [ ] All quotes are verbatim from source articles.
- [ ] 9 bullets, ordered by significance.
- [ ] Each bullet has bold lead (2–4 words), tight description (≤35 words), citation, date · agency tag.
- [ ] No DOJ glut: ≤2 DOJ items unless DOJ is the day's dominant story.
- [ ] No domestic glut: ≤3 purely-U.S.-domestic items per brief.
- [ ] Each bullet's date is the EVENT date, not the scrape date.
- [ ] No legal-mechanism explainers; no agency-org-chart paragraphs.
- [ ] All citations resolve to live .gov URLs.
- [ ] Sources section bibliography format clean.
- [ ] No editorial language; no "could potentially," "in a statement," "it remains to be seen."
- [ ] Quiet day handled honestly: short brief over padded brief.

---

## Reference briefs

- **Good (May 6, 2026):** `research/brief_2026-05-06.md` — Iran-Hormuz crisis dominant, ~23-word bullets, 3 voices, headline 13 words. Original draft had 16 bullets; under the 9-bullet target, would trim to top 9 by significance.
- **Bad first draft, then corrected (May 7, 2026):** `research/brief_2026-05-07.md` — first version had 51-word bullets and 38-word quotes; corrected to May 6 cadence.

When in doubt, model on May 6.
