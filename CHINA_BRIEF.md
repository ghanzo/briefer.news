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

## Active editorial direction (forward-looking)

Captured 2026-05-12 evening; to address in upcoming sessions.

1. **Voice ordering — Xi at top.** When Xi is in the picks, he should lead the voices section rather than appearing in slot #2 or #3. Synth prompt's "three registers, different speaker" rule produces good diversity but doesn't enforce hierarchy. Fix: add explicit Xi-leads rule to synth prompt.

2. **Quote freshness.** v3 brief used a Xi quote from Feb 4 phone call to Trump (~3 months old). Looks misleading in a "daily brief" context. Add a recency rule: voice quotes ≤30 days unless explicitly anchoring a structural arc, with the date in the cite either way.

3. **Structural anchor docs.** Beyond daily output, brief should draw on long-arc strategy: 15th Five-Year Plan (15FYP), Common Prosperity, Belt and Road, Made in China 2025/2035, etc. **Pending build:** `china_structural_arcs.md` (8-12 themes) + Stage 0 `china_world_context.sh` analogous to the US side.

4. **Dashboard framing — "from and to China".** Page should function as a two-way information dashboard: signals FROM China (current — their official output) AND signals TO China (sanctions / trade actions / diplomatic moves / allied responses). Implementation TBD; likely needs a separate ingestion layer for the "to China" side. Clarify next session.

---

## Open editorial questions (still open)

- **Naming**: "Briefer News — China" or distinct branding?
- **Provincial coverage volume cap**: current cap of 3 working OK; revisit if provincial sources start producing more usable items.
- **Anti-corruption (CCDI) cadence**: high-volume low-individual-importance most days, occasional senior-official fall is huge. Picker needs to discriminate "routine vs. tier-leadership" — currently no explicit signal.
- **Qiushi treatment**: Xi speeches are long. Excerpting verbatim vs. summarizing? Currently excerpt for voices, summarize for bullets — working OK.
- **The "to China" layer**: see direction item #4 above.

---

## What's done (chronological)

- **2026-05-10** — sources scaffolded (23 active), first scrape captured 499 articles across 11 sources, manual trial synth showed strong output
- **2026-05-12 morning** — 4 new sources added (MFA News, People's Daily Politics, People's Daily Opinion, CPC News), pattern fixes applied, fresh scrape recovered 12 zero-result sources
- **2026-05-12 afternoon** — `synthesize_china.sh` built end-to-end; v1 trial → v2 (China red theme + tighter word caps) → v3 (MFA quota + hard diverse-speaker rule) all run against fresh corpus
- **2026-05-12 evening** — multi-edition site shipped (selector at `/`, US at `/usa/`, China at `/china/`); China LaunchAgent at 07:30 PDT loaded; commit `bc68be1` pushed to ghanzo/briefer.news
