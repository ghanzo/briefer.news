# China brief — Allied Governments section (planned)

> **Status: planned, not yet implemented.** Scoped 2026-05-23. Pick up
> in a future session. Implementation is ~2-3 hours of work, mostly the
> source-scoping at the front.

---

## Goal

Add an Allied-Governments-equivalent section to the China brief —
parallel to the US edition's existing "Allied Governments" block, but
sourced from non-PRC governments commenting on or interacting with
China. Same trust posture as the daily brief: **government primary
sources only, no press, no opinion**. Preserves the brand promise
that was the reason the original "Outside the Gate" section was
reverted on 2026-05-14 (which used Reuters / AP / NBC and broke the
gov-sources-only rule).

This satisfies the original editorial intent (outside perspective on
China, the "to China" half of the dashboard framing) without
contaminating the citation spine with press sources.

## Sources — candidate list

All `.gov` (or equivalent) outputs that talk *about* China:

- **U.S. State Department** — China-relevant press releases, statements
  on Taiwan, sanctions announcements. Already scraped on the US side;
  needs a China-keyword filter to surface the China-relevant subset.
- **Japan MoFA** — already scraped (allied-gov on US side). Cross-Strait,
  East China Sea, Diet readouts touching China.
- **Australia DFAT** — already scraped. Indo-Pacific outputs concerning
  China.
- **UK MoD / FCDO** — UK MoD already scraped; FCDO is new. China policy
  releases, sanctions, Hong Kong reporting.
- **NATO** — already scraped. Communiqués mentioning China (have been
  ramping in 2024-2026).
- **Taiwan MOFA / Presidential Office / MND** — new sources. Cross-Strait
  statements, Taiwan-side framing on incidents.
- **India MEA** — new. China-relevant statements (border, BRI, etc.).
- **South Korea MOFA** — new. Statements on China, Taiwan, NK-China.
- **EU EEAS** — new. China policy statements.

Priority 1 (already scraped, just need a China filter): State Dept,
Japan MoFA, Australia DFAT, UK MoD, NATO.

Priority 2 (new sources to add): Taiwan MOFA + Presidential Office,
India MEA, FCDO, EU EEAS, South Korea MOFA.

Start with Priority 1 — get the section working from existing data
before adding new scrapers.

## Visual + structural design

Mirror the US Allied Governments treatment exactly:

- Section heading: `<h3 class="section-label">Allied Governments</h3>`
  (or potentially "International Governments" / "Outside Voices" —
  decide at implementation time; "Allied Governments" is the safest
  default since it matches the US naming).
- Bullet container: `<ul class="items allied-items">`.
- 3 bullets, same structure as Events (bold lead, tight description,
  citation, date + agency tag).
- Cite markers lowercase letters `(a, b, c)` to keep them visually
  distinct from the numbered .gov.cn cites (1-9) above.
- Self-contained cites: `<a class="cite">` carries the href + title
  attribute; allied items do NOT get numbered entries in the Sources
  bibliography (consistent with the US side).
- **Position on page:** directly after the more-events `<details>`
  closes, before Strategic Backdrop. Same vertical slot the US Allied
  Governments occupies relative to its more-events block.
- **Conditional rendering:** if no Allied-government material is worth
  a slot today, omit the section entirely (both `<h3>` and `<ul>`) —
  never render an empty section. Mirrors the US rule.

## Data layer

Two viable paths:

**Path A — extend the existing China candidate pool with a
non-PRC-gov-on-China subset.**
- Add a new SQL query in `pipeline/...` that filters all allied-gov
  scraped articles for China keywords (Taiwan / PRC / Xi / Beijing /
  Strait / NATO–China / etc.).
- Surface the top 5-10 hits as "Allied-gov candidates" in the
  China candidate-pool output that `synthesize_china.sh` reads.
- Synth picks 3 of these to render.

**Path B — dedicated `china_allied_context.sh` Stage 0.**
- Mirror the US `daily.sh` Allied-gov flow more literally.
- Standalone script that emits an "Allied-gov candidates" subsection
  in `.run/china_allied.md`, read by the synth.

Path A is leaner — uses existing infrastructure. Recommended.

## Synth prompt + prototype changes needed

- **`scripts/synthesize_china.sh`**:
  - Add an "ALLIED GOVERNMENTS SECTION" instruction block mirroring
    the wording at scripts/synthesize.sh line 346.
  - Add the section's `<h3>` + `<ul class="items allied-items">`
    selectors to the "Only replace:" list.
  - Position: directly after the `</details>` closing the more-events
    block, before the Strategic Backdrop opens.
- **`research/prototype_china_2026-05-12.html`**:
  - Add the section structure mirroring the US prototype's Allied
    Governments block.
  - Make sure CSS for `.allied-items` is present (it might already be
    shared from US prototype CSS; verify).
- **`CHINA_BRIEF.md`**:
  - Update the page-structure diagram to include the new section.

## Trade-offs / decisions to make at implementation time

- **Section naming.** "Allied Governments" matches the US side (and is
  the safest framing). "International Governments" is more neutral
  globally. "Outside Voices" was the abandoned 2026-05-14 name —
  probably avoid to prevent confusion. Default to "Allied Governments".
- **Taiwan inclusion.** Taiwan government sources are diplomatically
  sensitive — the PRC does not recognize them as a government. Including
  Taiwan MOFA in an "Allied Governments" block is a real editorial
  position (closer to the US's effective recognition than the PRC's).
  Defensible given the brand's source-transparency posture, but worth
  acknowledging in the BRIEF_STYLE.md or About page if Taiwan items
  routinely appear.
- **State Department dominance.** State.gov volume could crowd out the
  smaller allied-gov sources. Apply a cap (≤1 State item per day)
  similar to the US side's "≤2 DOJ" cap.

## Testing checklist (when implemented)

- Pilot synth produces an `Allied Governments` block on at least 5 of
  7 days (some quiet days are expected).
- Source diversity across a week: at least 3 distinct allied
  governments cited.
- No PRC sources sneak in (all cites point to non-`.gov.cn` domains).
- No press sources sneak in (no Reuters / AP / Bloomberg in the
  block's citations).
- Cite markers are lowercase letters, not numbers.
- Conditional omission works on days with no material (block fully
  disappears, not rendered empty).

## Why this was right to defer tonight

This is a real data-layer + editorial design effort. Tonight already
shipped the layout reorg, About refresh, Sources refresh, favicon, and
Search Console API hookup. Doing this properly when fresh — with focus
on source-scoping and editorial weight calibration — gives a much
better outcome than a tired late-night sprint.
