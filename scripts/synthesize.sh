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

# ── Stage 0: world-context generation (ambient signal for picker + synth) ───
# Runs Claude with WebSearch to assemble what global outlets consider today's
# biggest stories. Saved to .run/world_context.md and referenced (optionally)
# by the picker and synthesizer prompts. Failure here is non-fatal — the
# picker/synth tolerate a missing or stale file.
echo ""
echo "--- Stage 0: world context ---"
"$REPO/scripts/world_context.sh"

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
    ('UK Ministry of Defence', 2),
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
  ranked AS (
    SELECT
      a.id,
      s.name AS source,
      a.title,
      a.publish_date::date AS pub_date,
      a.url,
      al.priority
    FROM articles a
    JOIN sources s ON a.source_id = s.id
    JOIN allowlist al ON al.name = s.name
    WHERE a.full_text IS NOT NULL
      AND LENGTH(a.full_text) >= 500
      AND (a.publish_date >= CURRENT_DATE - INTERVAL '2 days' OR a.scraped_at >= NOW() - INTERVAL '36 hours')
      ${NOISE_FILTER}
    ORDER BY al.priority ASC, pub_date DESC NULLS LAST
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

Diversity requirement: ensure DEFENSE (CENTCOM, Navy, JCS, Air Force, War.gov, UK MoD), ENFORCEMENT (DOJ, CISA), and ECONOMIC (Federal Register Executive Orders & Rules, Treasury, Federal Reserve, BEA, BLS) get representation. State Dept will dominate by volume — do not let it crowd out the other categories.

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
3. @${REPO}/research/prototype_2026-05-07.html — the visual template you must mirror
4. @${FULL} — full text of the articles the picker selected

Optional ambient signal (read if present, treat as background not directive):
@${REPO}/.run/world_context.md — what global outlets consider today's biggest stories. Use this to frame your bullets in their wider narrative arc when natural (e.g., anchoring a CENTCOM-sourced bullet to "the deteriorating April 8 ceasefire" if that is the global frame). Every claim and citation must still come from the gov articles in the candidates list — the world context informs framing, not facts. Do NOT cite the world context.

Today is ${TODAY}.

Your job:
- From the candidates, select the 9 most consequential items per BRIEF_STYLE.md priority order.
- Apply BRIEF_STYLE.md rules: at most 2 DOJ items, at most 3 purely-domestic items, mix of registers in the voices.
- HEADLINE — read BRIEF_STYLE.md "Accessibility rule" carefully. Punchy, plain, fact-based. ONE OR TWO CLEAR ACTIONS MAX. Readable by a smart friend who reads the New York Times but does NOT follow the Federal Register. Replace acronyms and institutional shortcuts with plain descriptors: GAESA → "Cuba's military business arm"; DFARS/FOCI → "foreign-ownership rule"; FY27 → "2027 budget"; "designated" → "sanctioned" or "blacklisted"; bare place names need a one-word anchor ("Hormuz" → "Strait of Hormuz"). Avoid compound jargon ("oil-graft network", "launch sites"). If a term in the headline would need explaining at a dinner party, rewrite it.
- If many candidates are part of a single regulatory package (e.g., a coordinated set of ATF firearms rules in one Federal Register filing), combine into ONE bullet rather than spending multiple bullets on the package.
- Voices: 3 (occasionally 4), each 12 to 30 words, NEVER invent quotes — verbatim from the articles only, mixing registers (moral, technical, political).
- Render as a COMPLETE HTML FILE matching ${REPO}/research/prototype_2026-05-07.html. Preserve all CSS, the <head>, <header>, <footer>, and <script> blocks unchanged. Only replace:
  - <title>...</title> to "Briefer News — <human date>"
  - <div class="stamp">...</div> to today's date in CAPS
  - <h2 class="headline">...</h2> — 12 to 16 words, plain English, accessible to a non-specialist (see Accessibility rule above)
  - <div class="voices">...</div> — 3 voices as <blockquote class="pull">
  - <ul class="items">...</ul> — exactly 9 li with bold lead, tight description, citation, date+agency tag
  - <section class="sources">...</section> — numbered <ol> with publisher, title, date, link, shortened display URL

Save the complete HTML to ${OUT}. Do not output the HTML to stdout — write it to the file.
EOF

echo "--- Stage 4: Claude synthesizes the brief ---"
"$CLAUDE" -p "$(cat "$SYNTH_PROMPT")" --max-turns 80 --permission-mode acceptEdits

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
echo "--- Stage 5: deploying to nginx volume ---"
"$DOCKER" run --rm \
  -v "$RUN_DIR":/src:ro \
  -v briefernewsapp_site_output:/dst \
  alpine sh -c "
    cp /src/today.html /dst/index.html
    mkdir -p /dst/archive
    cp /src/today.html /dst/archive/${TODAY}.html
    ls -la /dst | head -5
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
  "$AWS" s3 cp "$OUT" "s3://${S3_BUCKET}/index.html" \
    --content-type "text/html; charset=utf-8" \
    --cache-control "no-store, no-cache" \
    && echo "S3: index.html uploaded" \
    || echo "S3: index.html upload FAILED (non-fatal)"

  "$AWS" s3 cp "$OUT" "s3://${S3_BUCKET}/archive/${TODAY}.html" \
    --content-type "text/html; charset=utf-8" \
    --cache-control "public, max-age=31536000, immutable" \
    && echo "S3: archive uploaded" \
    || echo "S3: archive upload FAILED (non-fatal)"

  "$AWS" cloudfront create-invalidation \
    --distribution-id "$DIST_ID" \
    --paths "/index.html" "/archive/${TODAY}.html" \
    --query 'Invalidation.Id' --output text \
    && echo "CloudFront: invalidation created" \
    || echo "CloudFront: invalidation FAILED (non-fatal)"
else
  echo "--- Stage 6: skipped — AWS CLI unavailable or unauthenticated ---"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Synthesis complete at $(date)"
echo "  Local:      http://localhost"
echo "  CloudFront: https://d1sl4o5xm2ds0o.cloudfront.net"
echo "  Custom:     https://briefer.news (pending alias transfer)"
echo "═══════════════════════════════════════════════════════════════"
