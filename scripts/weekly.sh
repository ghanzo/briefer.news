#!/bin/bash
# weekly.sh — Build and deploy the weekly digest pages for both editions.
#
# Pipeline:
#   1. Aggregate last 7 days of archived briefs per edition → JSON
#   2. Claude synthesizer reads WEEKLY.md + prototype + JSON → HTML
#   3. Deploy each edition to S3 /usa/weekly/ + /china/weekly/
#
# Cadence: daily-rolling. Fires every morning at 08:00 PDT via
# ~/Library/LaunchAgents/news.briefer.digests.plist (wrapped by
# daily_digests.sh, which runs og_weekly.sh first). The aggregator
# uses a "today − 6 days" window, so the /weekly/ page slides forward
# one day per run and is always current — never stale-for-a-week.
#
# Failure mode: any stage fails → log, exit 0, leave previous weekly live.

set +e

REPO=/Users/maxgoshay/code/briefernewsapp
cd "$REPO"

LOG_DIR="$REPO/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/weekly-$(date +%Y%m%d).log"
exec >> "$LOG_FILE" 2>&1

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Weekly synth starting at $(date)"
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
if ! "$DOCKER" ps --format '{{.Names}}' | grep -q briefer_nginx; then
  echo "ERROR: briefer_nginx not running — cannot read archives; bailing"
  exit 0
fi

# Helper: run the full pipeline for one edition.
synth_edition() {
  local edition="$1"           # "us" or "china"
  local edition_path           # "usa" or "china" — matches S3 / URL
  local edition_label          # "U.S." or "China" — display
  local intro_noun             # "U.S." or "PRC" — used in subtitles
  if [ "$edition" = "us" ]; then
    edition_path="usa"
    edition_label="U.S."
    intro_noun="U.S."
  else
    edition_path="china"
    edition_label="China"
    intro_noun="PRC"
  fi

  echo ""
  echo "──────────── Edition: $edition_label ────────────"

  # Stage 1: aggregate
  local JSON="$RUN_DIR/weekly_${edition}.json"
  echo "--- Stage 1: aggregating week for $edition_label ---"
  python3 "$REPO/scripts/weekly_aggregate.py" "$edition" "$TODAY" "$JSON"

  if [ ! -s "$JSON" ]; then
    echo "ERROR: weekly_aggregate produced no output for $edition — skipping"
    return 1
  fi

  # Stage 2: Claude synth
  local SYNTH_PROMPT="$RUN_DIR/prompt_weekly_${edition}.txt"
  local OUT="$RUN_DIR/weekly_${edition_path}.html"
  rm -f "$OUT"

  cat > "$SYNTH_PROMPT" <<EOF
You are the synthesizer for the weekly digest of briefer.news ($edition_label edition).

Required reading (in order):
1. @${REPO}/WEEKLY.md — the binding spec for this artifact. Read it carefully and follow every rule.
2. @${REPO}/DEK.md — voice rules. WEEKLY.md inherits the "Week's Read" lead-paragraph posture from DEK.md's spirit.
3. @${REPO}/BRIEF_STYLE.md — general style rules.
4. @${REPO}/lens.md — interpretive framework.
5. @${REPO}/research/prototype_weekly_2026-05-17.html — visual template. Preserve all CSS, head, masthead, footer structure; replace the editorial content per the rules below.
6. @${JSON} — full week's aggregated material for this edition (7 days of briefs with headlines, deks, threads, bullets, voices, OG items, and strategy cards).

Today is ${TODAY}. The week covered runs from ${TODAY} − 6 days to ${TODAY}.

Output requirements:

WEEKLY HEADLINE — ≤14 words, a stance or question, NOT a topic label. Read WEEKLY.md's "The Headline" section before drafting. Examples of right form:
  - "Washington went to Beijing with leverage and came back with a Taiwan warning."
  - "The Iran war's coalition phase began this week — quietly."
Examples of wrong form (BANNED):
  - "The week in Iran war and trade"
  - "Big week in US-China relations"
  - "Top stories of the week"

WEEK'S READ (lead paragraph) — 80-120 words, ≤3 sentences. Replaces the daily dek. Read WEEKLY.md's "The Week's Read" section. Must do at least 3 of: name a posture, notice an arc, identify an asymmetry, make a falsifiable claim, anchor to a longer arc. NO chronological recap, NO doctrine name-drops in the lead (NQPF / 15FYP / dual circulation / common prosperity / 30/60 / MIC2025), NO templated openers ("this week was about…", "the week saw…", "on Monday…"), NO list-with-no-stance constructions.

THREADS AT WEEK'S END — 60-150 words of PROSE (not bullets). Where the long arcs stand at week's close. Reference the thread strip's Day-N counts where natural. Name a *direction*, not statuses. Read WEEKLY.md's "Threads at week's end" section.

THE WEEK'S BULLETS — 5 to 7 items, 40-80 words EACH. These are NOT daily-bullet compression — they explain WHY each item mattered more than the other 40+ items from the week. Each bullet must answer: what happened, and what does it tell us in retrospect? Cap: ≤2 bullets from a single thread (don't make the week 100% Iran or 100% summit). Format inside <ul class="week-bullets">:
  <li><b>Lead phrase.</b> Editorial sentence on what happened, with date and source. Then the editorial read: why this item, why now, what it reveals or anchors. Cross-reference the daily where this first appeared.<sup><a class="cite" href="[URL]" title="[Source title]">N</a></sup><span class="week-tag">[Date] · [Agency]</span></li>

VOICES OF THE WEEK — 6 voices. 3 in Selected view + 3 in Expanded. Same speaker-diversity rule as daily (each voice from a different speaker AND a different source category). For the China edition, Xi-first rule applies: if Xi spoke this week and the quote is usable, Xi is voice #1.

Hard quote-recency: every voice quote must be from within the week. No exception. The weekly is about the week.

Voice format: <blockquote class="pull"><p>&ldquo;[quote]&rdquo;</p><cite>[Speaker name + role] &middot; [Date]<sup><a class="cite" href="[URL]" title="[Source]" target="_blank" rel="noopener">[N]</a></sup></cite></blockquote>

STRATEGIC BACKDROP WEEKLY ($([ "$edition" = "china" ] && echo "include — 2-3 cards" || echo "OMIT this section entirely for the U.S. edition") )
$(if [ "$edition" = "china" ]; then cat <<INNER_EOF
Identify the 2-3 doctrines from @${REPO}/pipeline/config/strategy/ that were NAMED or OPERATIVELY INVOKED most often across the week's bullets. This is a count, not a guess. For each, render a card in <div class="backdrop"> using the same format as the daily brief — strategy-title, strategy-status, strategy-blurb. The blurb (~30 words) must connect the doctrine to specific items from the week's bullets, not from external knowledge.
INNER_EOF
fi)

OUTSIDE THE GATE WEEKLY — Aggregate all OG items across the past 7 days from the JSON. Group by date with day-divider headers ("MAY 14, 2026 · THURSDAY"). Render in <ul class="outside-gate"> matching the daily brief's OG section. Use lowercase letter cite markers (a, b, c, ...) and the same <span class="when"> pattern as dailies. If the JSON contains zero OG items (rollout phase — pre-2026-05-15 archives don't have OG), render the empty-state inside <div class="og-empty">:
  <div class="og-empty">No Outside the Gate items archived this week yet. The section came online 2026-05-15; weekly aggregations fill in as daily briefs publish.</div>

DAY-BY-DAY SECTION + SITE FOOTER — preserve the section.daily-foot with one <li><a> per day of the week, linking to that day's archive. For days that came from the legacy /archive/ (pre-2026-05-12 for both editions), use href="/archive/YYYY-MM-DD.html". For days from /usa/archive/ or /china/archive/, use href="/usa/archive/YYYY-MM-DD.html" or href="/china/archive/YYYY-MM-DD.html". The JSON includes the date for each day; for missing days within the 7-day window, omit them from the section. PRESERVE the <footer class="site-foot"> with cross-site nav (← daily, archive, about, sources, GitHub) UNCHANGED — only the section.daily-foot content is replaced.

Render as a COMPLETE HTML FILE matching ${REPO}/research/prototype_weekly_2026-05-17.html. Preserve all CSS, <head>, masthead, and overall structure. Only replace:
  - <title>...</title> to "Briefer News — Weekly · Week of <human range> · $edition_label"
  - <p class="tagline">...</p> in masthead: "The week · $edition_label"
  - <div class="stamp">Week of <human range></div>
  - <h2 class="headline">...</h2> per rules above (≤14 words, stance not topic)
  - <p class="week-read">...</p> per rules above (80-120 words, ≤3 sentences)
  - <div class="threads-prose">...</div> per rules above (60-150 words prose)
  - <ul class="week-bullets">...</ul> per rules above (5-7 li elements)
  - 6 <blockquote class="pull">...</blockquote> blocks per rules above
$([ "$edition" = "china" ] && echo "  - <div class=\"backdrop\">...</div> with 2-3 strategy cards" || echo "  - REMOVE the Strategic Backdrop section entirely (H3 + div.backdrop) — U.S. edition does not include it")
  - <div class="og-empty"> OR <ul class="outside-gate">...</ul> per rules above
  - <section class="daily-foot">...</section> with day-by-day links per rules above (NOTE: this is now a <section>, not a <footer>; the <footer class="site-foot"> below it is PRESERVED unchanged)

Save the complete HTML to ${OUT}. Do not output the HTML to stdout — write it to the file.
EOF

  echo "--- Stage 2: Claude synthesizes weekly for $edition_label ---"
  "$CLAUDE" -p "$(cat "$SYNTH_PROMPT")" --max-turns 100 --permission-mode acceptEdits

  if [ ! -s "$OUT" ]; then
    echo "ERROR: claude did not write HTML to $OUT — bailing this edition"
    return 1
  fi
  if ! grep -q 'class="week-read"' "$OUT" || ! grep -q 'class="week-bullets"' "$OUT"; then
    echo "ERROR: $OUT missing required structural classes — bailing this edition"
    return 1
  fi
  echo "Weekly HTML produced for $edition_label: $(wc -c < "$OUT") bytes"

  # Stage 3: deploy nginx volume
  echo "--- Stage 3: deploying to nginx volume /$edition_path/weekly/ ---"
  "$DOCKER" run --rm \
    -v "$RUN_DIR":/src:ro \
    -v briefernewsapp_site_output:/dst \
    alpine sh -c "
      mkdir -p /dst/${edition_path}/weekly
      cp /src/weekly_${edition_path}.html /dst/${edition_path}/weekly/index.html
      ls -la /dst/${edition_path}/weekly | head -3
    "

  # Stage 4: deploy S3 + CloudFront
  local S3_BUCKET=briefer-news-site
  local DIST_ID=EMV1VIFYTSI3U
  local AWS=/Users/maxgoshay/.local/bin/aws
  if [ -x "$AWS" ] && "$AWS" sts get-caller-identity >/dev/null 2>&1; then
    echo "--- Stage 4: publishing to S3 + CloudFront ---"
    "$AWS" s3 cp "$OUT" "s3://${S3_BUCKET}/${edition_path}/weekly/index.html" \
      --content-type "text/html; charset=utf-8" \
      --cache-control "no-store, no-cache" \
      && echo "S3: ${edition_path}/weekly uploaded" \
      || echo "S3: ${edition_path}/weekly upload FAILED (non-fatal)"
    "$AWS" cloudfront create-invalidation \
      --distribution-id "$DIST_ID" \
      --paths "/${edition_path}/weekly/index.html" "/${edition_path}/weekly/" \
      --query 'Invalidation.Id' --output text \
      && echo "CloudFront: invalidation created" \
      || echo "CloudFront: invalidation FAILED (non-fatal)"
  else
    echo "--- Stage 4: skipped — AWS CLI unavailable ---"
  fi

  return 0
}

synth_edition "us"
synth_edition "china"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Weekly synth complete at $(date)"
echo "  US:    https://briefer.news/usa/weekly/"
echo "  China: https://briefer.news/china/weekly/"
echo "═══════════════════════════════════════════════════════════════"
