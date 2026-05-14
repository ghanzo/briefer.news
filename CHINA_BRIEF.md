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

## Voice format — English-only

Per design decision 2026-05-13 (revising the prior 2026-05-10 bilingual design): **voices are English translations only**. The verbatim Chinese was visually heavy and the English translations are already faithful (per the calibration table below), so the Chinese block was redundant on a page meant to be read.

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
- Three voices, **different speaker AND different source category** for each — synth must drop to 2 voices rather than repeat a speaker.

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
| Bullet body | **25 words max** | Bold lead + one clear sentence + cite. No clause-stacking with em-dashes. No comma-chain enumeration of every measure in a policy |
| Voices | 3 (occasionally 2 if categories don't allow 3 distinct speakers) | Bilingual Chinese + English |
| MFA spokesperson bullets | ≤2 routine denials | Picker quota guarantees MFA candidates exist |
| Provincial bullets | ≤3 | |
| China-US relations bullets | ≤3 | Don't let it become a US-China brief — internal-evolution framing prioritizes internal items |

These caps are stricter than the US side; baked into the synth prompt in `scripts/synthesize_china.sh`.

---

## Source list

Source-of-truth: **`pipeline/config/china_sources.yaml`**.
Scraper: **`pipeline/scraper/china_scrape.py`**.
Invoked via: `docker compose run --rm pipeline python main.py --china-only` (or as part of daily.sh's parallel scrape stage).

**27 active sources** as of 2026-05-12, organized by editorial weight:

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

### Tier 3 — political / judicial (priority 3)
| Source | Domain |
|---|---|
| CCDI News | ccdi.gov.cn |
| NPC News | npc.gov.cn |
| Supreme People's Court | court.gov.cn |
| Supreme People's Procuracy | spp.gov.cn |

### Tier 4 — financial regulators (priority 4)
CSRC, SAFE, SASAC

### Tier 5 — MFA voices (priority 5, with reserved 25-slot pool)
MFA Daily Press Conference (林剑 Lin Jian / 毛宁 Mao Ning / 郭嘉昆 Guo Jiakun), MFA News (Foreign Minister Activities)

### Tier 6 — Xinhua aggregation (priority 6)
Xinhua News (homepage discovery), Xinhua Politics — Leaders

### Tier 7 — provincial (priority 7)
Shanghai, Beijing, Guangdong, Zhejiang

### Held / blocked (`active: false`)
| Source | Issue |
|---|---|
| SCIO Press Conferences | HTTP 521 (Cloudflare origin error) |
| NFRA (banking/insurance regulator) | Returns 215-byte stub — needs correct sub-path |
| Customs (海关总署) | HTTP 412 — needs specific header set |

---

## Architecture (live)

```
04:00 PDT  daily.sh — parallel scrape (rss + akamai + china) via `&` / `wait`
              └─ china_scrape.py runs 27 sources sequentially within itself
                 (per-source extraction, retries with exponential backoff)

07:30 PDT  synthesize_china.sh — autonomous daily synth
              ├─ Stage 1: SQL pre-filter
              │     ├─ internal_pool: 175 slots, priority-ordered, MFA excluded
              │     └─ voices_pool: 25 reserved MFA slots
              │           ├─ 15 MFA Daily Press Conference (most recent)
              │           └─ 10 MFA News (Foreign Minister Activities, most recent)
              ├─ Stage 2: Claude picker (~50 picks, ≥6 MFA required for voices)
              ├─ Stage 3: SQL fetch full text (5000 char LEFT)
              ├─ Stage 4: Claude synthesizer
              │     ├─ Bilingual voices (Chinese verbatim + English translation)
              │     ├─ Hard 12-word headline cap, 25-word bullet cap
              │     ├─ Diplomatic-glossary calibration table inline
              │     └─ Render into research/prototype_china_2026-05-12.html
              ├─ Stage 5: deploy to local nginx /china/
              └─ Stage 6: deploy to S3 /china/ + CloudFront invalidate
```

**Output URL:** `https://briefer.news/china/`

---

## Editorial direction — landed 2026-05-14

The four direction items captured 2026-05-12 are now implemented:

1. **Voice ordering — Xi at top.** *Landed.* Synth prompt has a HARD ORDERING RULE: if any picked article carries a Xi speech/statement/quotation (and is usable per the recency rule), Xi is voice #1 in Selected view. Never demoted below MFA / regulator / commentator. Falls back to editorial importance only when no usable Xi material is in the picks.

2. **Quote freshness.** *Landed.* Synth prompt has a HARD RECENCY RULE: voice quote dates within 30 days of synth date, measured by the date in `<cite>`. Exception: a quote older than 30 days is allowed ONLY if it anchors a long-arc doctrine from the strategy library being invoked by today's bullets — and the bullet must name the anchored doctrine. Routine MFA / regulator slots cannot use the exception.

3. **Structural anchors — strategy library.** *Built.* Eleven strategy docs in `pipeline/config/strategy/` (14fyp, 15fyp, bri, carbon_dual_control_30_60, civil_military_fusion, common_prosperity, dual_circulation, energy_security_internal_transition, gdi_gsi, made_in_china_2025, new_quality_productive_forces). Each has a "Today's coverage triggers" section. The picker uses them as a tie-breaker; the synthesizer uses them to populate the Strategic Backdrop cards (2-3 fresh per day). The originally-planned single `china_structural_arcs.md` was superseded by the per-doctrine library.

4. **Dashboard framing — "from and to China".** *Landed.* Implementation chosen 2026-05-14: a dedicated **Outside the Gate** section between the 9 bullets (and summit transcript, if present) and Strategic Backdrop. 3-5 short items per day, labeled "Inbound signals · non-PRC sources" with sepia left-rule and lowercase (a, b, c) cite markers to visually distinguish from the .gov.cn (1-9) bullet cites. Data flow: `china_world_context.sh` now emits an "Outside the Gate candidates" subsection — each candidate carries actor, action, date, publication, and a working URL. The synth picks 3-5 of these to render. The rest of `china_world_context.md` remains reference-only (never cited).

### Trust posture (post-change)

The brief's spine remains Chinese government primary sources — 9 bullets, voices, Strategic Backdrop, Five-Year Plan, Sources are all .gov.cn-cited. Outside the Gate is the single labeled exception, explicitly flagged as non-PRC source material. The "Chinese government sources" tagline in the header remains accurate as a description of the brief's main editorial spine.

---

## Open editorial questions

Resolved 2026-05-14:

- **Naming.** *Decided: keep unified — "Briefer News — China".* Parent brand is "daily intelligence brief on government sources" and scales across editions. Strategic Backdrop, Outside the Gate, and Five-Year Plan sections are explicitly cross-cutting frameworks; distinct branding would imply editorial independence we don't actually want. Distinct names also break the `briefer.news/china/` domain story.

- **Provincial coverage volume cap.** *Stable at ≤3/day.* Not a binding cap in practice (most days have 0 provincial bullets). Revisit only if Shanghai/Guangdong start producing higher-volume usable items.

- **Anti-corruption (CCDI) cadence.** *Decided 2026-05-14: hybrid discriminator landed.*
  - SQL pre-filter in `scripts/synthesize_china.sh` now promotes CCDI items to priority 1 when title matches 政治局 (Politburo) / 中央军委 (CMC) / 中央委员 (Central Committee member) / 上将 / 中将 (senior PLA) / 省委书记 (provincial Party Secretary) / 副国级 / 副部级 (vice-state / vice-ministerial) / 部长 (full minister) / 双开 (double-expulsion), OR full-text matches 开除党籍 (expelled from the Party).
  - Picker prompt adds the routine/tier-leadership distinction with explicit instruction to discriminate using political knowledge of named officials beyond keyword matching.
  - Synth prompt caps routine CCDI at 1 bullet; tier-leadership items bypass the cap and lead with named position + formal phrase ("expelled from the Party" / 双开).

- **Qiushi treatment.** *Decided 2026-05-14: anchor rule landed.* Synth prompt now requires bullets sourced from Qiushi to anchor explicitly to the speech / piece ("in a Qiushi speech [date]", "Xi's [date] speech republished in Qiushi", "Qiushi commentary [date]"). Prevents long-arc doctrinal framing from reading as breaking news.

- **The "to China" layer.** *Decided 2026-05-14 — Outside the Gate section live.* See direction item #4 above.

---

## What's done (chronological)

- **2026-05-10** — sources scaffolded (23 active), first scrape captured 499 articles across 11 sources, manual trial synth showed strong output
- **2026-05-12 morning** — 4 new sources added (MFA News, People's Daily Politics, People's Daily Opinion, CPC News), pattern fixes applied, fresh scrape recovered 12 zero-result sources
- **2026-05-12 afternoon** — `synthesize_china.sh` built end-to-end; v1 trial → v2 (China red theme + tighter word caps) → v3 (MFA quota + hard diverse-speaker rule) all run against fresh corpus
- **2026-05-12 evening** — multi-edition site shipped (selector at `/`, US at `/usa/`, China at `/china/`); China LaunchAgent at 07:30 PDT loaded; commit `bc68be1` pushed to ghanzo/briefer.news
