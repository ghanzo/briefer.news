#!/bin/bash
# researcher.sh — Daily Researcher agent.
#
# Fires from news.briefer.researcher LaunchAgent at 09:00 and 18:00 PT.
# Gathers traffic + search data, last week of growth-loop history, and
# asks Claude to write a research log: what's working, what's not, and
# what angles to draft today.
#
# Output: research/loop/YYYY-MM-DD-{morning|evening}.md
# This file feeds the Drafter at 09:30 PT.

set -euo pipefail

REPO="/Users/maxgoshay/code/briefernewsapp"
cd "$REPO"

TODAY=$(/bin/date +%Y-%m-%d)
HOUR=$(/bin/date +%H)
# Morning runs: HOUR < 12 → "morning"; evening runs → "evening".
if [ "$HOUR" -lt 12 ]; then
  SLOT="morning"
else
  SLOT="evening"
fi

RESEARCH_DIR="$REPO/research/loop"
RUN_DIR="$REPO/.run"
mkdir -p "$RESEARCH_DIR" "$RUN_DIR"

CONTEXT="$RUN_DIR/researcher_context_${SLOT}.md"
PROMPT="$RUN_DIR/researcher_prompt_${SLOT}.txt"
OUT="$RESEARCH_DIR/${TODAY}-${SLOT}.md"

CLAUDE=/Users/maxgoshay/.local/bin/claude

echo "═══════════════════════════════════════════════════════════════"
echo "Researcher — $TODAY $SLOT"
echo "═══════════════════════════════════════════════════════════════"

# ── Stage 1: gather data ────────────────────────────────────────────────
echo "--- Stage 1: gathering ---"

{
  echo "# Researcher context — $TODAY $SLOT"
  echo ""

  echo "## Traffic (yesterday CloudFront)"
  echo ""
  if /usr/bin/python3 "$REPO/scripts/traffic_report.py" 2>/dev/null; then
    /usr/bin/python3 "$REPO/scripts/traffic_report.py" 2>/dev/null
  else
    echo "(traffic_report failed or no data yet)"
  fi
  echo ""

  echo "## Search Console (last 7 days)"
  echo ""
  if /usr/bin/python3 "$REPO/scripts/search_report.py" --days 7 2>/dev/null; then
    /usr/bin/python3 "$REPO/scripts/search_report.py" --days 7 2>/dev/null
  else
    echo "(search_report failed — likely first run; ADC may need refresh)"
  fi
  echo ""

  echo "## Cloudflare Web Analytics — humans only (last 7 + 30 days)"
  echo ""
  echo "### 7-day"
  if /usr/bin/python3 "$REPO/scripts/cloudflare_analytics.py" --days 7 2>/dev/null; then
    /usr/bin/python3 "$REPO/scripts/cloudflare_analytics.py" --days 7 2>/dev/null
  else
    echo "(cloudflare_analytics failed — token issue, or first day post-migration)"
  fi
  echo ""
  echo "### 30-day (medium-window trend)"
  /usr/bin/python3 "$REPO/scripts/cloudflare_analytics.py" --days 30 2>/dev/null || echo "(unavailable)"
  echo ""

  echo "## Posting history (last 7 days)"
  echo ""
  POST_FILES=$(/usr/bin/find "$REPO/logs" -name "posts-*.jsonl" -mtime -7 2>/dev/null | /usr/bin/sort)
  if [ -n "$POST_FILES" ]; then
    for f in $POST_FILES; do
      DATE=$(/usr/bin/basename "$f" .jsonl | /usr/bin/sed 's/posts-//')
      echo "### $DATE"
      /bin/cat "$f" 2>/dev/null | /usr/bin/python3 -c "
import sys, json
for line in sys.stdin:
  try:
    d = json.loads(line)
    print(f\"- **{d.get('channel','?')}**: {d.get('text','')[:200]}\")
  except: pass
" || true
      echo ""
    done
  else
    echo "(no posts in last 7 days)"
  fi
  echo ""

  echo "## Drafter output history (last 7 days)"
  echo ""
  DRAFT_FILES=$(/usr/bin/find "$REPO/logs" -name "drafts-*.md" -mtime -7 2>/dev/null | /usr/bin/sort)
  if [ -n "$DRAFT_FILES" ]; then
    for f in $DRAFT_FILES; do
      echo "### $(/usr/bin/basename "$f" .md)"
      /usr/bin/head -80 "$f" 2>/dev/null || true
      echo ""
    done
  else
    echo "(no drafter output in last 7 days)"
  fi
  echo ""

  echo "## Most recent weekly analysis (if any)"
  echo ""
  LATEST_ANALYSIS=$(/usr/bin/find "$REPO/logs" -name "analysis-*.md" -mtime -8 2>/dev/null | /usr/bin/sort | /usr/bin/tail -1)
  if [ -n "$LATEST_ANALYSIS" ]; then
    /bin/cat "$LATEST_ANALYSIS"
  else
    echo "(no weekly analysis yet — first week of the loop)"
  fi
  echo ""

  echo "## Today's brief headlines"
  echo ""
  for EDITION in usa china; do
    HTML_PATH="$REPO/.run/${EDITION}_brief_today.html"
    if [ ! -f "$HTML_PATH" ] || [ $(($(/bin/date +%s) - $(/usr/bin/stat -f %m "$HTML_PATH" 2>/dev/null || echo 0))) -gt 86400 ]; then
      /usr/bin/curl -s "https://briefer.news/${EDITION}/" > "$HTML_PATH" 2>/dev/null || true
    fi
    if [ -s "$HTML_PATH" ]; then
      /usr/bin/python3 -c "
import re
html = open('$HTML_PATH').read()
h = re.search(r'<h2 class=\"headline\">([\s\S]+?)</h2>', html)
d = re.search(r'<p class=\"dek\">([\s\S]+?)</p>', html)
print('### $EDITION')
print('**' + (re.sub(r'<[^>]+>','',h.group(1)).strip() if h else '(no headline)') + '**')
print('')
print(re.sub(r'<[^>]+>','',d.group(1)).strip() if d else '(no dek)')
print('')
"
    fi
  done

} > "$CONTEXT"

CONTEXT_SIZE=$(/usr/bin/wc -c < "$CONTEXT")
echo "Context gathered: $CONTEXT bytes=$CONTEXT_SIZE"

# ── Stage 2: Claude writes the research log ─────────────────────────────
echo "--- Stage 2: Claude analyzes + writes research log ---"

/bin/cat > "$PROMPT" <<EOF
You are the Researcher agent for briefer.news — a daily intelligence brief
sourced from primary government documents (US + China editions).

Your job ($TODAY $SLOT slot): synthesize the last week of growth-loop activity
into a focused research log that helps the Drafter (which runs 30 min after
you in the morning slot) pick the right angles for today's posts.

Brand promise: "All sourcing from government · Everything cited · No opinion."
The growth content has to live up to that — no clickbait, no opinion takes,
no fake urgency. Treat readers as serious people who want signal, not heat.

Read the context: @${CONTEXT}

Write a research log in this exact structure. Plain markdown. ~400-700 words.

# Research log — $TODAY $SLOT

## Traffic snapshot (last 7d)
We have THREE traffic data sources in the context — synthesize across them:
- **CloudFront logs** (everything, including bots) — top pages, top referrers,
  unique /24 buckets per day, status codes
- **Cloudflare Web Analytics / RUM** (humans only, JS-beacon) — real browser
  sessions by path / country / referrer / device
- **Search Console** — impressions, clicks, position trends

Three or four bullet points naming SPECIFIC numbers. Examples worth calling out:
- Total CloudFront unique buckets this week vs last week
- Human page loads (Cloudflare RUM) — even 1 hit is a meaningful signal early;
  call out the country + path it came from
- Bot-to-human ratio: CloudFront total requests ÷ Cloudflare RUM page-loads
  (gives a rough sense of how much organic-human traffic vs scraper noise)
- Top 3 pages by Cloudflare RUM (closer to "real" engagement than CF logs)
- Top 3 external referrers (Cloudflare RUM and CF logs both)
If a data source is empty or sparse, say so explicitly — don't invent numbers.

## Search performance (last 7d)
- Top 3 queries by impressions + their average position
- Any queries that moved up or down notably
- Total clicks this week, CTR
- If Cloudflare RUM shows clicks but Search Console shows zero CTR, that's
  REAL human traffic NOT coming from search — note which referrer is driving it

## What worked
The posts (Bluesky, X, manual) and angles that drove the best engagement
in the last 7 days. If no posts yet (first week), write:
"First week of the loop — no historical data yet. Starting from zero."

## What stalled
Channels or angles that produced posts but no traffic. If no posts yet,
write the same first-week note.

## Today's hooks
THIS IS THE KEY OUTPUT — the Drafter reads this verbatim.
Look at the U.S. + China brief headlines + deks in the context. For each
edition, identify 2-3 angles in today's content that are:
- Concrete enough to fit Bluesky's 300 chars
- Substantive enough to draw clicks (not "WOW you'll never guess…")
- Actually defensible per the brand promise (gov-sourced, no opinion)

For each angle, write:
- ANGLE: <one-sentence framing>
- WHY IT WORKS: <one sentence on why a serious-news reader cares>
- SUGGESTED CHANNEL(S): bluesky | x | hn | reddit-r/<sub> | linkedin

## Channel experiments for the Drafter to try
2-3 suggestions for the Drafter. Examples:
- "Cross-post yesterday's U.S. brief link to r/geopolitics with a 200-word
  context comment — that sub has gov-source tolerance"
- "Make the Bluesky post a quote of the most-cited gov document, not a
  paraphrase — quotes get reposted, paraphrases don't"

Write directly. Don't preface. Don't summarize. Don't editorialize.

Write the markdown to: $OUT
EOF

PROMPT_SIZE=$(/usr/bin/wc -c < "$PROMPT")
echo "Prompt size: $PROMPT_SIZE bytes"

set +e
"$CLAUDE" -p "$(/bin/cat "$PROMPT")" \
  --allowed-tools Read,Write,Bash \
  > "$RUN_DIR/researcher_${SLOT}_stdout.log" 2> "$RUN_DIR/researcher_${SLOT}_stderr.log"
CLAUDE_EXIT=$?
set -e

if [ $CLAUDE_EXIT -ne 0 ]; then
  echo "Claude failed (exit $CLAUDE_EXIT). See $RUN_DIR/researcher_${SLOT}_stderr.log"
  exit $CLAUDE_EXIT
fi

if [ ! -s "$OUT" ]; then
  echo "ERROR: Claude didn't produce $OUT"
  exit 1
fi

OUT_SIZE=$(/usr/bin/wc -c < "$OUT")
echo "✓ Wrote $OUT ($OUT_SIZE bytes)"
