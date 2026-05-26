#!/bin/bash
# briefer.news — China-source brief synthesizer.
#
# Parallels scripts/synthesize.sh for the China side. Reads from articles
# tagged language='zh', applies internal-evolution editorial priority per
# CHINA_BRIEF.md, produces a bilingual brief deployed to /china/ on the
# live site.
#
# Triggered manually for now; once output is publishable quality, will be
# wired to a third LaunchAgent at 07:30 (offset from US synth at 07:00).
#
# Failure behavior: any stage fails → log, exit 0, leave previous brief.

set +e

REPO=/Users/maxgoshay/code/briefernewsapp
cd "$REPO"

LOG_DIR="$REPO/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/synthesize-china-$(date +%Y%m%d).log"
exec >> "$LOG_FILE" 2>&1

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "China synthesis starting at $(date)"
echo "═══════════════════════════════════════════════════════════════"

DOCKER=/usr/local/bin/docker
CLAUDE=/Users/maxgoshay/.local/bin/claude
TODAY=$(date +%Y-%m-%d)
RUN_DIR="$REPO/.run"
mkdir -p "$RUN_DIR"

if [ ! -x "$CLAUDE" ]; then
  echo "ERROR: claude CLI not at $CLAUDE — bailing"
  exit 0
fi
if ! "$DOCKER" ps --format '{{.Names}}' | grep -q briefer_postgres; then
  echo "ERROR: briefer_postgres not running — bailing"
  exit 0
fi

# ── Preflight: abort before the expensive synth if the pipeline is broken ───
# Catches the failure classes that have burned a full turn budget for nothing
# (heredoc backticks, syntax errors, missing spec files, dead corpus). Cheap,
# no Claude calls. A hard failure skips the synth and leaves yesterday's brief.
echo ""
echo "--- Preflight ---"
if ! bash "$REPO/scripts/preflight.sh"; then
  echo "ERROR: preflight failed — skipping synth, leaving yesterday's brief in place"
  exit 0
fi

# China source allowlist + priority. Internal-evolution weighting per CHINA_BRIEF.md.
ALLOWLIST_SQL="
  WITH allowlist(name, priority) AS (VALUES
    -- A: top-tier internal Party / policy text
    ('Qiushi (Party Theoretical Journal)', 1),
    ('CPC News (中国共产党新闻网)', 1),
    ('People''s Daily Politics', 1),
    ('People''s Daily Opinion (Commentary)', 1),
    ('State Council Policies', 1),
    ('State Council Yaowen (Top News)', 1),
    -- B: economic / industrial regulators (internal-economic core)
    ('NDRC News Releases', 2),
    ('PBOC Press Releases', 2),
    ('MOF News', 2),
    ('MIIT News', 2),
    ('CAC Notices', 2),
    ('Stats Bureau', 2),
    -- B2: military signal sources (added 2026-05-14; Taiwan-frame editorial center)
    ('MND (国防部)', 3),
    ('China Military Online (81.cn)', 3),
    -- C: political signals
    ('CCDI News', 3),
    ('NPC News', 3),
    ('Supreme People''s Court', 3),
    ('Supreme People''s Procuracy', 3),
    -- D: financial regulators
    ('CSRC (Securities Regulator)', 4),
    ('SAFE (Foreign Exchange)', 4),
    ('SASAC (SOE Regulator)', 4),
    -- D2: Chinese commercial / professional press (added 2026-05-12)
    ('Caixin (财新)', 4),
    ('Yicai (第一财经)', 5),
    -- D3: Energy regulators / sector (added 2026-05-12)
    ('NEA (国家能源局)', 2),
    ('China Electricity Council (中国电力企业联合会)', 4),
    -- E: MFA — voices source, lower selection priority but high voice value
    ('MFA Daily Press Conference', 5),
    ('MFA News (Foreign Minister Activities)', 5),
    -- F: Xinhua aggregation
    ('Xinhua News (homepage discovery)', 6),
    ('Xinhua Politics — Leaders', 6),
    -- G: provincial
    ('Shanghai Government', 7),
    ('Beijing Government', 7),
    ('Guangdong Government', 7),
    ('Zhejiang Government', 7)
  )
"

# Title-noise filter — Chinese gov pages have specific noise patterns
NOISE_FILTER="
  AND a.title NOT ILIKE '%系统维护%'
  AND a.title NOT ILIKE '驻外团、处%'
  AND a.title NOT ILIKE '%国资数据%'
  AND a.title NOT ILIKE '数据（%'
  AND a.title NOT ILIKE '行业\\r%'
  AND a.title NOT ILIKE '%首页%'
  AND a.title NOT ILIKE '局领导%'
  AND a.title NOT ILIKE '%招标公告%'
  AND a.title NOT ILIKE '%意见征求%'
  AND a.title NOT ILIKE '%公开征求%意见%'
  AND a.title NOT ILIKE '通过云计算服务安全评估%'
  AND a.title NOT ILIKE '%政府信息公开工作年度报告%'
"

# ── Stage 0: China world-context (inbound signals, ambient framing) ─────────
# Reference material only — never cited or quoted in the brief. Synth uses it
# to calibrate framing emphasis and to optionally surface "outside-the-gate"
# acknowledgements. Non-fatal: if it fails, synth proceeds without it.
echo "--- Stage 0: china world-context (Claude WebSearch) ---"
"$REPO/scripts/china_world_context.sh"

# ── Stage 0b: continuity threads (resolve threads.yaml → today's chips) ─────
# Reads pipeline/config/threads.yaml and writes pre-rendered chip strings
# to .run/threads_china.txt. Synth renders these in a <p class="thread-strip">
# immediately after the dek. Failure non-fatal — synth skips the strip if
# the file is empty.
echo "--- Stage 0b: continuity threads ---"
"$REPO/scripts/threads_today.sh"

# ── Stage 1: SQL pre-filter ────────────────────────────────────────────────
# Two-pool design: 175 internal-evolution slots (priority-ordered, excluding MFA)
# + 25 reserved MFA slots (most recent across both MFA sources). Without the reserved
# quota, MFA gets crowded out of the top-200 by higher-priority sources, leaving the
# picker with no MFA candidates and the synth with no voices material.
META="$RUN_DIR/china_candidates_meta.json"
echo "--- Stage 1: SQL pre-filter to candidate metadata ---"
"$DOCKER" exec briefer_postgres psql -U briefer -d briefer -tA -c "
  ${ALLOWLIST_SQL},
  internal_scored AS (
    -- CCDI tier-leadership promotion: routine anti-corruption notices flood CCDI daily
    -- (deputy bureau chiefs under investigation). Tier-leadership falls (Politburo / CMC /
    -- minister / provincial party secretary / senior PLA general) are editorially huge but
    -- get drowned in volume. Promote those to priority 1 via title/body keyword match.
    SELECT
      a.id,
      s.name AS source,
      a.title,
      a.publish_date::date AS pub_date,
      a.url,
      a.scraped_at,
      LENGTH(a.full_text) AS tlen,
      CASE
        WHEN s.name = 'CCDI News' AND (
             a.title ILIKE '%政治局%'         -- Politburo
          OR a.title ILIKE '%中央军委%'       -- CMC
          OR a.title ILIKE '%中央委员%'       -- Central Committee member
          OR a.title ILIKE '%上将%'           -- General (senior PLA)
          OR a.title ILIKE '%中将%'           -- Lieutenant General (senior PLA)
          OR a.title ILIKE '%省委书记%'       -- Provincial Party Secretary
          OR a.title ILIKE '%副国级%'         -- vice-state level
          OR a.title ILIKE '%副部级%'         -- vice-ministerial level
          OR a.title ILIKE '%部长%'           -- full minister
          OR a.title ILIKE '%双开%'           -- "double-expulsion" (Party + position)
          OR a.full_text ILIKE '%开除党籍%'   -- expelled from the Party
        ) THEN 1
        ELSE al.priority
      END AS priority
    FROM articles a
    JOIN sources s ON a.source_id = s.id
    JOIN allowlist al ON al.name = s.name
    WHERE a.language = 'zh'
      AND a.full_text IS NOT NULL
      AND LENGTH(a.full_text) >= 300
      AND a.scraped_at >= NOW() - INTERVAL '7 days'
      AND s.name NOT LIKE 'MFA%'
      ${NOISE_FILTER}
  ),
  internal_capped AS (
    -- Per-source cap: no single source contributes more than 12 candidates,
    -- so a first-run back-catalogue dump (e.g. China Military Online's
    -- 269-article archive) cannot crowd the internal pool. The partition
    -- is ordered priority-first, so a promoted CCDI tier-leadership fall
    -- ranks ahead of routine CCDI volume and survives the cap.
    SELECT id, source, title, pub_date, url, priority,
      ROW_NUMBER() OVER (
        PARTITION BY source
        ORDER BY priority ASC, pub_date DESC NULLS LAST, scraped_at DESC, tlen DESC
      ) AS rn
    FROM internal_scored
  ),
  internal_pool AS (
    SELECT id, source, title, pub_date, url, priority
    FROM internal_capped
    WHERE rn <= 12
    ORDER BY priority ASC, pub_date DESC NULLS LAST
    LIMIT 175
  ),
  voices_pool AS (
    -- Sub-quota: 15 MFA Daily Press Conference (spokesperson transcripts) +
    -- 10 MFA News (foreign minister activities). Without the sub-quota, whichever
    -- source was scraped more recently fills all 25 slots and shuts out the other.
    SELECT id, source, title, pub_date, url, priority FROM (
      SELECT
        a.id,
        s.name AS source,
        a.title,
        a.publish_date::date AS pub_date,
        a.url,
        al.priority,
        ROW_NUMBER() OVER (PARTITION BY s.name ORDER BY a.scraped_at DESC, LENGTH(a.full_text) DESC) AS rn
      FROM articles a
      JOIN sources s ON a.source_id = s.id
      JOIN allowlist al ON al.name = s.name
      WHERE a.language = 'zh'
        AND a.full_text IS NOT NULL
        AND LENGTH(a.full_text) >= 300
        AND a.scraped_at >= NOW() - INTERVAL '7 days'
        AND s.name LIKE 'MFA%'
        ${NOISE_FILTER}
    ) ranked_mfa
    WHERE (source = 'MFA Daily Press Conference' AND rn <= 15)
       OR (source = 'MFA News (Foreign Minister Activities)' AND rn <= 10)
  ),
  ranked AS (
    SELECT * FROM internal_pool
    UNION ALL
    SELECT * FROM voices_pool
  )
  SELECT json_agg(json_build_object(
    'id', id, 'source', source, 'title', title,
    'pub_date', pub_date, 'url', url
  )) FROM ranked;
" > "$META"

if [ ! -s "$META" ] || [ "$(wc -c < "$META")" -lt 500 ]; then
  echo "ERROR: candidate metadata too small — bailing"
  cat "$META"
  exit 0
fi
N_META=$(jq 'length' "$META" 2>/dev/null || echo "?")
echo "China candidate pool: $N_META articles, $(wc -c < "$META") bytes"

# ── Stage 1b: Outside-the-Gate candidate pool ──────────────────────────────
# Non-PRC government voices that bear on China: near-orbit partners (Russia,
# Iran, Pakistan, North Korea) + cross-Strait counterpart (Taiwan). All
# government primary sources, routed via Google News site-restricted RSS.
# Taiwan items are included unfiltered (every Taiwan gov statement is
# cross-Strait relevant by context); other partner sources are keyword-
# filtered to surface only China-relevant items.
# Output: $OUTSIDE_META. Synth picks 3 of these to render in the
# "Outside the Gate" section between Voices and Strategic Backdrop.
# Non-fatal: if empty, synth omits the section entirely.
OUTSIDE_META="$RUN_DIR/china_outside_meta.json"
echo "--- Stage 1b: outside-the-gate SQL pre-filter ---"
"$DOCKER" exec briefer_postgres psql -U briefer -d briefer -tA -c "
  WITH outside_sources(name, is_taiwan) AS (VALUES
    ('Taiwan MOFA', true),
    ('Taiwan Presidential Office', true),
    ('Russia Foreign Ministry', false),
    ('Iran MFA', false),
    ('Pakistan Foreign Office', false)
    -- KCNA (DPRK) dropped 2026-05-25: Google News scrape returns
    -- only the source-name string for every item, no usable titles.
    -- Source stays in pipeline/config/sources.yaml in case a future
    -- direct scrape becomes worth the work.
  ),
  outside_candidates AS (
    -- Note: Google News scrapes save title + URL only; the extractor does not
    -- follow the news.google.com redirect to fetch full body text. For the
    -- Outside the Gate section the title IS the substance (each bullet is a
    -- one-line factual claim), so we filter on title presence + length, not
    -- full_text. The URL still resolves to the underlying gov source for cites.
    SELECT a.id, s.name AS source, a.title,
      a.publish_date::date AS pub_date, a.url, a.scraped_at
    FROM articles a
    JOIN sources s ON a.source_id = s.id
    JOIN outside_sources os ON os.name = s.name
    WHERE a.title IS NOT NULL
      AND LENGTH(a.title) >= 20
      -- Noise excludes: generic landing-page artifacts surfaced by Google
      -- News, administrative pages, source-name-only placeholders.
      AND a.title NOT ILIKE 'News Agency:Events%'
      AND a.title NOT ILIKE 'Ministry of Foreign Affairs of the Islamic Republic of Iran%'
      AND a.title NOT ILIKE 'Visa - Ministry%'
      AND a.title NOT ILIKE 'Consular Services - Ministry%'
      AND (a.publish_date >= NOW() - INTERVAL '14 days'
           OR (a.publish_date IS NULL AND a.scraped_at >= NOW() - INTERVAL '36 hours'))
      AND (
        os.is_taiwan = true
        -- Direct China references
        OR a.title ILIKE '%China%'
        OR a.title ILIKE '%PRC%'
        OR a.title ILIKE '%People''s Republic of China%'
        OR a.title ILIKE '%Beijing%'
        OR a.title ILIKE '%Xi Jinping%'
        OR a.title ILIKE '%Chinese%'
        OR a.title ILIKE '%Sino-%'
        -- Cross-Strait + Taiwan
        OR a.title ILIKE '%Taiwan%'
        OR a.title ILIKE '%Strait%'
        OR a.title ILIKE '%Cross-Strait%'
        -- China-adjacent territories
        OR a.title ILIKE '%Hong Kong%'
        OR a.title ILIKE '%Xinjiang%'
        OR a.title ILIKE '%Tibet%'
        -- PLA / military
        OR a.title ILIKE '%PLA%'
        OR a.title ILIKE '%South China Sea%'
        -- Multilateral frameworks where China is central
        OR a.title ILIKE '%BRICS%'
        OR a.title ILIKE '%SCO%'
        OR a.title ILIKE '%Shanghai Cooperation%'
        OR a.title ILIKE '%Belt and Road%'
        OR a.title ILIKE '%BRI %'
        OR a.title ILIKE '%CPEC%'
        OR a.title ILIKE '%Indo-Pacific%'
        OR a.title ILIKE '%Quad %'
        OR a.title ILIKE '%AUKUS%'
      )
  ),
  capped AS (
    SELECT id, source, title, pub_date, url,
      ROW_NUMBER() OVER (PARTITION BY source
        ORDER BY pub_date DESC NULLS LAST, scraped_at DESC) AS rn
    FROM outside_candidates
  )
  SELECT COALESCE(json_agg(json_build_object(
    'id', id, 'source', source, 'title', title,
    'pub_date', pub_date, 'url', url
  )), '[]'::json)
  FROM (SELECT * FROM capped WHERE rn <= 6 ORDER BY pub_date DESC NULLS LAST LIMIT 30) ranked;
" > "$OUTSIDE_META"

N_OUTSIDE=$(jq 'length' "$OUTSIDE_META" 2>/dev/null || echo "0")
echo "Outside-the-gate pool: $N_OUTSIDE articles, $(wc -c < "$OUTSIDE_META") bytes"
# Note: non-fatal — section omits entirely if pool is empty/sparse.

# ── Stage 2: Claude PICKER ──────────────────────────────────────────────────
PICK_PROMPT="$RUN_DIR/prompt_china_pick.txt"
PICKED="$RUN_DIR/china_picked_ids.json"
rm -f "$PICKED"

cat > "$PICK_PROMPT" <<EOF
You are the picker for the China-source brief of briefer.news.

Read these references first:
1. @${REPO}/CHINA_BRIEF.md — editorial framing for this brief specifically (READ THIS)
2. @${REPO}/BRIEF_STYLE.md — general style rules
3. @${REPO}/lens.md — interpretive framework
4. **Strategy library** — list and read the markdown files in @${REPO}/pipeline/config/strategy/ . Each describes a long-arc Chinese strategic doctrine (15FYP, 新质生产力, common prosperity, dual circulation, civil-military fusion, BRI, etc.) with a "Today's coverage triggers" section. Use these to give EXTRA WEIGHT to candidate articles whose titles touch operative doctrines.
5. **World-context (ambient signal):** @${REPO}/.run/china_world_context.md if it exists. This is REFERENCE MATERIAL ONLY — what non-Chinese sources are reporting about China today, inbound signals (sanctions / export controls / allied military), and politically-vital stories Chinese state press won't carry. Use it to bias toward candidates that engage with what the world is watching, AND to recognize when our corpus is silent on something globally significant.
6. @${META} — JSON candidates from Chinese-government sources

Pick approximately 50 article IDs you would want to read in full to write today's 9-bullet brief.

Editorial framing (per CHINA_BRIEF.md):
- INTERNAL CHINA EVOLUTION is the priority for the 9 BULLETS — what is China structurally becoming. State Council policy, NDRC/PBOC/MOF/MIIT/CAC regulation, CCDI anti-corruption, NPC legislative, Xi speeches in Qiushi/CPC News/People's Daily, judicial interpretations.
- **Strategic-doctrine resonance is a tie-breaker.** When two candidates are equally fresh and from equally-weighted sources, prefer the one whose subject matches a current-active doctrine in the strategy library. e.g., an article about AI agent rules > a routine notice, because 新质生产力 is operative; an article about cropland-protection rules > another routine notice, because the cadre-assessment / Beautiful China apparatus connects to common prosperity.
- **MFA spokespersons (林剑 Lin Jian, 毛宁 Mao Ning, 郭嘉昆 Guo Jiakun) are REQUIRED for the bilingual voices section.** You MUST include AT LEAST 6 MFA Daily Press Conference items in your 50 picks — ideally spread across all three spokespersons and the most recent 3-5 days. Without MFA picks the synthesizer cannot produce diverse voices. This is a hard requirement, not a preference. MFA items will not dominate the brief itself (only 1-2 will end up as bullets) but the synthesizer needs many MFA candidates to choose voice quotes from.
- **Xi mentions: at least 3 picks where 习近平 appears in title or you can infer Xi as author/speaker.** Xi-speech material is voice-section gold and frames everything else.
- De-prioritize routine procedural items (operational notices, sub-provincial bureaucratic items, repeat publications).
- **CCDI tier-leadership rule (HARD).** Most CCDI items are routine — a deputy bureau chief at a provincial agency under investigation. Cap routine CCDI at 1 in your 50-pick set. But when a CCDI item touches the senior leadership tier — Politburo members, CMC members, full ministers, provincial Party secretaries, senior PLA generals (上将/中将), "双开" (double-expulsion / 开除党籍) cases, or vice-state/vice-ministerial figures — it is editorially HUGE and must always be picked. The SQL pre-filter has already promoted these to priority 1; treat them as candidates equal to State Council policy releases. Use your political knowledge of named officials to discriminate beyond just keyword matching: if a name appears in the picks and you recognize it as senior-tier even without the keyword match, treat it as tier-leadership.
- Aim for diversity in the picks: at least one Xi-speech / Party-theory piece (≥3 with Xi), multiple economic/industrial regulators, at least one CCDI political-signal item, ≥6 MFA daily press conferences (REQUIRED for voices), some provincial/Xinhua aggregation, recent economic-data drops (CPI/PPI/GDP/PMI) if present.
- **Military signal source picks (NEW 2026-05-14):** MND (国防部) and China Military Online (81.cn) are the PLA-side primary feeds. Pick 1-2 military items when material exists — MND spokesperson statements (Taiwan / cross-Strait / US-China military / sanctions / exercises) are editorially central for the Taiwan-frame; 81.cn carries broader PLA doctrine, exercise readouts, and readiness signals. These weight equal to other political-signal sources, NOT below MFA. If a Taiwan-related MND statement is in the picks, treat it on par with Xi-speech material for headline priority.
- **Energy preference: include 1-2 energy-policy or energy-data items when material exists** (NEA capacity announcements, NDRC energy planning, State Council energy-related notices, EV/battery/solar industrial policy, carbon-market regulation). Editorial framing is **internal transition + capacity buildout** — what China is building (renewable + nuclear + EV + grid + battery industrial base), not import-source diplomacy.

Today is ${TODAY}.

Write the result as a JSON array of integer IDs (highest priority first) to: ${PICKED}

The file content should be ONLY the JSON array, e.g. [123, 456, 789]. No preamble, no markdown fences, no commentary.
EOF

echo "--- Stage 2: Claude picks ~50 articles ---"
"$CLAUDE" -p "$(cat "$PICK_PROMPT")" --max-turns 40 --permission-mode acceptEdits

if [ ! -s "$PICKED" ]; then
  echo "ERROR: claude did not write picked IDs to $PICKED — bailing"
  exit 0
fi
if ! jq -e 'type == "array"' "$PICKED" >/dev/null 2>&1; then
  echo "ERROR: $PICKED is not a JSON array — bailing. Contents:"
  cat "$PICKED"
  exit 0
fi
ID_COUNT=$(jq 'length' "$PICKED")
echo "Claude picked $ID_COUNT article IDs"
if [ "$ID_COUNT" -lt 10 ] || [ "$ID_COUNT" -gt 100 ]; then
  echo "ERROR: picked count $ID_COUNT outside reasonable range (10-100) — bailing"
  exit 0
fi

# ── Stage 3: SQL pull full text for picked IDs ─────────────────────────────
FULL="$RUN_DIR/china_candidates_full.json"
IDS_CSV=$(jq -r 'join(",")' "$PICKED")

echo "--- Stage 3: pulling full text for $ID_COUNT picked articles ---"
"$DOCKER" exec briefer_postgres psql -U briefer -d briefer -tA -c "
  SELECT json_agg(j ORDER BY pub_date DESC NULLS LAST)
  FROM (
    SELECT json_build_object(
      'id', a.id,
      'source', s.name,
      'title', a.title,
      'url', a.url,
      'pub_date', a.publish_date::date,
      'full_text', LEFT(a.full_text, 5000)
    ) AS j,
    a.publish_date::date AS pub_date
    FROM articles a
    JOIN sources s ON a.source_id = s.id
    WHERE a.id IN ($IDS_CSV)
  ) sub;
" > "$FULL"

if [ ! -s "$FULL" ] || [ "$(wc -c < "$FULL")" -lt 1000 ]; then
  echo "ERROR: full-text dump too small — bailing"
  exit 0
fi
echo "Full text dumped: $(wc -c < "$FULL") bytes"

# ── Stage 4: Claude SYNTHESIZER ─────────────────────────────────────────────
SYNTH_PROMPT="$RUN_DIR/prompt_china_synth.txt"
OUT="$RUN_DIR/china_today.html"
rm -f "$OUT"

cat > "$SYNTH_PROMPT" <<EOF
You are the synthesizer for the China-source brief of briefer.news.

Required reading (in order):
1. @${REPO}/CHINA_BRIEF.md — editorial framing for this brief specifically (READ THIS)
2. @${REPO}/BRIEF_STYLE.md — style rules; follow Accessibility rule on the headline
3. @${REPO}/lens.md — interpretive framework
4. @${REPO}/research/prototype_china_2026-05-12.html — visual template; preserve all CSS, header, footer, script
5. @${FULL} — full text of the articles the picker selected
6. **Strategy library** — list and read the markdown files in @${REPO}/pipeline/config/strategy/ . Each describes a long-arc Chinese strategic doctrine (15FYP, new quality productive forces, common prosperity, dual circulation, civil-military fusion, BRI, GDI/GSI, energy 30/60, energy security, etc.) with a "Today's coverage triggers" section. You'll use these to populate the Strategic Backdrop section.
7. **World-context (ambient signal, NEVER published):** @${REPO}/.run/china_world_context.md if it exists. What non-Chinese sources are reporting about China today — inbound signals, Western framing, politically-vital stories Chinese state press won't carry. Use this to (a) calibrate which bullets to emphasize and how, (b) inform the dek's selection of which events to name, (c) decide which Strategic Backdrop cards are most resonant. **NEVER cite, quote, or directly reproduce this file in the brief.** Every cite in the 9 BULLETS / Voices / Strategic Backdrop / numbered Sources must point to .gov.cn or another Chinese-government primary source. The 9-bullet spine of the brief is primary-government-sources-only.

8. **Outside the Gate candidates:** @${OUTSIDE_META} — non-PRC government voices that bear on China (near-orbit partners: Russia, Iran, Pakistan, North Korea; cross-Strait counterpart: Taiwan). Read this file and pick 3 to render in the Outside the Gate section per the OUTSIDE THE GATE SECTION instruction below. These are the explicit, labeled exception to the PRC-only rule — non-PRC GOV sources with their own letter-cite (a, b, c) markers and a separate listing in Sources. **Conditional:** if the file is empty or has 0 items, omit the Outside the Gate section entirely.

Today is ${TODAY}.

Output requirements:

HEADLINE: **HARD MAX 12 WORDS**. ONE clear action only — NO semicolons, NO "X; and also Y" compound structures. Plain English readable by someone who does NOT follow Chinese-government output daily. Avoid acronyms (NDRC → "central planners", PBOC → "central bank", CAC → "internet regulator", MIIT → "industry ministry", CCDI → "anti-corruption commission"). Avoid jargon — "autonomous AI agents" → "AI assistants" or "AI products"; "legislative agenda" → "lawmaking plan" or "new laws"; "Implementation Opinions" → "rules" or "policy". Anchor to the single most important specific.

Count your headline words. If over 12, cut.

DEK: Right below the headline, render a <p class="dek">…</p>. **Read @${REPO}/DEK.md before drafting.** It is short and binding — the dek is now a factual synopsis of the day's most important events (3–4 named items), not an editorial frame. Covers length (30–55 words), neutral-verb voice, banned framings (no stance, no falsifiable claims, no "while/even as" hedges, no "Beijing meets X from a posture of Y" or "X threads through today" template openers, no doctrine name-drops including NQPF / 15FYP / dual circulation / common prosperity / 30/60 / MIC2025 — those belong in Strategic Backdrop cards), and a pre-draft checklist. Follow every rule. Every event named in the dek must also appear in the Events list above.

CONTINUITY STRIP: Immediately after the dek (before the Voices section), render a <p class="thread-strip">…</p> with the active long-running threads.
- Read @${REPO}/.run/threads_china.txt. Each non-empty line is a pre-rendered chip string like "Day 76 · Iran war" or "Day 1 · Trump–Xi summit".
- For each line, render one chip: <span class="thread-chip"><b>[part before " · "]</b> &middot; [part after " · "]</span>. The bold-wrapped portion is everything up to and not including the " · " separator (e.g., "Day 76", "Day 1"). The trailing part is the thread name. Use &ndash; for en-dashes in names ("Trump–Xi summit" → "Trump&ndash;Xi summit").
- If threads_china.txt is empty or missing, omit the entire <p class="thread-strip"> block entirely. Do not render an empty strip.
- The strip is data; do not invent threads. Use only the chips in the file.
- When a long-running thread is the day's biggest event, the dek may name it factually (e.g. "Day 85 of the Iran war" if the Iran war is the day's dominant story). This is factual naming of today's events — not narrative editorializing — and counts toward the 3–4 event-naming density per DEK.md.

VOICES: **6 voices total** as <blockquote class="pull">. **ENGLISH-ONLY FORMAT** — each voice is a faithful English translation of the original Chinese quote. The translation MUST reflect the calibrated diplomatic vocabulary (see below) — translate the gradation, not the literal word. Each 12-30 words. Order by editorial importance: the first 3 are the priority selection (always visible). Wrap the additional 3 in a details block of this exact shape: <details class="voices-extras"><summary class="voices-extras-summary">Show 3 more voices</summary> then the 3 more <blockquote class="pull"> elements then </details> — native HTML expander, no JS. Both groups follow the same hard rules below (no repeat speakers, mix of registers).

Three registers, drawn from different source types. **HARD RULE: each voice must be from a DIFFERENT speaker AND a DIFFERENT source category.** Never quote the same person twice. If only 2 distinct categories are available in your picks, output 2 voices, not 3 with a repeat.
- One MFA spokesperson (Lin Jian / Mao Ning / Guo Jiakun) — attribute by English name + role. With 25 MFA articles in the candidate pool you should always have material here.
- One State Council / Xi speech / Party theory voice — anchor to the policy / speech
- One regulator / Party body / judicial voice — anchor to the regulation

**HARD ORDERING RULE — Xi leads when present.** If any picked article carries a Xi Jinping speech, statement, or direct quotation (and the quote is usable per the recency rule below), the Xi voice MUST be voice #1 in the Selected view. Never demote Xi below an MFA spokesperson, regulator, or any other voice. Xi is the ultimate signal source in PRC governance; placing him below subordinates understates where authority sits. If no usable Xi material is in the picks, fall back to editorial importance for #1.

**HARD RECENCY RULE — quote dates.** Voice quote dates must be within 30 days of today (${TODAY}). The date in the <cite> tag is the dispositive check — count back from today. Exception: a quote older than 30 days is allowed ONLY if it directly anchors a long-arc strategic doctrine from the strategy library (e.g., a Xi 14th/15th Five-Year Plan speech, a NQPF / Common Prosperity programmatic statement) that is actively being invoked by today's bullets. When you use this exception, you MUST also name the anchored doctrine in the bullet that connects to it, not just rely on the cite. Do NOT use older quotes for routine MFA / regulator / commentary slots — there is always fresh material there.

Voice HTML template (use this structure):
<blockquote class="pull">
  <p>&ldquo;[Faithful English translation]&rdquo;</p>
  <cite>[Speaker name + role] &middot; [Date]<sup><a class="cite" href="[URL]" title="[Source]" target="_blank" rel="noopener">[N]</a></sup></cite>
</blockquote>

Diplomatic vocabulary calibration — translate the gradation, not the literal word:
| Chinese | English |
|---|---|
| 关切 | concerned (mild) |
| 严重关切 | grave concern (formal) |
| 坚决反对 | firmly opposes (immovable / red line) |
| 严正交涉 | filed formal protest |
| 强烈谴责 | strongly condemns (escalated) |
| 必将作出回应 | will certainly respond (action threat) |

9 BULLETS in priority order. English narrative, with citation to .gov.cn URL in <sup>, plus <span class="when">Date · Source</span>. Internal-evolution priority — economic policy, Xi speeches, regulatory rules, political signals weight higher than diplomatic statements.

**BULLET LENGTH HARD MAX: 25 words per bullet body** (not counting the bold lead phrase). Structure: <b>Lead phrase.</b> One clear sentence stating the action + one key consequence or specific. NO clause-stacking with em-dashes. NO comma-chain enumerations of every measure in a policy — pick the ONE consequence that matters. If you need more, the reader can click through to the source.

Example of TOO LONG (don't do this):
"Cyberspace Administration, economic planner, and industry ministry jointly issued the first national framework for autonomous AI agents — requiring user consent for agent decisions, behavior-fencing controls, supply-chain security rules, and tiered governance by risk and sector."

Example of RIGHT length:
"<b>AI agent rules.</b> Internet regulator, central planners, and industry ministry jointly published China's first rulebook for AI agents — requiring user consent for any decision they take."

Count bullet words. If over 25, cut.

Bullet caps:
- ≤2 routine MFA spokesperson denial items
- ≤3 provincial items
- ≤3 items focused on China-US relations (we don't want this to become a US-China brief — internal-evolution framing means most bullets are about what China is doing internally)
- ≤1 routine CCDI item (deputy bureau chief / provincial agency-level investigations). EXCEPTION: tier-leadership CCDI items (Politburo / CMC / minister / provincial Party secretary / senior PLA general / "双开" cases / 开除党籍) do NOT count against this cap and should always be bullets when present. When you write such a bullet, lead with the named position and the formal phrase ("expelled from the Party" / "双开" double-expulsion) — distinguish clearly from routine notices.

**Qiushi anchor rule (HARD).** When a bullet sources from Qiushi (求是, Party Theoretical Journal), the bullet text MUST anchor to the speech / piece — explicitly name "in a Qiushi speech [date]", "Xi's [date] speech republished in Qiushi", or "Qiushi commentary, [date]". Otherwise the bullet reads as breaking news when the underlying material is long-arc doctrinal framing.

OUTSIDE THE GATE SECTION: directly after the Voices section closes and BEFORE Strategic Backdrop, render a short non-PRC-government section — an <h3 class="section-label">Outside the Gate</h3> then <ul class="items allied-items">. UP TO 3 bullets, drawn ONLY from items in @${OUTSIDE_META} (Taiwan MOFA, Taiwan Presidential Office, Russia Foreign Ministry, Iran MFA, Pakistan Foreign Office, KCNA — non-PRC government voices that bear on China). Same bullet structure as Events (bold lead, tight description, citation, date+agency tag), but cite markers are LOWERCASE LETTERS (a, b, c) so they do not collide with the Events numerals 1-9. **Outside the Gate items ALSO get entries in the Sources bibliography** — render them as a second list <ol type="a" class="sources-allied"> inside the <section class="sources"> (after the main 1-9 <ol>), containing 3 li in the same cite format as the numbered events. SELECTION GUIDANCE: prefer recency (last 7 days), distinct sources (do not render 3 from Taiwan if other voices are available), and items that materially engage with today's PRC story (the Russia/Iran/Pakistan/NK items already passed the China-keyword filter; Taiwan items are unfiltered because every Taiwan-gov statement is cross-Strait relevant by context — pick those that specifically respond to or anticipate today's PRC moves). CONDITIONAL: if @${OUTSIDE_META} is empty or no item is worth a slot today, OMIT the whole Outside the Gate section AND the corresponding sources-allied list — never render either empty.

STRATEGIC BACKDROP: After the Voices section AND the Outside the Gate section (if present), and after the summit transcript section if present, identify the **2 or 3 strategy documents** from @${REPO}/pipeline/config/strategy/ whose themes most strongly connect to today's items. (Note: the more-events <details class="more-events"> block sits at the BOTTOM of the brief, immediately before Sources — after Strategic Backdrop and Five-Year Plan render.) Read each doc's "Today's coverage triggers" section to judge fit. For each pick, write a card.

Pick rules:
- Each card connects to AT LEAST 2 of today's bullets via the strategy's themes.
- Prefer currently-active over closing/superseded doctrines (e.g., prefer "新质生产力" over "Made in China 2025" if both fit).
- Each card's blurb is **~30 words** linking the doctrine to today's specific items.

Strategic Backdrop HTML template (use this structure, 2-3 cards inside the .backdrop div). **Do NOT include a Chinese name line** — English name + status only.
<h3 class="section-label">Strategic Backdrop</h3>
<div class="backdrop">
  <article>
    <h4 class="strategy-title">[English name from doc's name: field]</h4>
    <p class="strategy-status">[Status from doc's status: field] &middot; [Period from doc's period: field]</p>
    <p class="strategy-blurb">[~30 words connecting today's items to this doctrine. Specific. Name today's bullets.]</p>
  </article>
  ...
</div>

SOURCES section: numbered <ol>, each <li> with publisher in <span class="pub">, article title, date, full URL.

Render as a COMPLETE HTML FILE matching ${REPO}/research/prototype_china_2026-05-12.html. Preserve all CSS, <header>, <footer>, <script> unchanged — including the China-flag SVG mark, the masthead tagline, the .backdrop CSS rules, AND the .fyp CSS rules. Only replace:
- <title>...</title> to a SEO-discoverable format: 2-3 key noun phrases from today's content (≤50 chars combined), then date, then brand+edition. Format pattern is "[KEY PHRASES] · [Month Day] · Briefer News China". Concrete example: "Xi welcomes Trump, Taiwan red line · May 14 · Briefer News China". Goal: ≤70 total chars. Avoid acronyms in the title; use plain-English noun phrases that match what a reader would Google (no NDRC / CAC / MIIT — use "central planners," "internet regulator," "industry ministry"; no "新质生产力 NQPF" — use "AI-and-tech doctrine" or the specific policy in plain words).
- <meta name="description" content="..."> — paste today's full dek text (verbatim, including punctuation). The dek is already 30-55 words, ideal length for search snippets and social previews.
- <meta property="og:title" content="..."> — same string as the <title> tag.
- <meta property="og:description" content="..."> — same as meta description (today's dek).
- <meta property="og:url" content="..."> — leave as "https://briefer.news/china/" (canonical URL, not the dated archive URL).
- <link rel="canonical" href="..."> — leave as "https://briefer.news/china/" (same canonical URL as og:url).
- <meta name="twitter:title" content="..."> — same as <title>.
- <meta name="twitter:description" content="..."> — same as meta description (today's dek).
- <div class="stamp">...</div> to today's date in ALL CAPS, e.g. literally "MAY 12, 2026" (not "May 12, 2026")
- <h2 class="headline">...</h2> per rules above
- Insert <p class="dek">...</p> IMMEDIATELY after </h2> (closing tag of headline) — the day's factual synopsis per DEK.md
- Insert <p class="thread-strip">...</p> IMMEDIATELY after </p> closing the dek — the continuity strip per rules above. Omit entirely if .run/threads_china.txt is empty.
- <div class="voices">...</div> — first 3 voices as <blockquote class="pull"> directly inside, then a <details class="voices-extras"><summary class="voices-extras-summary">Show 3 more voices</summary> with the additional 3 <blockquote class="pull"> elements inside. No "open" attribute on this details — extras default to hidden (preserving the priority-selection-first behavior).
- <ul class="items">...</ul> — the TOP EVENTS block (always visible): exactly 3 <li> elements. These are the day's THREE MOST CONSEQUENTIAL items, ordered by significance. Cite numerals 1-3.
- <details class="more-events"><summary class="more-events-summary">Show 6 more events</summary><ul class="items items-more">...</ul></details> — appears in the prototype at the BOTTOM of the brief, immediately before the Sources block (after Strategic Backdrop, Five-Year Plan, and the transcript section if present). Exactly 6 <li> elements inside the items-more <ul>, same bullet structure as the visible top 3. These are items 4-9 in significance order, with cite numerals 4-9. No "open" attribute — collapsed by default. Together with the top 3, the 9 events preserve the Sources bibliography numbering 1-9.
- <h3 class="section-label">Outside the Gate</h3> + <ul class="items allied-items">...</ul> — directly AFTER the Voices section closes and BEFORE Strategic Backdrop, per the OUTSIDE THE GATE SECTION instruction above. Omit BOTH the h3 and the ul entirely if there is no Outside the Gate material today.
- <ol type="a" class="sources-allied">...</ol> — a second ordered list with type="a" (renders a, b, c) inside <section class="sources">, immediately after the main 9-item <ol>. Contains 3 li, one per Outside the Gate item, in the same cite format as the numbered events. The letter labels (a, b, c) match the lowercase cite markers in the Outside the Gate bullets above. CONDITIONAL: if there is no Outside the Gate section today, OMIT this list entirely.
- The inner <div class="backdrop">...</div> of the Strategic Backdrop block (PRESERVE the wrapping <details class="collapsible-details" open><summary class="collapsible-summary">Strategic Backdrop</summary> and the closing </details>; only the inner backdrop div is replaced with 2-3 fresh strategy cards per today's items). Strategic Backdrop uses <details open> — expanded by default with a click-to-collapse chevron; the synth must not remove the wrapper, the summary text, or the "open" attribute.
- The inner <section class="sources"><ol>...</ol></section> (PRESERVE the wrapping <details class="sources-details" open><summary class="sources-summary">Sources</summary> and the closing </details>; only the inner section + ol is replaced). Sources uses <details open> — expanded by default with a click-to-collapse chevron; the synth must not remove the wrapper, the summary text, or the "open" attribute.
- The Five-Year Plan section is wrapped in <details class="collapsible-details" open><summary class="collapsible-summary">Five-Year Plan</summary>...</details>. The synth must PRESERVE this wrapper, the summary text, and the "open" attribute. The inner <article class="fyp"> content is unchanged — see the existing preserve rule for the Five-Year Plan section.

**Preserve unchanged:** the Five-Year Plan section (<h3 class="section-label">Five-Year Plan</h3> and the <article class="fyp">…</article> block immediately following it). This is a static long-arc anchor; do not edit its title, status, body, themes, or predecessor note. It sits between Strategic Backdrop and Sources.

Save the complete HTML to ${OUT}. Do not output the HTML to stdout — write to the file.
EOF

echo "--- Stage 4: Claude synthesizes the brief ---"
"$CLAUDE" -p "$(cat "$SYNTH_PROMPT")" --max-turns 100 --permission-mode acceptEdits

if [ ! -s "$OUT" ]; then
  echo "ERROR: claude did not write HTML to $OUT — bailing, leaving previous brief in place"
  exit 0
fi
if ! grep -q 'class="headline"' "$OUT" || ! grep -q 'class="items"' "$OUT" || ! grep -q 'class="sources"' "$OUT"; then
  echo "ERROR: $OUT missing required structural classes — leaving previous brief in place"
  exit 0
fi
if ! grep -q 'class="backdrop"' "$OUT"; then
  echo "WARN: $OUT missing Strategic Backdrop section — publishing anyway, but flag for review"
fi
echo "Brief HTML produced: $(wc -c < "$OUT") bytes"

# ── Stage 5: deploy to local nginx /china/ subpath ─────────────────────────
# Archive copy gets a rewritten canonical pointing to ITS dated URL so
# Google indexes each archive as unique content, not a dupe of today.
echo "--- Stage 5: deploying to nginx volume /china/ ---"
ARCHIVE_HTML="$RUN_DIR/china_today-archive.html"
/usr/bin/sed "s|<link rel=\"canonical\" href=\"https://briefer.news/china/\">|<link rel=\"canonical\" href=\"https://briefer.news/china/archive/${TODAY}.html\">|" "$OUT" > "$ARCHIVE_HTML"

"$DOCKER" run --rm \
  -v "$RUN_DIR":/src:ro \
  -v briefernewsapp_site_output:/dst \
  alpine sh -c "
    mkdir -p /dst/china /dst/china/archive
    cp /src/china_today.html /dst/china/index.html
    cp /src/china_today-archive.html /dst/china/archive/${TODAY}.html
    ls -la /dst/china | head -5
  "

# ── Stage 6: deploy to S3 /china/ + CloudFront invalidate ───────────────────
S3_BUCKET=briefer-news-site
DIST_ID=EMV1VIFYTSI3U
AWS=/Users/maxgoshay/.local/bin/aws

if [ -x "$AWS" ] && "$AWS" sts get-caller-identity >/dev/null 2>&1; then
  echo ""
  echo "--- Stage 6: publishing to S3 /china/ + CloudFront invalidation ---"
  "$AWS" s3 cp "$OUT" "s3://${S3_BUCKET}/china/index.html" \
    --content-type "text/html; charset=utf-8" \
    --cache-control "no-store, no-cache" \
    && echo "S3: china/index.html uploaded" \
    || echo "S3: china/index.html upload FAILED (non-fatal)"

  "$AWS" s3 cp "$ARCHIVE_HTML" "s3://${S3_BUCKET}/china/archive/${TODAY}.html" \
    --content-type "text/html; charset=utf-8" \
    --cache-control "public, max-age=31536000, immutable" \
    && echo "S3: china/archive uploaded (with archive canonical)" \
    || echo "S3: china/archive upload FAILED (non-fatal)"

  "$AWS" cloudfront create-invalidation \
    --distribution-id "$DIST_ID" \
    --paths "/china/index.html" "/china/archive/${TODAY}.html" \
    --query 'Invalidation.Id' --output text \
    && echo "CloudFront: invalidation created" \
    || echo "CloudFront: invalidation FAILED (non-fatal)"
else
  echo "--- Stage 6: skipped — AWS CLI unavailable or unauthenticated ---"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "China synthesis complete at $(date)"
echo "  Local:      http://localhost/china/"
echo "  CloudFront: https://d1sl4o5xm2ds0o.cloudfront.net/china/"
echo "  Public:     https://briefer.news/china/"
echo "═══════════════════════════════════════════════════════════════"
