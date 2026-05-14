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
  internal_pool AS (
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
    ORDER BY priority ASC, pub_date DESC NULLS LAST, LENGTH(a.full_text) DESC
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
7. **World-context (ambient signal):** @${REPO}/.run/china_world_context.md if it exists. This is what non-Chinese sources are reporting about China today — inbound signals, Western framing, politically-vital stories Chinese state press won't carry. The file has TWO uses:
   - **Upper sections (Inbound signals / Western framing / Politically-vital / Calendar):** ambient framing ONLY. Use to (a) calibrate which bullets to emphasize and how, (b) inform the Day's Narrative dek's macro framing, (c) decide which Strategic Backdrop cards are most resonant. **NEVER cite, quote, or directly reproduce these sections in the brief.**
   - **"Outside the Gate candidates" subsection:** this IS citable. Each candidate has a publication + date + URL and is intended to be rendered directly in the new Outside the Gate page section (see Output requirements). Pick 3-5 of the candidates that best illustrate "what the world is sending toward China this week."

Today is ${TODAY}.

Output requirements:

HEADLINE: **HARD MAX 12 WORDS**. ONE clear action only — NO semicolons, NO "X; and also Y" compound structures. Plain English readable by someone who does NOT follow Chinese-government output daily. Avoid acronyms (NDRC → "central planners", PBOC → "central bank", CAC → "internet regulator", MIIT → "industry ministry", CCDI → "anti-corruption commission"). Avoid jargon — "autonomous AI agents" → "AI assistants" or "AI products"; "legislative agenda" → "lawmaking plan" or "new laws"; "Implementation Opinions" → "rules" or "policy". Anchor to the single most important specific.

Count your headline words. If over 12, cut.

DAY'S NARRATIVE: Right below the headline, render a <p class="dek">…</p>. **Read @${REPO}/DEK.md before drafting.** It is short and binding — covers required properties, banned openers (including "Beijing meets…posture of internal consolidation" which was reused verbatim across multiple recent days), the doctrine-name-drop prohibition (NQPF / 15FYP / dual circulation / common prosperity / 30/60 / MIC2025 do NOT belong in the dek — they go in Strategic Backdrop cards), hard-rule prohibitions, worked examples of what we've shipped vs. what we should ship, and a short pre-draft checklist. Follow every rule. The dek is the one line the brief is willing to be wrong about; it names the day's *shape*, not its contents.

CONTINUITY STRIP: Immediately after the dek (before the Voices section), render a <p class="thread-strip">…</p> with the active long-running threads.
- Read @${REPO}/.run/threads_china.txt. Each non-empty line is a pre-rendered chip string like "Day 76 · Iran war" or "Day 1 · Trump–Xi summit".
- For each line, render one chip: <span class="thread-chip"><b>[part before " · "]</b> &middot; [part after " · "]</span>. The bold-wrapped portion is everything up to and not including the " · " separator (e.g., "Day 76", "Day 1"). The trailing part is the thread name. Use &ndash; for en-dashes in names ("Trump–Xi summit" → "Trump&ndash;Xi summit").
- If threads_china.txt is empty or missing, omit the entire <p class="thread-strip"> block entirely. Do not render an empty strip.
- The strip is data; do not invent threads. Use only the chips in the file.
- DEK.md notes "anchor a thread that returns tomorrow" is one of the five qualities a good dek can have. These threads are the menu — when natural, the dek can reference "Day 76 of the Iran war" or similar to anchor a thread.

VOICES: **6 voices total** as <blockquote class="pull">. **ENGLISH-ONLY FORMAT** — each voice is a faithful English translation of the original Chinese quote. The translation MUST reflect the calibrated diplomatic vocabulary (see below) — translate the gradation, not the literal word. Each 12-30 words. Order by editorial importance: the first 3 are shown in the page's default "Selected" view; the next 3 appear when readers click "Expanded." Both sets follow the same hard rules below (no repeat speakers, mix of registers).

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

OUTSIDE THE GATE: After the 9 bullets (and after the summit transcript section, if present), render the "Outside the Gate" section using 3-5 candidates from the "Outside the Gate candidates" subsection of @${REPO}/.run/china_world_context.md.

Selection rules:
- Pick the candidates that best illustrate "what the world is sending toward China this week" — concrete ACTIONS by named actors (sanctions / export controls / military exercises / G7-G20 statements / tariffs / deals).
- Prefer freshness (≤7 days) and concrete actors. Skip pure analyst commentary.
- Each item must come WITH its citable source and URL from the world-context file. If a candidate lacks a working URL, do not render it.
- Items must be RECENT (date within last 14 days). Do not surface items older than 14 days even if the candidate file lists them.
- Maintain editorial neutrality. State the action; do not editorialize about Chinese reaction.

Outside the Gate HTML template (use this structure):
<div class="outside-gate-wrap">
  <h3 class="section-label">Outside the Gate</h3>
  <p class="og-subtitle">Inbound signals &middot; non-PRC sources</p>
  <ul class="outside-gate">
    <li><b>[Lead actor + action, ≤8 words].</b> [One-clause explanation, ≤20 words.]<sup><a class="cite" href="[URL]" title="[Source] &mdash; [short title], [date]" target="_blank" rel="noopener">[letter]</a></sup><span class="when">[Date short] &middot; [Source]</span></li>
    ...
  </ul>
</div>

Use lowercase letters (a, b, c, d, e) for Outside the Gate cite markers — keep them visually distinct from the numbered (1-9) bullet cites that point to .gov.cn sources. The visual cue helps readers parse "this section is the non-PRC exception."

STRATEGIC BACKDROP: After the Outside the Gate section, identify the **2 or 3 strategy documents** from @${REPO}/pipeline/config/strategy/ whose themes most strongly connect to today's items. Read each doc's "Today's coverage triggers" section to judge fit. For each pick, write a card.

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

Render as a COMPLETE HTML FILE matching ${REPO}/research/prototype_china_2026-05-12.html. Preserve all CSS, <header>, <footer>, <script> unchanged — including the China-flag SVG mark, the "Chinese government sources" tagline, the .backdrop CSS rules, AND the .fyp CSS rules. Preserve the <p class="weekly-link">...</p> nav element immediately after the Outside the Gate block — do not remove it. Only replace:
- <title>...</title> to a SEO-discoverable format: 2-3 key noun phrases from today's content (≤50 chars combined), then date, then brand+edition. Format: `[KEY PHRASES] · [Month Day] · Briefer News China`. Example: `Xi welcomes Trump, Taiwan red line · May 14 · Briefer News China`. Goal: ≤70 total chars. Avoid acronyms in the title; use plain-English noun phrases that match what a reader would Google (no NDRC / CAC / MIIT — use "central planners," "internet regulator," "industry ministry"; no "新质生产力 NQPF" — use "AI-and-tech doctrine" or the specific policy in plain words).
- <meta name="description" content="..."> — paste today's full dek text (verbatim, including punctuation). The dek is already 30-55 words, ideal length for search snippets and social previews.
- <meta property="og:title" content="..."> — same string as the <title> tag.
- <meta property="og:description" content="..."> — same as meta description (today's dek).
- <meta property="og:url" content="..."> — leave as "https://briefer.news/china/" (canonical URL, not the dated archive URL).
- <meta name="twitter:title" content="..."> — same as <title>.
- <meta name="twitter:description" content="..."> — same as meta description (today's dek).
- <div class="stamp">...</div> to today's date in ALL CAPS, e.g. literally "MAY 12, 2026" (not "May 12, 2026")
- <h2 class="headline">...</h2> per rules above
- Insert <p class="dek">...</p> IMMEDIATELY after </h2> (closing tag of headline) — the Day's Narrative per the rules above
- Insert <p class="thread-strip">...</p> IMMEDIATELY after </p> closing the dek — the continuity strip per rules above. Omit entirely if .run/threads_china.txt is empty.
- <div class="voices">...</div> with 3 bilingual blockquotes
- <ul class="items">...</ul> with exactly 9 <li> elements
- The Outside the Gate block (everything from <div class="outside-gate-wrap"> through its closing </div>) with 3-5 fresh inbound-signal items drawn from the world-context candidate list
- The Strategic Backdrop block (everything from <h3 class="section-label">Strategic Backdrop</h3> through </div>) with 2-3 fresh strategy cards per today's items
- The inner <section class="sources"><ol>...</ol></section> (PRESERVE the wrapping <details class="sources-details"><summary class="sources-summary">Sources</summary> and the closing </details>; only the inner section + ol is replaced). The Sources section is collapsed by default via native <details>; the synth must not remove the wrapper or the summary text.

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
if ! grep -q 'class="outside-gate"' "$OUT"; then
  echo "WARN: $OUT missing Outside the Gate section — publishing anyway, but flag for review"
fi
echo "Brief HTML produced: $(wc -c < "$OUT") bytes"

# ── Stage 5: deploy to local nginx /china/ subpath ─────────────────────────
echo "--- Stage 5: deploying to nginx volume /china/ ---"
"$DOCKER" run --rm \
  -v "$RUN_DIR":/src:ro \
  -v briefernewsapp_site_output:/dst \
  alpine sh -c "
    mkdir -p /dst/china /dst/china/archive
    cp /src/china_today.html /dst/china/index.html
    cp /src/china_today.html /dst/china/archive/${TODAY}.html
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

  "$AWS" s3 cp "$OUT" "s3://${S3_BUCKET}/china/archive/${TODAY}.html" \
    --content-type "text/html; charset=utf-8" \
    --cache-control "public, max-age=31536000, immutable" \
    && echo "S3: china/archive uploaded" \
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
