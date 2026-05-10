# CHINA_BRIEF.md — China-source brief design + status

> Companion document to `BRIEF_STYLE.md` and `lens.md`, but for the China side.
> Captures editorial framing, source list, what's actually in the corpus today,
> and what's next. Started 2026-05-10 alongside the US brief going live at
> https://briefer.news.

---

## Why a China brief

The US-China axis is the defining geopolitical relationship of the era — `lens.md` already says this. Covering only the US side is half the picture. The world watches Chinese gov output patchily; there's editorial value in synthesizing it daily with the same rigor we apply to US gov output.

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
| Qiushi (Xi speeches, Party theory) | China Daily English coverage |

MFA daily press conferences stay valuable — they're the **best voice source** (daily transcripts of named spokespersons). But MFA content gets weighted by *substance*, not by volume.

---

## Voice format

Per design discussion 2026-05-10: **bilingual voices with Chinese verbatim + English translation, both shown.**

```
"中方坚决反对美方动用国家力量打压中国企业。"
"China firmly opposes the U.S. using state power to suppress Chinese enterprises."
— MFA Spokesperson Lin Jian, May 9 daily press conference [→ fmprc.gov.cn link]
```

Reasons:
- Preserves sourcing fidelity (verbatim Chinese can be checked against the .gov.cn URL)
- Readable for English audience
- Anchors the brief's "no spin, no paraphrase" trust posture

**Hard rule (parallel to BRIEF_STYLE.md cardinal sin):** never paraphrase inside Chinese quotes. Translation must be faithful, not interpretive.

### Diplomatic vocabulary calibration

Chinese diplomatic language is graded — flat translations lose the gradation. The synthesizer should know:

| Chinese | Common (weak) | Calibrated |
|---|---|---|
| 关切 | concerned | mild diplomatic note |
| 严重关切 | strongly concerned | formal grave concern |
| 坚决反对 | firmly opposes | immovable opposition (formal red line) |
| 严正交涉 | makes solemn representations | filed a formal protest |
| 强烈谴责 | strongly condemns | escalated language; significant |
| 必将作出回应 | will certainly respond | concrete action threat |

This calibration belongs in the synthesizer's prompt; not yet codified separately.

---

## Source list

Source-of-truth file: **`pipeline/config/china_sources.yaml`**.
Scraper module: **`pipeline/scraper/china_scrape.py`**.
Invoked via: `docker compose run --rm pipeline python main.py --china-only`

### Tier 1 (build first — internal-weight elevated)

| Source | Domain | Discovery | Why it matters |
|---|---|---|---|
| MFA Daily Press Conference | mfa.gov.cn | bespoke `mfa_press_conf` | Voices source; daily transcripts; spokespersons Lin Jian / Mao Ning / Guo Jiakun |
| State Council Policies | gov.cn | html_curl_cffi (custom `pages_content` selector) | Definitive policy text; Premier-signed orders |
| Xinhua via homepage | news.cn | bespoke `xinhua_home` | Aggregated wire content; ~128 URLs per fetch |
| NDRC | ndrc.gov.cn | html_curl_cffi | Economic planning announcements |
| PBOC | pbc.gov.cn | html_curl_cffi | Monetary policy; financial system signals |
| MOF | mof.gov.cn | html_curl_cffi (multi-subdomain) | Fiscal policy |
| MIIT | miit.gov.cn | html_curl_cffi (with retry) | Industrial / chip / AI policy |
| CAC | cac.gov.cn | html_curl_cffi (with retry) | Internet / data / algorithm regulation |
| Qiushi | qstheory.cn | html_curl_cffi (custom `detail` selector) | Xi speeches verbatim; Party theory — highest ideological signal |
| CCDI | ccdi.gov.cn | html_curl_cffi (with retry) | Anti-corruption / Party discipline |
| NPC | npc.gov.cn | html_curl_cffi | Legislative + leadership readouts |
| Supreme People's Court | court.gov.cn | html_curl_cffi | Major rulings, judicial reports |
| Supreme People's Procuracy | spp.gov.cn | html_curl_cffi (with retry) | Prosecutorial activity (often trails CCDI) |
| CSRC | csrc.gov.cn | html_curl_cffi | Securities regulator |
| SAFE | safe.gov.cn | html_curl_cffi | Foreign exchange / reserves |
| SASAC | sasac.gov.cn | html_curl_cffi | SOE management |
| Stats Bureau | stats.gov.cn | html_curl_cffi (custom `pages_content`) | Economic data drops |

### Tier 2 (provincial, by major economic center)

| Source | Domain | Status |
|---|---|---|
| Shanghai Government | shanghai.gov.cn | ✓ working |
| Beijing Government | beijing.gov.cn | flaky — needs retry |
| Guangdong Government | gd.gov.cn | ✓ working |
| Zhejiang Government | zj.gov.cn | flaky — needs retry |

### Held / blocked (`active: false` in yaml)

| Source | Issue |
|---|---|
| SCIO Press Conferences | HTTP 521 (Cloudflare origin error) on initial probe; retry later |
| NFRA (banking/insurance regulator) | Returns 215-byte stub — needs correct sub-path |
| Customs (海关总署) | HTTP 412 — needs specific header set |

---

## Current corpus (as of 2026-05-10)

First full china scrape ran 2026-05-09 → 2026-05-10. Captured **499 articles across 11 sources, 862 KB of Chinese-language text.** All articles tagged `language='zh'` in the `articles` table.

| Source | Articles | Avg chars |
|---|---|---|
| Supreme People's Procuracy | 90 | 2,387 |
| Guangdong Government | 69 | 1,231 |
| Xinhua News (homepage) | 63 | 1,347 |
| SAFE | 62 | 1,634 |
| CAC Notices | 61 | 1,251 |
| Qiushi | 58 | 2,735 |
| MFA Daily Press Conference | 40 | 1,968 |
| SASAC | 30 | 1,299 |
| MOF News | 15 | 1,195 |
| Shanghai Government | 8 | 1,366 |
| State Council Policies | 3 | 5,215 |

### Pattern-fix backlog (12 sources returned 0 articles)

The first scrape captured 11 of 23 active sources. The remaining 12 are accessible (probes confirm HTTP 200) but the `link_pattern` regex in `china_sources.yaml` doesn't match what's in those listings. To-fix:

State Council Yaowen, Xinhua Politics-Leaders, NDRC, PBOC, MIIT, Stats Bureau, CCDI, NPC, Supreme Court, CSRC, Beijing, Zhejiang.

These are 30-second probes each — fetch listing, find actual URL pattern, update yaml. Highest-value to fix first (per internal-weight): **NDRC, PBOC, MIIT, CCDI, NPC**.

---

## Architecture (planned, not yet built)

Mirroring the US brief's autonomous flow:

```
04:00 PDT  daily.sh — extend to also call --china-only after --akamai-only
07:30 PDT  synthesize_china.sh — NEW (US synth runs at 07:00; offset 30min for resource separation)
              ├─ Stage 0: china_world_context.sh — what global outlets say about China today
              │  + china_structural_arcs.md — slow-changing internal-evolution themes (refresh monthly)
              ├─ Stage 1: SQL pre-filter on language='zh'
              ├─ Stage 2: Claude picker (with internal-weight + diplomatic-glossary instruction)
              ├─ Stage 3: SQL fetch full text
              ├─ Stage 4: Claude synthesizer — bullets in English with Chinese citations,
              │  voices bilingual (Chinese verbatim + English translation)
              ├─ Stage 5: deploy to local nginx volume (/china subpath)
              └─ Stage 6: deploy to S3 + CloudFront invalidate (/china/index.html)
```

**Output URL planned**: `https://briefer.news/china/` (subpath on existing domain) or `https://china.briefer.news/` (subdomain — would need ACM cert update).

---

## What's next

In rough order:

1. **Fix the 12 zero-result source patterns** (NDRC, PBOC, MIIT, CCDI, NPC priority). ~30 min total.
2. **Run a second china scrape** with the patterns fixed — should land another ~300-500 articles.
3. **Build `scripts/synthesize_china.sh`** mirroring `synthesize.sh` shape, with China-specific prompts. Includes diplomatic-glossary table inline.
4. **Write `china_structural_arcs.md`** — 8-12 slow-changing internal-evolution themes (real-estate stress, demographic shift, AI/chips sovereignty, Common Prosperity, energy transition, political consolidation, etc.).
5. **Build `scripts/world_context_china.sh`** — Claude WebSearch tuned to China-internal narrative arcs.
6. **Manual trial synthesis** — run synthesize_china.sh on the captured corpus, look at what comes out, iterate on prompts before automating.
7. **New LaunchAgent** `news.briefer.synthesize.china` at 07:30 once trial output is publishable quality.
8. **Deploy** to `/china` subpath on briefer.news.

---

## Open editorial questions

- **Naming**: "Briefer News — China" or distinct branding?
- **English-only headlines**: yes (audience is English-reading), but should bullets be English with Chinese citations only, or include Chinese-original snippets inline alongside the English description?
- **Provincial coverage volume cap**: 4 provinces × ~70 articles each could swamp the picker. Hard cap at e.g. 5 provincial bullets per brief?
- **Anti-corruption (CCDI) coverage cadence**: high-volume, low-individual-event-importance most days, then occasional senior-official fall is huge. Picker needs to discriminate "routine vs. tier-leadership" cases.
- **Qiushi treatment**: Xi speeches are long. Excerpting verbatim vs. summarizing? Probably excerpt for voices, summarize for bullets.
- **When to flip the China brief on for autonomous publish**: only after several days of manual trials confirming editorial quality.
