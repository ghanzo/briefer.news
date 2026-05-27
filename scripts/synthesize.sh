#!/bin/bash
# briefer.news daily synthesis — Path B (auto-generate the brief).
# Triggered by ~/Library/LaunchAgents/news.briefer.synthesize.plist at 07:00 local.
#
# Two-stage Claude architecture:
#   1. SQL pre-filters to ~200 candidates (allowlist + recency + length + noise
#      filter). No AI here — just deterministic source/topic gating.
#   2. Claude PICKER reads BRIEF_STYLE.md + lens.md + the 200-article metadata
#      (titles/sources/dates only), picks ~50 with editorial diversity, writes
#      picked_ids.json.
#   3. SQL pulls full text for the picked IDs into candidates_full.json.
#   4. Claude SYNTHESIZER reads style guides + prototype HTML + the 50 full
#      articles, picks 9, writes today.html in the prototype's design.
#   5. Alpine container deploys today.html into the nginx volume.
#
# Failure behavior: any stage fails → log, exit 0, leave yesterday's brief live.

set +e

REPO=/Users/maxgoshay/code/briefernewsapp
cd "$REPO"

LOG_DIR="$REPO/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/synthesize-$(date +%Y%m%d).log"
exec >> "$LOG_FILE" 2>&1

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Synthesis starting at $(date)"
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

# ── Stage 0: world-context generation (ambient signal for picker + synth) ───
# Runs Claude with WebSearch to assemble what global outlets consider today's
# biggest stories. Saved to .run/world_context.md and referenced (optionally)
# by the picker and synthesizer prompts. Failure here is non-fatal — the
# picker/synth tolerate a missing or stale file.
echo ""
echo "--- Stage 0: world context ---"
"$REPO/scripts/world_context.sh"

# ── Stage 0b: continuity threads (resolve threads.yaml → today's chips) ─────
# Reads pipeline/config/threads.yaml and writes pre-rendered chip strings
# to .run/threads_us.txt. Synth renders these in a <p class="thread-strip">
# immediately after the dek. Failure non-fatal — synth skips the strip if
# the file is empty.
echo "--- Stage 0b: continuity threads ---"
"$REPO/scripts/threads_today.sh"

# Shared SQL fragment for the source allowlist + noise blacklist.
ALLOWLIST_SQL="
  WITH allowlist(name, priority) AS (VALUES
    -- A: structural foreign-policy / EOs / sanctions
    ('Federal Register — Executive Orders & Rules', 1),
    ('White House — News', 1),
    ('GovInfo — Presidential Documents', 1),
    ('State Dept — Press Releases', 1),
    ('State Dept — Secretary''s Remarks', 1),
    ('U.S. Treasury — Press Releases', 1),
    ('OFAC — Sanctions Actions', 1),
    ('USTR — Press Releases', 1),
    -- B: defense / military operations
    ('CENTCOM Press Releases', 2),
    ('DOD War.gov News Stories', 2),
    ('Department of Defense — News', 2),
    ('Joint Chiefs of Staff', 2),
    ('Navy.mil Press Releases', 2),
    ('U.S. Air Force', 2),
    -- B2: allied gov foreign-policy
    ('UK Ministry of Defence', 2),
    ('Australia DFAT — Departmental Media Releases', 2),
    ('Japan MoFA — Press Releases (EN)', 2),
    ('NATO News', 2),
    -- C: enforcement / cyber
    ('DOJ — Justice News (OPA)', 3),
    ('DOJ — National Security Division', 3),
    ('DOJ — Antitrust Press Room', 3),
    ('CISA — Alerts & Advisories', 3),
    -- D: economy / regulatory
    ('Federal Reserve — Press Releases', 4),
    ('Federal Reserve — Speeches', 4),
    ('GAO — Reports & Testimonies', 4),
    ('CBO — Publications', 4),
    ('BLS — Major Economic Indicators', 4),
    ('BEA — Releases', 4),
    ('NY Fed — Liberty Street Economics', 4),
    -- E: state regional desks
    ('State Dept — East Asia & the Pacific', 5),
    ('State Dept — Near East', 5),
    ('State Dept — Europe & Eurasia', 5),
    ('State Dept — South & Central Asia', 5),
    ('State Dept — Western Hemisphere', 5),
    ('State Dept — Africa', 5),
    ('State Dept — International Organizations', 5),
    ('State Dept — Diplomatic Security', 5),
    ('State Dept — Treaties (TIAS)', 5),
    -- F: other agencies
    ('DOE — Newsroom', 6),
    ('Federal Register — Public Inspection', 6),
    ('CBP — News', 6),
    ('FTC — Press Releases', 6),
    ('SEC — Press Releases', 6),
    ('NRC — Press Releases', 6),
    ('FERC — Federal Register (Rules & Orders)', 6),
    ('FDA — Press Announcements', 6),
    ('CFPB — Newsroom', 6),
    ('NASA — Breaking News', 6),
    ('NOAA — News', 6),
    ('EPA — News Releases', 6),
    ('NIH — News Releases', 6),
    ('CDC — Newsroom', 6),
    ('NIST — News', 6),
    ('FBI — National Press', 7),
    ('EIA — Today in Energy', 7),
    ('OilPrice.com — News', 8),
    ('Mining.com — Critical Minerals', 8)
  )
"

NOISE_FILTER="
  AND a.title NOT ILIKE '%sunshine act%'
  AND a.title NOT ILIKE 'Agency Information Collection%'
  AND a.title NOT ILIKE '%Hearings, Meetings, Proceedings%'
  AND a.title NOT ILIKE 'Combined Filings%'
  AND a.title NOT ILIKE 'Self-Regulatory Organizations%'
  AND a.title NOT ILIKE 'Antidumping or Countervailing%'
  AND a.title NOT ILIKE 'Safety Zone%'
  AND a.title NOT ILIKE 'Airspace Designations%'
  AND a.title NOT ILIKE '%Environmental Assessments%'
  AND a.title NOT ILIKE '%Environmental Impact Statements%'
  AND a.title NOT ILIKE 'Charter Amendments%'
  AND a.title NOT ILIKE 'Special Local Regulation%'
  AND a.title NOT ILIKE 'New Postal Products%'
  AND a.title NOT ILIKE 'Drug Products not Withdrawn%'
  AND a.title NOT ILIKE 'Airworthiness Directives%'
  AND a.title NOT ILIKE 'Special Observances%'
  AND a.title NOT ILIKE 'Guidance: % firing %'
  AND a.title NOT ILIKE 'Transparency data:%'
  AND a.title NOT ILIKE 'Guidance: Military low flying%'
  AND a.title NOT ILIKE 'Notice of OFAC Sanctions Action'
  AND a.title NOT ILIKE 'Air Plan Approval%'
  AND a.title NOT ILIKE 'Amendment of Class % Airspace%'
  AND a.title NOT ILIKE 'Approval and Promulgation%'
  AND a.title NOT ILIKE 'Air Quality Plan%'
  AND a.title NOT ILIKE 'Atlantic Highly Migratory Species%'
  AND a.title NOT ILIKE '%Outer Continental Shelf Lease%'
  AND a.title NOT ILIKE 'Semiannual Reporting%'
  AND a.title NOT ILIKE 'Risk Management and Financial Assurance%'
"

# ── Stage 1: SQL pre-filter to ~200 candidates ─────────────────────────────
META="$RUN_DIR/candidates_meta.json"
echo "--- Stage 1: SQL pre-filter to candidate metadata ---"
"$DOCKER" exec briefer_postgres psql -U briefer -d briefer -tA -c "
  ${ALLOWLIST_SQL},
  capped AS (
    -- Per-source cap: no single source may contribute more than 12 candidates.
    -- Without this, a source with a large back-catalogue scraped in one run
    -- (e.g. a first-run allied-gov archive dump, or GovInfo Bills' routine
    -- daily volume) floods the 200-slot pool and starves every other desk.
    SELECT
      a.id,
      s.name AS source,
      a.title,
      a.publish_date::date AS pub_date,
      a.url,
      al.priority,
      ROW_NUMBER() OVER (
        PARTITION BY s.name
        ORDER BY a.publish_date DESC NULLS LAST, a.scraped_at DESC, LENGTH(a.full_text) DESC
      ) AS rn
    FROM articles a
    JOIN sources s ON a.source_id = s.id
    JOIN allowlist al ON al.name = s.name
    WHERE a.full_text IS NOT NULL
      AND LENGTH(a.full_text) >= 500
      AND (
        a.publish_date >= CURRENT_DATE - INTERVAL '2 days'
        OR (a.publish_date IS NULL AND a.scraped_at >= NOW() - INTERVAL '36 hours')
      )
      ${NOISE_FILTER}
  ),
  ranked AS (
    SELECT id, source, title, pub_date, url, priority
    FROM capped
    WHERE rn <= 12
    ORDER BY priority ASC, pub_date DESC NULLS LAST
    LIMIT 200
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
echo "Candidates pool: $N_META articles, $(wc -c < "$META") bytes"

# ── Stage 2: Claude PICKER ──────────────────────────────────────────────────
PICK_PROMPT="$RUN_DIR/prompt_pick.txt"
PICKED="$RUN_DIR/picked_ids.json"
rm -f "$PICKED"

cat > "$PICK_PROMPT" <<EOF
You are the picker for briefer.news, a daily intelligence brief on US government and allied output.

Read these references first:
1. @${REPO}/BRIEF_STYLE.md — editorial style and priority rules
2. @${REPO}/lens.md — interpretive frame
3. @${META} — JSON array of today's candidate articles (id, source, title, pub_date, url) — already pre-filtered for noise

Optional ambient signal (read if present, treat as background not directive):
@${REPO}/.run/world_context.md — what global outlets consider today's biggest stories. Use it to navigate — when a US-gov candidate connects to or contextualizes a global narrative, that is a useful signal for selection. But your editorial decisions remain primary; do not pick a story just because it is in the world context, and do not skip a story because it is not.

Your job: pick approximately 50 article IDs you would want to read in full to write today's 9-bullet brief.

Pick using the BRIEF_STYLE priority order: structural foreign-policy moves → enforcement actions of national/international significance → cyber/national-security incidents → economic/procurement rules with broad effect → energy/infrastructure → diplomatic engagements → administrative.

Diversity requirement: ensure DEFENSE (CENTCOM, Navy, JCS, Air Force, War.gov), ENFORCEMENT (DOJ, CISA), and ECONOMIC (Federal Register Executive Orders & Rules, Treasury, Federal Reserve, BEA, BLS) get representation. ALLIED-GOV (UK MoD, UK FCDO, UK No.10, NATO, Australia DFAT, Japan MoFA, Taiwan MOFA, G7 Council (via Global Affairs Canada)) — pick 3-5 allied-gov items when material exists; these populate the separate Allied Governments section, NOT the Events list, especially Indo-Pacific / Taiwan / AUKUS / Five Eyes / NATO-axis stories. State Dept will dominate by volume — do not let it crowd out the other categories.

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
FULL="$RUN_DIR/candidates_full.json"
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
      'full_text', LEFT(a.full_text, 4000)
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
SYNTH_PROMPT="$RUN_DIR/prompt_synth.txt"
OUT="$RUN_DIR/today.html"
rm -f "$OUT"

cat > "$SYNTH_PROMPT" <<EOF
You are the synthesizer for briefer.news.

Required reading (in order):
1. @${REPO}/BRIEF_STYLE.md — editorial style; follow exactly
2. @${REPO}/lens.md — interpretive frame
3. @${REPO}/research/prototype_us_2026-05-12.html — the visual template you must mirror
4. @${FULL} — full text of the articles the picker selected

Ambient signal (reference only, NEVER published):
@${REPO}/.run/world_context.md if it exists. What non-US-gov sources (Reuters, AP, FT, Bloomberg, BBC, etc.) are reporting about today's stories. Use this to frame your bullets in their wider narrative arc when natural (e.g., anchoring a CENTCOM-sourced bullet to "the deteriorating April 8 ceasefire" if that is the global frame). **Every claim and citation in the bullets must come from the US-gov articles in the candidates list — the world context informs framing, not facts.** Do NOT cite the world context anywhere in the rendered HTML; do NOT quote it; do NOT render any non-gov source on the page. The brand promise is primary-government-sources-only.

Today is ${TODAY}.

Your job:
- From the U.S.-federal-government candidates, select the 9 most consequential items for the EVENTS list per BRIEF_STYLE.md priority order. ORDER MATTERS: items 1-3 are the day's MOST consequential and render in the visible top-events block; items 4-9 render in the collapsed "Show 6 more events" details. Pick the 3 most important deliberately — they are what every visitor sees.
- Apply BRIEF_STYLE.md rules: at most 2 DOJ items, at most 3 purely-domestic items, mix of registers in the voices.

- SOURCE HIERARCHY (read BRIEF_STYLE.md "Source hierarchy — U.S. government leads" carefully — this is binding):
  - The brief's spine is U.S. FEDERAL GOVERNMENT primary sourcing. These FOUR sources are ALLIED governments, NOT the U.S. government: "UK Ministry of Defence", "NATO News", "Australia DFAT — Departmental Media Releases", "Japan MoFA — Press Releases (EN)". Every OTHER source in the candidate set is U.S. federal government.
  - EVENTS LIST: the 9 Events bullets are U.S.-FEDERAL-GOVERNMENT items ONLY. An allied-government item NEVER appears in the Events list. A significant allied-sourced story goes in the separate Allied Governments section (see the ALLIED GOVERNMENTS SECTION instruction below) — never in Events.
  - HEADLINE: summarizes the most consequential U.S.-federal-government item. A second clause MAY reference an allied-sourced story for context, but the verifiable spine is U.S.-gov. Never lead with a story whose only source is an allied government.
  - DEK: every event named in the dek must appear in the Events list (a U.S.-government item). The dek is a factual synopsis — see DEK.md for the binding voice + content rules.
- HEADLINE — **5 to 8 words. One event.** Statement of fact, plain English. The day's single most consequential outcome named with neutral verbs (sign, announce, publish, reject, close, fail, host, award). NO editorial verbs ("hardens", "answers with", "responds to", "underscores"). NO unfamiliar personal names — use country or institution (Rubio → U.S.; Jaishankar → India). Globally-recognized names are fine (Xi, Trump, Putin, Modi, Netanyahu, Erdoğan, Kim Jong Un). NO acronyms (NPT, Quad, AUKUS) without spelling out — but the headline should rarely need acronyms at 5–8 words anyway. Example: "U.S. and India sign critical-minerals deal." (7 words, one event, neutral, no names, no acronyms). The primary event MUST be U.S.-gov-sourced (see SOURCE HIERARCHY above). When two events are equally dominant, you may join with a semicolon up to 10 words total — but prefer one.
- DEK: Right below the headline, render a <ul class="dek-bullets"> containing **EXACTLY 3 <li> bullets**. **Read @${REPO}/DEK.md (v3, 2026-05-27) before drafting — it is binding.** The 3 dek bullets ARE the same 3 events as the visible top-3 events block below (no duplication of work; the dek is the collapsed view, the events block is the expanded view). Each bullet: ≤12 words, one event, plain English, statement of fact, no acronyms, no unfamiliar personal names (use country/institution), prefer outcomes over process (sign/publish/announce, not "meet/talk"), neutral verbs only. The target reader is a smart layperson who reads NYT once a day — every bullet must be understandable on first read with zero Googling. Every event named in the dek MUST appear in the top-3 Events list (U.S.-government sourced — see SOURCE HIERARCHY).

- CONTINUITY STRIP: Immediately after the dek <ul> (before the Voices section), render a <p class="thread-strip">…</p> with the active long-running threads.
  - Read @${REPO}/.run/threads_us.txt. Each non-empty line is a pre-rendered chip string like "Day 76 · Iran war" or "Year 5 · Ukraine war".
  - For each line, render one chip: <span class="thread-chip"><b>[part before " · "]</b> &middot; [part after " · "]</span>. The bold-wrapped portion is everything up to and not including the " · " separator (e.g., "Day 76", "Year 5"). The trailing part is the thread name (e.g., "Iran war"). Use &ndash; for en-dashes in names ("Trump–Xi summit" → "Trump&ndash;Xi summit").
  - If threads_us.txt is empty or missing, omit the entire <p class="thread-strip"> block entirely. Do not render an empty strip.
  - The strip is data; do not invent threads. Use only the chips in the file.
  - When a long-running thread is the day's biggest event, the dek may name it factually (e.g. "Day 76 of the Iran war: forty navies coordinated on Hormuz" or "the Iran war's eighty-fifth day"). This is just factual naming of today's events — not narrative editorializing — and counts toward the 3–4 event-naming density per DEK.md.
- If many candidates are part of a single regulatory package (e.g., a coordinated set of ATF firearms rules in one Federal Register filing), combine into ONE bullet rather than spending multiple bullets on the package.
- Voices: **6 voices total**, each 12 to 30 words, NEVER invent quotes — verbatim from the articles only, mixing registers (moral, technical, political). Order by editorial importance: the first 3 are the priority selection (always visible). Wrap the additional 3 in a details block of this exact shape: <details class="voices-extras"><summary class="voices-extras-summary">Show 3 more voices</summary> then the 3 more <blockquote class="pull"> elements then </details> — native HTML expander, no JS. Both groups follow the same rules (no repeat speakers, mix of registers).
- ALLIED GOVERNMENTS SECTION: directly after the Voices section closes (BEFORE the more-events block at the bottom of the brief), render a short allied-government section — an <h3 class="section-label">Allied Governments</h3> then <ul class="items allied-items">. UP TO 3 bullets, drawn ONLY from non-US allied government sources (UK MoD, UK FCDO, UK No.10, NATO News, Australia DFAT, Japan MoFA, Taiwan MOFA, G7 Council (via Global Affairs Canada) — and AUKUS-keyword items from UK gov.uk search atom). NEVER from US-government domains (.gov, .mil, state.gov, defense.gov, whitehouse.gov, etc.) — Allied Governments is by definition non-US. Same bullet structure as Events (bold lead, tight description, citation, date+agency tag), but cite markers are LOWERCASE LETTERS (a, b, c) so they do not collide with the Events' numerals 1-9. **Allied items ALSO get entries in the Sources bibliography** — render them as a second list <ol type="a" class="sources-allied"> inside the <section class="sources"> (after the main 1-9 <ol>), containing 3 li with the same citation format as the numbered events. The letter markers in the allied cites must match the letter labels in the Sources bibliography. CONDITIONAL: if no allied-sourced material is worth a slot today, OMIT the whole Allied Governments section AND the corresponding sources-allied list — never render either empty.
- Render as a COMPLETE HTML FILE matching ${REPO}/research/prototype_us_2026-05-12.html. Preserve all CSS, the <header>, <footer>, and <script> blocks unchanged. Only replace:
  - <title>...</title> to a SEO-discoverable format: 2-3 key noun phrases from today's content (≤50 chars combined), then date, then brand. Format pattern is "[KEY PHRASES] · [Month Day] · Briefer News". Concrete example: "Trump-Xi summit, Hormuz coalition · May 14 · Briefer News". Goal: ≤65 total chars. Avoid acronyms; use plain-English noun phrases that match what a reader would Google ("Hormuz coalition" not "CENTCOM patrol", "Trump-Xi summit" not "bilateral meeting").
  - <meta name="description" content="..."> — write a DEDICATED meta description, ≤155 characters total. NOT the dek — the dek is too long and gets truncated in Google's SERP. The meta description is a short, punchy synopsis front-loaded with concrete nouns: 2-3 names (people / countries / institutions), one place, one verb. Active voice, present tense. Example: "Rubio and Jaishankar sign U.S.-India critical-minerals framework in Delhi. Quad's first 2026 meeting. NPT Review Conference closes without consensus." (149 chars). Count characters — if it exceeds 155, trim. This string drives SERP click-through; treat it as marketing copy for a serious-news reader, not as a paraphrase of the dek.
  - <meta property="og:title" content="..."> — same string as the <title> tag.
  - <meta property="og:description" content="..."> — same string as the meta description (the ≤155-char dedicated description, not the dek).
  - <meta property="og:url" content="..."> — leave as "https://briefer.news/usa/" (canonical URL, not the dated archive URL).
  - <link rel="canonical" href="..."> — leave as "https://briefer.news/usa/" (same canonical URL as og:url; the live daily is the authoritative URL, not the dated archive snapshot).
  - <meta name="twitter:title" content="..."> — same as <title>.
  - <meta name="twitter:description" content="..."> — same string as the meta description (the ≤155-char dedicated description).
  - <div class="stamp">...</div> to today's date in CAPS (e.g. "MAY 13, 2026", not "May 13, 2026")
  - <h2 class="headline">...</h2> — **5 to 8 words**, one event, plain English statement of fact (see HEADLINE rule above)
  - Insert <ul class="dek-bullets">…</ul> IMMEDIATELY after </h2> (closing tag of headline) — exactly 3 <li> bullets, each a one-line statement of fact per DEK.md v3. The 3 bullets are the lede phrases for the top-3 events below.
  - Insert <p class="thread-strip">…</p> IMMEDIATELY after </ul> closing the dek bullets — the continuity strip per rules above. Omit entirely if .run/threads_us.txt is empty.
  - <div class="voices">...</div> — first 3 voices as <blockquote class="pull"> directly inside, then a <details class="voices-extras"><summary class="voices-extras-summary">Show 3 more voices</summary> with the additional 3 <blockquote class="pull"> elements inside. No "open" attribute on this details — extras default to hidden (preserving the original "Selected" view as default).
  - <ul class="items">...</ul> — the TOP EVENTS block (always visible): exactly 3 li, ALL U.S.-federal-government items (no allied items — see SOURCE HIERARCHY), each with bold lead, tight description, citation, date+agency tag. These are the day's THREE MOST CONSEQUENTIAL items per BRIEF_STYLE.md priority order. Cite numerals 1-3.
  - <details class="more-events"><summary class="more-events-summary">Show 6 more events</summary><ul class="items items-more">...</ul></details> — appears in the prototype at the BOTTOM of the brief, immediately before the Sources block (and after the transcript section, if present). Exactly 6 li inside the items-more <ul>, ALL U.S.-federal-government items, same bullet structure as the visible top 3. These are items 4-9 in significance order, with cite numerals 4-9. No "open" attribute on the details — collapsed by default. Together with the visible top 3, the 9 events preserve the Sources bibliography numbering 1-9.
  - <h3 class="section-label">Allied Governments</h3> + <ul class="items allied-items">...</ul> — directly AFTER the Voices section's closing </div> and BEFORE the more-events block, per the ALLIED GOVERNMENTS SECTION instruction above. Omit BOTH the h3 and the ul entirely if there is no allied material today.
  - <ol type="a" class="sources-allied">...</ol> — a second ordered list with type="a" (renders a, b, c) inside <section class="sources">, immediately after the main 9-item <ol>. Contains 3 li, one per Allied Governments item, in the same <cite> format as the numbered events. The letter labels (a, b, c) match the lowercase cite markers used in the Allied Governments bullets above. CONDITIONAL: if there's no Allied Governments section today, OMIT this list entirely.
  - The inner <section class="sources"><ol>...</ol></section> (PRESERVE the wrapping <details class="sources-details"><summary class="sources-summary">Sources</summary> and the closing </details>; only the inner section + ol is replaced). The Sources section is now **COLLAPSED by default** — `<details>` with NO `open` attribute. Readers click "Sources" to expand. The synth must NOT add `open`; render exactly `<details class="sources-details">` (no attributes). Keep the wrapper, summary text, and closing tag intact.

Save the complete HTML to ${OUT}. Do not output the HTML to stdout — write it to the file.
EOF

echo "--- Stage 4: Claude synthesizes the brief ---"
"$CLAUDE" -p "$(cat "$SYNTH_PROMPT")" --max-turns 100 --permission-mode acceptEdits

if [ ! -s "$OUT" ]; then
  echo "ERROR: claude did not write HTML to $OUT — bailing, leaving yesterday's brief in place"
  exit 0
fi
if ! grep -q 'class="headline"' "$OUT" || ! grep -q 'class="items"' "$OUT" || ! grep -q 'class="sources"' "$OUT"; then
  echo "ERROR: $OUT missing required structural classes — leaving yesterday's brief in place"
  exit 0
fi
echo "Brief HTML produced: $(wc -c < "$OUT") bytes"

# ── Stage 5: deploy to local nginx volume ──────────────────────────────────
# Archive copy gets a rewritten canonical pointing to ITS dated URL, not
# the live /usa/ — so Google indexes each archive as unique content rather
# than a duplicate of today's brief.
echo "--- Stage 5: deploying to nginx volume ---"
ARCHIVE_HTML="$RUN_DIR/today-archive.html"
/usr/bin/sed "s|<link rel=\"canonical\" href=\"https://briefer.news/usa/\">|<link rel=\"canonical\" href=\"https://briefer.news/usa/archive/${TODAY}.html\">|" "$OUT" > "$ARCHIVE_HTML"

"$DOCKER" run --rm \
  -v "$RUN_DIR":/src:ro \
  -v briefernewsapp_site_output:/dst \
  alpine sh -c "
    mkdir -p /dst/usa /dst/usa/archive
    cp /src/today.html /dst/usa/index.html
    cp /src/today-archive.html /dst/usa/archive/${TODAY}.html
    ls -la /dst/usa | head -5
  "

# ── Stage 6: publish to AWS S3 + CloudFront invalidate (non-fatal on error) ─
# Targets the deployment account's bucket via default ~/.aws credentials.
# briefer.news public alias is gated on a CloudFront cross-account CNAME
# transfer (case 177826301600063 with AWS Support); until that's done, content
# still serves via https://d1sl4o5xm2ds0o.cloudfront.net.
S3_BUCKET=briefer-news-site
DIST_ID=EMV1VIFYTSI3U
AWS=/Users/maxgoshay/.local/bin/aws

if [ -x "$AWS" ] && "$AWS" sts get-caller-identity >/dev/null 2>&1; then
  echo ""
  echo "--- Stage 6: publishing to S3 + CloudFront ---"
  "$AWS" s3 cp "$OUT" "s3://${S3_BUCKET}/usa/index.html" \
    --content-type "text/html; charset=utf-8" \
    --cache-control "no-store, no-cache" \
    && echo "S3: usa/index.html uploaded" \
    || echo "S3: usa/index.html upload FAILED (non-fatal)"

  "$AWS" s3 cp "$ARCHIVE_HTML" "s3://${S3_BUCKET}/usa/archive/${TODAY}.html" \
    --content-type "text/html; charset=utf-8" \
    --cache-control "public, max-age=31536000, immutable" \
    && echo "S3: usa/archive uploaded (with archive canonical)" \
    || echo "S3: usa/archive upload FAILED (non-fatal)"

  "$AWS" cloudfront create-invalidation \
    --distribution-id "$DIST_ID" \
    --paths "/usa/index.html" "/usa/archive/${TODAY}.html" \
    --query 'Invalidation.Id' --output text \
    && echo "CloudFront: invalidation created" \
    || echo "CloudFront: invalidation FAILED (non-fatal)"
else
  echo "--- Stage 6: skipped — AWS CLI unavailable or unauthenticated ---"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Synthesis complete at $(date)"
echo "  Local:      http://localhost/usa/"
echo "  CloudFront: https://d1sl4o5xm2ds0o.cloudfront.net/usa/"
echo "  Public:     https://briefer.news/usa/"
echo "═══════════════════════════════════════════════════════════════"
