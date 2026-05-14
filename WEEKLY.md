# WEEKLY.md — The weekly digest voice and structure

The weekly is a different artifact from the daily. The daily is the heartbeat; the weekly is what people save and forward. It is the editorial product that builds a returning-reader habit.

The daily is "what happened." The weekly is "what the week *meant*."

This document is binding. Synth must follow every rule below.

---

## What the weekly is for

A reader who skims only the weekly should walk away with:
- A **posture** on the week (the editor's read of what just happened, not a summary)
- A handful of items that *clarified* something — not the loudest, the most revealing
- A sense of which long-arc threads advanced and how
- A few voices worth remembering
- A list of moves that came from outside the gate (sanctions, deployments, allied positions, adversary statements)

The weekly is **longer-form than the daily** — total editorial content 800–1500 words. It's expected to take 8–12 minutes to read, not 3–5.

---

## Structure

The page has these sections, in this order:

1. **Masthead + week stamp** — "WEEK OF MAY 8 – MAY 14, 2026"
2. **Headline** — one line, ≤14 words. A stance or a question. Not a topic.
3. **The Week's Read** — the lead paragraph, 80–120 words. Replaces the daily dek but does more work.
4. **Threads at week's end** — 60–150 words, prose. Where the long arcs stand at week's close.
5. **The Week's Bullets** — 5–7 items, each 40–80 words. The clarifying items, with explanatory text.
6. **Voices of the Week** — 6 voices. 3 in Selected view + 3 in Expanded, same as daily.
7. **Strategic Backdrop weekly** (China edition only) — 2–3 doctrines that recurred across the week.
8. **Outside the Gate weekly** — 5–7 inbound signals from the week, sourced from non-gov outlets. (This section is auto-populated from the OG weekly aggregation — synth doesn't re-author it, it includes it.)
9. **Footer** — small links to each of the past 7 daily briefs by date.

---

## The Headline

≤14 words. **Not a topic label.** A stance, a question, or a one-line summation of the week's posture.

**Anti-pattern (banned):**
- "The week in Iran war and trade" — topic label
- "Big week in US-China relations" — vague
- "Top stories of the week" — generic

**Right pattern (worked examples):**
- "Washington went to Beijing with leverage and came back with a Taiwan warning."
- "The Iran war's coalition phase began this week — quietly."
- "Three Fridays of regulatory consolidation, one Sunday of accidental clarity."

Read it aloud. If it sounds like an editor's verdict, it's right. If it sounds like a topic, rewrite.

---

## The Week's Read (lead paragraph)

80–120 words. **Two or three sentences max.** Replaces the daily dek; does heavier work.

A good Week's Read does at least three of these five:

1. **Names a posture** — who came out ahead, who was pressed, who improvised, what was choreographed.
2. **Notices an arc** — what moved in a direction. "The Iran war shifted from active strikes to coalition assembly." "Beijing's pre-summit consolidation was the actual story; the summit was the cover."
3. **Identifies an asymmetry** — what was said vs. done, what made the headlines vs. what mattered, who moved first vs. who answered.
4. **Makes a falsifiable claim** — something a careful reader could argue with.
5. **Anchors to a longer arc** — references the threads (Day 76 of Iran war, Year 5 of Ukraine, etc.) where natural.

**Banned constructions:**
- "This week was about [X]." (too literal — the reader can see the headlines)
- "On Monday we saw…, on Tuesday…" (chronological recap — boring)
- "Three big things happened." (list-with-no-stance)
- "X dominated the week" (filler)

**Banned doctrine name-drops** (same rule as DEK.md): no NQPF, 15FYP, dual circulation, common prosperity, 30/60, MIC2025 in the lead paragraph. Those belong in the Strategic Backdrop weekly section.

---

## Threads at week's end

60–150 words. Prose, not bullets.

Tell the reader, in the editor's voice, where each active thread stands at week's close. Reference the thread strip's Day-N counts where natural ("By Friday the Iran war was on Day 76; the coalition phase that began Monday now reads as cumulative"). Do not recite what advanced as a list. Name a *direction*.

If a thread *resolved* this week (a war ended, a summit concluded, a regulatory cycle closed), say so plainly and note what comes next.

**Anti-pattern:** "The Iran war continued. The Trump-Xi summit happened. The Ukraine war continued." (List of statuses — useless.)

**Right pattern:** "The Iran war's seventy-sixth day saw the coalition rather than the trigger become the story; forty navies in Hormuz outsizes any single strike. Trump landed in Beijing Wednesday and left Friday — the summit ended without a joint statement and with Taiwan as Xi's chosen sharp edge. Ukraine entered its fifth year unchanged in shape and worse in stamina."

---

## The Week's Bullets — 5 to 7 items

These are NOT the same shape as daily bullets. Daily bullets compress events into bold-lead + one sentence. Weekly bullets are 40–80 words each — enough to **explain why this item mattered more than the other forty-four** from the week.

**Each weekly bullet should answer:** what happened, and what does it tell us in retrospect?

Format:
```html
<li>
  <b>Lead phrase.</b> What happened in one sentence, with the date and source.
  Then the editorial read: why this item, why now, what it reveals or anchors.
  Cross-reference the daily where this first appeared.
</li>
```

Selection rule: **5–7 items that, in retrospect, told you what the week meant.** Not the biggest news. The most clarifying news. Avoid items that were dominant but didn't reveal anything new ("more Iran sanctions" — only include if a specific sanction signaled a new posture).

Cap: ≤2 of the 5–7 bullets can be from a single thread (so the week's news isn't 100% Iran or 100% summit).

---

## Voices of the Week

6 voices, same speaker-diversity rule as daily — each voice from a different speaker AND a different source category. 3 in Selected view, 3 in Expanded.

For the China edition, the Xi-first rule from the daily applies: if Xi spoke this week (and the quote is usable), Xi is voice #1.

Quote recency: must be from within the week being summarized. Older quotes are NOT allowed even with the strategy-anchor exception that applies to the daily. The weekly is about the week.

Each voice is the same shape as in the daily: 12–30 word verbatim quote, attribution + date in the cite, link to the source.

---

## Strategic Backdrop weekly (China edition only)

2–3 cards, same format as daily. Pick the doctrines from `pipeline/config/strategy/` that were **named or operatively-invoked most often** across the week's bullets. The card's blurb (~30 words) should connect the doctrine to specific items from the week.

This is NOT a guess at which doctrines might be relevant. It's a count: which strategy themes did the week's actual content invoke?

---

## Outside the Gate weekly

This section is **auto-populated** from the OG weekly aggregator (`scripts/og_weekly_aggregate.py`). The synth does not re-author it. The synth's job here is just to include the rendered OG weekly content in the right place on the page.

If the OG weekly aggregator returns 0 items (e.g., during rollout when post-change daily archives haven't accumulated yet), render the empty-state placeholder.

---

## Hard rules

- **Total editorial word count: 800–1500 words** for sections 2–6 (headline, lead, threads, bullets, voices). Strategic Backdrop and OG weekly are auto-shaped.
- **Headline ≤14 words.** Stance, not topic. (See banned patterns above.)
- **Lead paragraph 80–120 words, ≤3 sentences.**
- **Bullets 40–80 words each.** Compressing this week's daily output, with editorial explanation.
- **No chronological recap.** "On Monday…" / "By Wednesday…" / "Thursday brought…" is banned.
- **No doctrine name-drops in the lead.** Same rule as DEK.md.
- **No "the week saw" / "this week's news" / "in a week dominated by" openers.** Templates produce dead prose.
- **No claim in the lead that isn't supported by the bullets.**
- **Voices must be from within the week.** No strategy-anchor exception.

---

## When to break the rules

Two cases:

1. **A single dominant event consumed the week** (a presidential resignation, a major military strike, a market crash, a summit). On those weeks, the lead paragraph can be longer (120–180 words) and the bullets fewer (3–5), all converging on the single event from different angles.

2. **The week was unusually quiet.** On those weeks, the editorial value is naming *what didn't happen* and what that absence means. Lead can be shorter (50–80 words). Bullets fewer (4–5). Voices remain at 6 if material permits.

---

## A short checklist for the synth before drafting

Before writing the headline + lead:

- What is the *posture* I'm naming for this week?
- What arc moved most clearly? In which direction?
- What asymmetry emerged across days?
- Which bullets, in retrospect, clarified what the week meant? Why those?
- Have I avoided every banned construction?
- Could a careful reader disagree with my lead? (If no, the lead is too safe.)
