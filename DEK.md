# DEK.md — The day's synopsis (v3, 2026-05-27)

The dek is the brief's short factual synopsis of the day. It names the
day's most consequential events as a tight bullet list, each bullet a
plain-English statement of fact.

This document is binding. Synth must follow every rule below.

---

## What the dek is for

A reader who skims only the **headline + dek** should walk away knowing
exactly what happened today — the top three events, in plain English,
with zero foreign-policy jargon, zero acronyms, and zero personal names
they don't already recognize.

The target reader is a **smart layperson who reads NYT or Washington Post
once a day**. They are not a foreign-policy professional. They do not
follow alliance acronyms (Quad, NPT, AUKUS), they do not recognize most
foreign ministers by name (Jaishankar, Vučić, Sharif, Motegi), and they
do not know what abbreviations like NDRC, MFA, or CCDI stand for.

The dek must be readable by that audience **on first read, with zero
Googling**. If a term needs a footnote or a glossary, it does not
belong in the dek.

---

## Form

The dek is a `<ul class="dek-bullets">` containing **exactly three
`<li>` bullets**. Each bullet is a single short sentence — no semicolons,
no commas-as-conjunctions, no clauses-within-clauses.

**Bullet length: ≤12 words each.** Aim for 6–10. A bullet that needs more
than 12 words is hiding either (a) a name that should be dropped, (b)
an acronym that should be spelled out as a phrase, or (c) two events
glued together that should be split.

---

## Hard rules

### 1. The three bullets ARE the top-3 visible event ledes

The dek bullets are the same three events that anchor the top-3 visible
items list below. No duplication of work, no contradiction — the dek is
the collapsed view of those three events, and the events block is the
expanded view. Pick the day's three most consequential events, write
each as a dek bullet, and use that same lede phrase as the `<b>...</b>`
opener on each top-3 event below.

### 2. No bare acronyms or insider jargon

Spell out or rephrase. Examples:

- ❌ `NPT Review Conference closes without consensus.`
- ✅ `Nuclear non-proliferation treaty review closes without agreement.`

- ❌ `Quad foreign ministers meet for the first time in 2026.`
- ✅ (drop entirely — see rule 4 on outcomes vs process)

- ❌ `CCDI announces new disciplinary measures.`
- ✅ `Communist Party's anti-corruption body announces new disciplinary measures.`

- ❌ `NDRC publishes mineral-resources enforcement rules.`
- ✅ `China's central planning agency publishes mineral-resources enforcement rules.`

Banned-without-context terms: NPT, NDRC, MFA, CCDI, CAC, MIIT, PBOC, SAFE,
SASAC, NPC, MND, Quad, AUKUS, BRICS, G7 (acceptable — most readers know),
ASEAN (acceptable — most readers know), NATO (acceptable).

When in doubt: would a smart layperson know what this means? If no,
spell it out or rephrase.

### 3. No unfamiliar personal names

Use country or institution instead.

- ❌ `Rubio and Jaishankar sign minerals framework.`
- ✅ `U.S. and India sign critical-minerals framework in New Delhi.`

- ❌ `Xi awards Vučić the Friendship Medal.`
- ✅ `Xi awards Serbia's president the Friendship Medal.`

Globally-recognized names are fine: **Xi, Trump, Putin, Modi, Netanyahu,
Erdoğan, MBS, Kim Jong Un, Macron, Sunak/Starmer**. Everyone else: use
country or institution.

When in doubt: would the average newspaper reader recognize this name?
If no, drop it.

### 4. Prefer outcomes over process

A deal signed is news. A meeting held is process, and process is empty
without an outcome.

- ❌ `Quad foreign ministers meet for the first time in 2026.`
- ❌ `U.S. and Iran begin a new round of talks.`
- ✅ `U.S. and India sign critical-minerals framework in New Delhi.`
- ✅ `Nuclear non-proliferation treaty review closes without agreement.`

The exception: when the *meeting itself is the news* — a first-ever
summit, a walkout, a no-show, an unprecedented signal. Include only with
the specific newsworthy element named.

### 5. Neutral verbs, no editorial framing

Use plain verbs: sign, announce, publish, host, award, reject, close,
fail, open, expel, suspend, deploy, recall.

Avoid interpretive verbs: answers with, responds with, threads through,
sits behind, points to, signals, suggests, underscores, looks like,
appears to, increasingly, mounting, deepening.

### 6. No "while/even as/even" hedge clauses

They imply editorial framing. Each bullet is one event, one verb, one fact.

### 7. Every dek bullet's event must be in the top-3 events list

Coherence: the dek and the visible top-3 events must name the same
three things. They're two views of the same content.

---

## What the dek must do

A dek that ships satisfies all three:

1. **Name three concrete events** — by what happened, where, and (when
   useful) when.
2. **Be readable on its own.** A general-news reader sees the bullet
   list and understands what happened today without needing context
   from the events block.
3. **Stay factual.** No interpretation, no stance, no editorial flourish.

---

## Examples

### Good — three concrete events, no jargon, no unfamiliar names

```
• U.S. and India sign critical-minerals framework in New Delhi.
• Nuclear non-proliferation treaty review closes without agreement.
• U.S. and Iran continue Strait of Hormuz negotiations in Qatar.
```

Plain English. Outcomes, not meetings. Country names, not personal names.
No acronyms (NPT spelled out, Quad dropped entirely).

### Good — China brief

```
• Xi awards Serbia's president the Friendship Medal.
• China's defense ministry rebuffs Taiwan's inauguration speech.
• Huawei unveils new chip-design principle.
```

Xi kept (globally recognized). Vučić, Sharif, Lai dropped (use country
or institution). "Inauguration speech" replaces "May 20 speech" (dates
without context confuse).

### Bad — jargon-loaded

```
• Quad foreign ministers meet for the first time in 2026.
• NPT Review Conference closes without consensus.
• MFA daily briefing addresses Hormuz situation.
```

"Quad," "NPT," "MFA" all require prior knowledge. None of these would
pass the smart-layperson readability test.

### Bad — name-loaded

```
• Rubio and Jaishankar sign minerals framework in New Delhi.
• Wong, Motegi, and Jaishankar join Rubio at Quad meeting.
• Araghchi tells Motegi Iran is committed to talks.
```

A general reader recognizes ~0 of these names. Replace with countries
or institutions.

### Bad — process, not outcome

```
• U.S. and India hold bilateral talks in New Delhi.
• Quad ministers meet on Indo-Pacific cooperation.
• Pakistani prime minister visits Beijing.
```

Meetings, not events. None of these tell the reader what *happened.*

---

## Pre-flight checklist for synth

Before writing the dek bullets, answer for each one:

1. Would a smart layperson — who reads mainstream news daily but doesn't
   follow foreign policy — fully understand this bullet on first read,
   with zero Googling?
2. Does it use any acronym I haven't spelled out?
3. Does it use any personal name a typical reader wouldn't recognize?
4. Is it an outcome (signed, published, announced, rebuffed) or just
   process (met, discussed, talked)?
5. Is the bullet ≤12 words?
6. Is this event in the top-3 visible events list?

If any answer is no, rewrite.
