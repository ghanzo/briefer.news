# CHINA_BRIEF.md — China-source brief design + status

> Companion document to `BRIEF_STYLE.md` and `lens.md`, for the China side
> of briefer.news. Captures editorial framing, source list, current state,
> and active editorial direction.
>
> **Status: live and autonomous.** Brief at `https://briefer.news/china/`,
> synth fires 07:30 PDT daily via LaunchAgent `news.briefer.synthesize.china`.

---

## Why a China brief

The US-China axis is the defining geopolitical relationship of the era — `lens.md` says this. Covering only the US side is half the picture. The world watches Chinese gov output patchily; there's editorial value in synthesizing it daily with the same rigor we apply to US gov output.

**The hardest part isn't technical — it's editorial.** Reading Xinhua and reprinting it produces propaganda. The value of a China brief comes from knowing what to extract, what to discount, and which announcements actually matter. That requires a different lens than the US side.

---

## Editorial framing — internal-evolution priority

**Lens shift vs. the US brief:** for China, *internal developments matter more than external diplomatic statements*. What the user is curious about is **how China is structurally evolving from within** — not just "what is China saying about X to the world today."

This means weighting:

| Higher weight (internal, structural) | Lower weight (external, performative) |
|---|---|
| State Council policy releases | MFA spokesperson denials of foreign criticism |
| NDRC economic planning | Diplomatic readouts of bilateral meetings |
| PBOC monetary policy + financial system signals | UN/G20 positioning statements |
| MIIT industrial / chip / AI rules | Embassy press releases |
| CAC internet / data / algorithm rules | Generic "official line" statements |
| CCDI anti-corruption (political signals) | Tweet-grade Global Times commentary |
| Qiushi / People's Daily / CPC News (Xi speeches, Party theory) | China Daily English coverage |

MFA daily press conferences stay valuable — they're the **best voice source** (daily transcripts of named spokespersons). But MFA content gets weighted by *substance*, not by volume.

**Picker enforces the framing via two SQL pools** (`scripts/synthesize_china.sh` Stage 1): 175 slots for priority-ordered internal-evolution sources, 25 reserved slots for MFA (15 Daily Press Conference + 10 Foreign Minister Activities). Without the quota, MFA gets crowded out by higher-priority sources entirely.

---

## Voice format — English-only, 6 voices with progressive disclosure

Per design decision 2026-05-13 (revising the prior 2026-05-10 bilingual design): **voices are English translations only**. The verbatim Chinese was visually heavy and the English translations are already faithful (per the calibration table below), so the Chinese block was redundant on a page meant to be read.

**6 voices total per brief.** The first 3 are the priority selection (always visible). The remaining 3 are wrapped in a `<details class="voices-extras">` with a "Show 3 more voices" pill — native HTML expander, no JS, defaults closed so the editor's first-3 selection holds at first paint.

```html
<blockquote class="pull">
  <p>"China firmly opposes and strongly condemns Paraguay's actions."</p>
  <cite>MFA Spokesperson Guo Jiakun · May 12<sup><a class="cite" href="…">9</a></sup></cite>
</blockquote>
```

Trust posture is preserved by:
- Faithful (not interpretive) translation, calibrated via the diplomatic-vocabulary table below
- Direct .gov.cn citation in the `<cite>` — any reader can verify the source
- Diplomatic-glossary calibration so escalation/de-escalation language translates with its proper gradation

**Hard rules** (in synth prompt):
- Translation must be faithful, not interpretive. Translate the gradation (see calibration table), not the literal word.
- 6 voices, **different speaker AND different source category** for each across all 6 — synth must drop a slot rather than repeat a speaker.
- **Xi-first ordering rule (HARD).** If any picked article carries a Xi speech / statement / quotation usable per the recency rule, Xi is voice #1 in the visible-3. Never demoted below MFA / regulator / commentator.
- **Recency rule (HARD).** Voice quote dates ≤30 days. Exception only when the quote anchors a long-arc strategy-library doctrine actively invoked by today's bullets, AND the bullet names the anchored doctrine. Routine MFA / regulator slots cannot use the exception.

### Diplomatic vocabulary calibration

Chinese diplomatic language is graded — flat translations lose the gradation. The synthesizer's prompt includes this table verbatim:

| Chinese | English |
|---|---|
| 关切 | concerned (mild) |
| 严重关切 | grave concern (formal) |
| 坚决反对 | firmly opposes (immovable / red line) |
| 严正交涉 | filed formal protest |
| 强烈谴责 | strongly condemns (escalated) |
| 必将作出回应 | will certainly respond (action threat) |

Verified working in v3 brief — May 12 Guo Jiakun quote correctly rendered 坚决反对 + 强烈谴责 as "firmly opposes and strongly condemns".

---

## Headline + bullet caps (China-specific)

| Element | Cap | Notes |
|---|---|---|
| Headline | **12 words max** | Single action only, no semicolons, plain English (CAC → "internet regulator", NDRC → "central planners", etc.) |
| Dek (Day's Narrative) | 30–55 words, ≤2 sentences | Stance over scope; see `DEK.md` for the full voice spec |
| Bullet body | **25 words max** | Bold lead + one clear sentence + cite. No clause-stacking with em-dashes. No comma-chain enumeration of every measure in a policy |
| Voices | **6** (3 visible + 3 in `<details class="voices-extras">`) | English-only; Xi-first rule; ≤30-day recency rule with strategy-anchor exception |
| MFA spokesperson bullets | ≤2 routine denials | Picker quota guarantees MFA candidates exist |
| Routine CCDI bullets | **≤1** | Tier-leadership CCDI bypasses this cap (Politburo / CMC / minister / senior PLA / 双开 / 开除党籍 — see SQL keyword promotion below) |
| Provincial bullets | ≤3 | |
| China-US relations bullets | ≤3 | Don't let it become a US-China brief — internal-evolution framing prioritizes internal items |
| Qiushi-sourced bullets | must anchor | Bullet text must say "in a Qiushi speech [date]" / "Xi's [date] speech republished in Qiushi" / "Qiushi commentary [date]" — prevents long-arc doctrinal framing from reading as breaking news |

These caps are stricter than the US side; baked into the synth prompt in `scripts/synthesize_china.sh`.

---

## Source list

Source-of-truth: **`pipeline/config/china_sources.yaml`**.
Scraper: **`pipeline/scraper/china_scrape.py`**.
Invoked via: `docker compose run --rm pipeline python main.py --china-only` (or as part of daily.sh's parallel scrape stage).

**29 active sources** as of 2026-05-14, organized by editorial weight:

### Tier 1 — internal-policy core (priority 1)
| Source | Domain |
|---|---|
| Qiushi (Party Theoretical Journal) | qstheory.cn |
| People's Daily Politics | people.com.cn |
| People's Daily Opinion (Commentary) | people.com.cn |
| CPC News (中国共产党新闻网) | cpc.people.com.cn |
| State Council Policies | gov.cn |
| State Council Yaowen (Top News) | gov.cn |

### Tier 2 — economic / industrial regulators (priority 2)
| Source | Domain |
|---|---|
| NDRC News Releases | ndrc.gov.cn |
| PBOC Press Releases | pbc.gov.cn |
| MOF News | mof.gov.cn |
| MIIT News | miit.gov.cn |
| CAC Notices | cac.gov.cn |
| Stats Bureau | stats.gov.cn |
| NEA (国家能源局) | nea.gov.cn |

### Tier 3 — political + military signal (priority 3)
| Source | Domain |
|---|---|
| CCDI News | ccdi.gov.cn |
| NPC News | npc.gov.cn |
| Supreme People's Court | court.gov.cn |
| Supreme People's Procuracy | spp.gov.cn |
| MND (国防部) | mod.gov.cn |
| China Military Online | 81.cn |

### Tier 4 — financial regulators + commercial press (priority 4)
| Source | Domain |
|---|---|
| SAFE (Foreign Exchange) | safe.gov.cn |
| SASAC (SOE Regulator) | sasac.gov.cn |
| Caixin (财新) | caixin.com |
| China Electricity Council | cec.org.cn |

### Tier 5 — MFA voices (priority 5, with reserved 25-slot pool)
MFA Daily Press Conference (林剑 Lin Jian / 毛宁 Mao Ning / 郭嘉昆 Guo Jiakun), MFA News (Foreign Minister Activities)

### Tier 6 — Xinhua aggregation + Yicai (priority 5–6)
Xinhua News (homepage discovery), Xinhua Politics — Leaders, Yicai (第一财经)

### Tier 7 — provincial (priority 7)
Shanghai, Guangdong

### Held / blocked (`active: false`)
| Source | Issue |
|---|---|
| SCIO Press Conferences | HTTP 521 (Cloudflare origin unreachable) — re-probe weekly |
| NFRA (banking/insurance regulator) | Returns 215-byte stub — needs correct sub-path |
| Customs (海关总署) | Akamai-family JS bot challenge. Playwright solves the challenge but content paths still return 400; English mirror works but publishes ~2-4 narrative items/year. Parked indefinitely — trade data already covered by Stats Bureau + NDRC + State Council. See `memory/project_china_sourcing_probes.md` |
| Beijing Government | Flaky timeouts; covered by Shanghai/Guangdong |
| Zhejiang Government | Same as Beijing |
| CSRC | Pruned 2026-05-12 — 0 articles, mirrors gov.cn; covered by PBOC + SAFE |

---

## Architecture (live)

```
04:00 PDT  daily.sh — parallel scrape (rss + akamai + china) via `&` / `wait`
              └─ china_scrape.py runs 29 sources sequentially within itself
                 (per-source extraction, retries with exponential backoff)

07:30 PDT  synthesize_china.sh — autonomous daily synth
              ├─ Stage 0: china_world_context.sh — Claude WebSearch gathers
              │           ambient non-PRC framing (Reuters/AP/FT etc.). NEVER
              │           published; informs synth's framing only.
              ├─ Stage 0b: threads_today.sh — resolves threads.yaml to today's
              │            Day-N chip strings (Iran war, Trump-Xi summit, etc.)
              ├─ Stage 1: SQL pre-filter (two-pool design)
              │     ├─ internal_pool: 175 slots, priority-ordered, MFA excluded
              │     │     └─ CCDI tier-leadership keyword promotion: titles
              │     │        matching 政治局 / 中央军委 / 中央委员 / 上将 / 中将 /
              │     │        省委书记 / 副国级 / 副部级 / 部长 / 双开 (or full-text
              │     │        matching 开除党籍) auto-promote from priority 3 → 1.
              │     └─ voices_pool: 25 reserved MFA slots
              │           ├─ 15 MFA Daily Press Conference (most recent)
              │           └─ 10 MFA News (Foreign Minister Activities, most recent)
              ├─ Stage 2: Claude picker (~50 picks, ≥6 MFA required for voices)
              ├─ Stage 3: SQL fetch full text (5000 char LEFT)
              ├─ Stage 4: Claude synthesizer
              │     ├─ Headline ≤12 words; dek per DEK.md (present-tense voice)
              │     ├─ Thread strip (chips from .run/threads_china.txt)
              │     ├─ TOP EVENTS — 3 bullets (most consequential; cites 1-3)
              │     ├─ 6 voices (English-only); Xi-first; ≤30-day recency
              │     │   • First 3 visible
              │     │   • 3 more in <details class="voices-extras">
              │     ├─ OUTSIDE THE GATE — 3 bullets (cites a-c)
              │     │   non-PRC government voices that bear on China:
              │     │   near-orbit partners (Russia MID, Iran MFA,
              │     │   Pakistan FO, KCNA) + cross-Strait counterpart
              │     │   (Taiwan MOFA, Taiwan Presidential Office).
              │     │   Conditional: omitted if no material today.
              │     │   Items also appear in Sources as <ol type="a">.
              │     ├─ Strategic Backdrop (2-3 doctrines, collapsible-open)
              │     ├─ MORE EVENTS — 6 bullets in <details class="more-events">
              │     │   (cites 4-9; collapsed by default; 25-word cap;
              │     │   CCDI cadence rule; Qiushi anchor)
              │     │   (Note: positioned at the bottom of the brief,
              │     │    immediately before Sources)
              │     ├─ Five-Year Plan static anchor (collapsible-open)
              │     ├─ "This week" synopsis (injected at runtime by
              │     │   inject_weekly_preview.py — headline + 2-3
              │     │   sentence lead + link to /china/weekly/)
              │     ├─ Sources block (collapsible-open)
              │     ├─ Footer nav (Archive / Weekly / About / Sources)
              │     └─ Render into research/prototype_china_2026-05-12.html
              ├─ Stage 5: deploy to local nginx /china/
              └─ Stage 6: deploy to S3 /china/ + CloudFront invalidate

08:00 PDT  daily_digests.sh — refresh secondary surfaces
              ├─ weekly.sh — full weekly digest at /china/weekly/
              ├─ archive_index.py — rebuilds /china/archive/ listing
              ├─ inject_weekly_preview.py — patches "This week" section
              │                              on today's daily with the
              │                              fresh weekly's headline+lead+events
              ├─ build_sitemap.py — refreshes sitemap.xml
              └─ threads_propose.sh — Claude analyzer surfaces candidate
                                       new threads from past 14 days (editor-
                                       review only, never auto-merged)
```

**Output URLs:**
- Daily: `https://briefer.news/china/`
- Weekly: `https://briefer.news/china/weekly/` (daily-rolling 7-day window)
- Archive: `https://briefer.news/china/archive/`

---

## Editorial direction — landed 2026-05-14

The four direction items captured 2026-05-12 are now implemented:

1. **Voice ordering — Xi at top.** *Landed.* Synth prompt has a HARD ORDERING RULE: if any picked article carries a Xi speech/statement/quotation (and is usable per the recency rule), Xi is voice #1 in Selected view. Never demoted below MFA / regulator / commentator. Falls back to editorial importance only when no usable Xi material is in the picks.

2. **Quote freshness.** *Landed.* Synth prompt has a HARD RECENCY RULE: voice quote dates within 30 days of synth date, measured by the date in `<cite>`. Exception: a quote older than 30 days is allowed ONLY if it anchors a long-arc doctrine from the strategy library being invoked by today's bullets — and the bullet must name the anchored doctrine. Routine MFA / regulator slots cannot use the exception.

3. **Structural anchors — strategy library.** *Built.* Eleven strategy docs in `pipeline/config/strategy/` (14fyp, 15fyp, bri, carbon_dual_control_30_60, civil_military_fusion, common_prosperity, dual_circulation, energy_security_internal_transition, gdi_gsi, made_in_china_2025, new_quality_productive_forces). Each has a "Today's coverage triggers" section. The picker uses them as a tie-breaker; the synthesizer uses them to populate the Strategic Backdrop cards (2-3 fresh per day). The originally-planned single `china_structural_arcs.md` was superseded by the per-doctrine library.

4. **Dashboard framing — "from and to China".** *Reverted 2026-05-14 evening.* The Outside the Gate section briefly added a labeled exception for non-PRC sources but broke the brand's primary-source-only promise. Removed everywhere on the page. The synth still reads ambient world-context (Reuters/AP/etc.) for FRAMING — to know what the world is saying about today's PRC output — but never publishes or cites non-PRC content. Every cite in the brief points to .gov.cn or another Chinese-government primary source.

### Trust posture

Every bullet, voice, Strategic Backdrop card, Five-Year Plan reference, and Source entry cites a Chinese-government primary URL. The "Chinese government sources" tagline in the header describes the entire spine — no exceptions.

---

## Open editorial questions

Resolved 2026-05-14:

- **Naming.** *Decided: keep unified — "Briefer News — China".* Parent brand is "daily intelligence brief on government sources" and scales across editions. Strategic Backdrop and Five-Year Plan sections are explicitly cross-cutting frameworks; distinct branding would imply editorial independence we don't actually want. Distinct names also break the `briefer.news/china/` domain story.

- **Provincial coverage volume cap.** *Stable at ≤3/day.* Not a binding cap in practice (most days have 0 provincial bullets). Revisit only if Shanghai/Guangdong start producing higher-volume usable items.

- **Anti-corruption (CCDI) cadence.** *Decided 2026-05-14: hybrid discriminator landed.*
  - SQL pre-filter in `scripts/synthesize_china.sh` now promotes CCDI items to priority 1 when title matches 政治局 (Politburo) / 中央军委 (CMC) / 中央委员 (Central Committee member) / 上将 / 中将 (senior PLA) / 省委书记 (provincial Party Secretary) / 副国级 / 副部级 (vice-state / vice-ministerial) / 部长 (full minister) / 双开 (double-expulsion), OR full-text matches 开除党籍 (expelled from the Party).
  - Picker prompt adds the routine/tier-leadership distinction with explicit instruction to discriminate using political knowledge of named officials beyond keyword matching.
  - Synth prompt caps routine CCDI at 1 bullet; tier-leadership items bypass the cap and lead with named position + formal phrase ("expelled from the Party" / 双开).

- **Qiushi treatment.** *Decided 2026-05-14: anchor rule landed.* Synth prompt now requires bullets sourced from Qiushi to anchor explicitly to the speech / piece ("in a Qiushi speech [date]", "Xi's [date] speech republished in Qiushi", "Qiushi commentary [date]"). Prevents long-arc doctrinal framing from reading as breaking news.

- **The "to China" layer.** *Reverted 2026-05-14 evening — non-PRC-source content removed from the published page.* See direction item #4 above for the revert reasoning.

---

## What's done (chronological)

- **2026-05-10** — sources scaffolded (23 active), first scrape captured 499 articles across 11 sources, manual trial synth showed strong output
- **2026-05-12 morning** — 4 new sources added (MFA News, People's Daily Politics, People's Daily Opinion, CPC News), pattern fixes applied, fresh scrape recovered 12 zero-result sources
- **2026-05-12 afternoon** — `synthesize_china.sh` built end-to-end; v1 trial → v2 (China red theme + tighter word caps) → v3 (MFA quota + hard diverse-speaker rule) all run against fresh corpus
- **2026-05-12 evening** — multi-edition site shipped (selector at `/`, US at `/usa/`, China at `/china/`); China LaunchAgent at 07:30 PDT loaded
- **2026-05-13** — Voices switched bilingual → English-only; design tightening (P1/P2/P3 commits for headline/dek/typography)
- **2026-05-14 morning** — Trump-Xi summit transcript section + summit content
- **2026-05-14 afternoon** — Major editorial-improvement sweep:
  - `DEK.md` voice spec landed; both synths now route through it
  - Xi-first voice ordering (HARD), ≤30-day quote recency, Qiushi anchor rule
  - CCDI tier-leadership SQL keyword promotion + picker + bullet caps
  - `threads.yaml` + thread strip with daily-rolling Day-N counters
  - Weekly digest pipeline at `/china/weekly/` (daily-rolling)
  - "This week" preview section on the daily, drop-down for events
  - Voices grew 3 → 6 with `<details class="voices-extras">` for extras
  - Strategic Backdrop, Five-Year Plan, Sources all wrapped in collapsibles
  - PLA / military sources added: MND (mod.gov.cn) + China Military Online (81.cn) at tier 3 — closes the Taiwan-frame's largest source gap
  - About / Sources / Archive index pages built; unified footer nav
  - Reading-progress bar, SEO meta tags, sitemap.xml + robots.txt
  - Auto-thread proposer (`threads_propose.sh`) runs nightly, editor-review only
- **2026-05-14 evening** — Outside the Gate concept (briefly added that morning) reverted everywhere; gov-sources-only brand promise restored end-to-end. World-context still informs framing; nothing non-gov gets published or cited.
