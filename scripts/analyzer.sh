#!/bin/bash
# analyzer.sh — Weekly Analyzer agent.
#
# Fires from news.briefer.analyzer LaunchAgent at 10:00 PT on Sunday.
# Reads the past 7 days of drafts + posts + traffic + search data,
# computes engagement on autonomous posts, and writes a retrospective
# at logs/analysis-YYYY-MM-DD.md.
#
# The output feeds back into next week's Researcher (as historical
# context) so the loop improves over time.

set -euo pipefail

REPO="/Users/maxgoshay/code/briefernewsapp"
cd "$REPO"

TODAY=$(/bin/date +%Y-%m-%d)
WEEK_AGO=$(/bin/date -v-7d +%Y-%m-%d)
LOG_DIR="$REPO/logs"
RUN_DIR="$REPO/.run"
mkdir -p "$LOG_DIR" "$RUN_DIR"

CONTEXT="$RUN_DIR/analyzer_context.md"
PROMPT="$RUN_DIR/analyzer_prompt.txt"
OUT="$LOG_DIR/analysis-${TODAY}.md"

CLAUDE=/Users/maxgoshay/.local/bin/claude

echo "═══════════════════════════════════════════════════════════════"
echo "Analyzer — week of $WEEK_AGO → $TODAY"
echo "═══════════════════════════════════════════════════════════════"

# ── Stage 1: gather a full week of context ──────────────────────────────
echo "--- Stage 1: gathering ---"

{
  echo "# Analyzer context — week ending $TODAY"
  echo ""
  echo "Window: $WEEK_AGO → $TODAY"
  echo ""

  echo "## Traffic — daily breakdown"
  echo ""
  for i in 7 6 5 4 3 2 1; do
    DATE=$(/bin/date -v-${i}d +%Y-%m-%d)
    echo "### $DATE"
    /usr/bin/python3 "$REPO/scripts/traffic_report.py" --date "$DATE" 2>/dev/null || echo "(no data for $DATE)"
    echo ""
  done

  echo "## Search Console (last 7 days vs prior 7)"
  echo ""
  /usr/bin/python3 "$REPO/scripts/search_report.py" --days 7 2>/dev/null || echo "(search data unavailable)"
  echo ""

  echo "## All autonomous posts this week (Bluesky + X)"
  echo ""
  POSTS=$(/usr/bin/find "$REPO/logs" -name "posts-*.jsonl" -mtime -7 2>/dev/null | /usr/bin/sort)
  if [ -n "$POSTS" ]; then
    for f in $POSTS; do
      /bin/cat "$f"
    done
  else
    echo "(no autonomous posts this week — Bluesky or X may not be enabled yet)"
  fi
  echo ""

  echo "## All drafts this week (including manual-channel drafts)"
  echo ""
  DRAFTS=$(/usr/bin/find "$REPO/logs" -name "drafts-*.md" -mtime -7 2>/dev/null | /usr/bin/sort)
  if [ -n "$DRAFTS" ]; then
    for f in $DRAFTS; do
      echo "### $(/usr/bin/basename "$f" .md)"
      /bin/cat "$f"
      echo ""
    done
  else
    echo "(no drafts produced this week — drafter may not have run)"
  fi
  echo ""

  echo "## Researcher logs this week"
  echo ""
  RLOGS=$(/usr/bin/find "$REPO/research/loop" -name "*.md" -mtime -7 2>/dev/null | /usr/bin/sort)
  if [ -n "$RLOGS" ]; then
    for f in $RLOGS; do
      echo "### $(/usr/bin/basename "$f" .md)"
      /bin/cat "$f"
      echo ""
    done
  else
    echo "(no researcher logs this week)"
  fi
  echo ""

  echo "## Previous weekly analyses (last 4 weeks)"
  echo ""
  PREV=$(/usr/bin/find "$REPO/logs" -name "analysis-*.md" -mtime -28 -not -name "analysis-${TODAY}.md" 2>/dev/null | /usr/bin/sort | /usr/bin/tail -4)
  if [ -n "$PREV" ]; then
    for f in $PREV; do
      echo "### $(/usr/bin/basename "$f" .md)"
      /usr/bin/head -40 "$f"
      echo "..."
      echo ""
    done
  else
    echo "(this is the first weekly analysis)"
  fi

} > "$CONTEXT"

echo "Context: $(/usr/bin/wc -c < "$CONTEXT") bytes"

# ── Stage 2: Claude writes the retro ────────────────────────────────────
echo "--- Stage 2: Claude analyzes + writes retro ---"

/bin/cat > "$PROMPT" <<EOF
You are the Analyzer agent for briefer.news. Once a week, on Sunday, you
look at the past 7 days of growth-loop activity and write a retrospective.

Read the context: @${CONTEXT}

Write a retro in this exact structure. Plain markdown. ~600-1000 words.
Be brutally honest. Naming losses is more valuable than narrating wins.

# Weekly analysis — week ending $TODAY

## Traffic
- WoW unique buckets (this week's daily avg vs last week's): name the
  numbers. If equal or down, say so plainly.
- Where the growth (or shortfall) came from: top referrer changes,
  specific pages that moved.
- If data is sparse / missing, say so — don't invent.

## Search performance
- Top queries by impressions this week, with average position.
- Position changes ≥3 spots from last week (up or down).
- Click-through rate trend.

## Posted this week
Count by channel. If autonomous posts (Bluesky/X) are zero, that's a
process gap to flag — the drafter is supposed to post if enabled.

## Hits
SPECIFIC posts that drove a measurable bump (or got measurable
engagement). Quote the post text. Name the channel and the day.

## Misses
SPECIFIC posts that underperformed. Same format. Don't sugarcoat —
if every Bluesky post got 0 likes, write that.

## What we learned
2-4 concrete observations from the week. NOT generic ("posting more
helps"). Specific ("Tuesday's Bluesky post linking the SCIO statement
got 4× the click-through of Monday's link to /usa/ — direct-to-source
links may outperform direct-to-brief").

## Next week's experiments
3-4 concrete things to test, written so the Researcher can pick them
up Monday morning. Example format:
- TEST: post Bluesky link to the underlying primary source (gov.cn,
  whitehouse.gov, etc.) instead of /usa/. Measure CTR. Run for 3 days.
- TEST: write the Reddit r/geopolitics post as a 3-paragraph analysis
  with the brief link at the bottom, not the top.

## Brand-promise check
Any posts this week that drifted from "no opinion, gov sources only"?
Be specific. If clean, write "Clean."

The output must be written to: $OUT
EOF

set +e
"$CLAUDE" -p "$(/bin/cat "$PROMPT")" \
  --allowed-tools Read,Write,Bash \
  > "$RUN_DIR/analyzer_stdout.log" 2> "$RUN_DIR/analyzer_stderr.log"
CLAUDE_EXIT=$?
set -e

if [ $CLAUDE_EXIT -ne 0 ]; then
  echo "Claude failed (exit $CLAUDE_EXIT). See $RUN_DIR/analyzer_stderr.log"
  exit $CLAUDE_EXIT
fi

if [ ! -s "$OUT" ]; then
  echo "ERROR: Analyzer didn't produce $OUT"
  exit 1
fi

echo "✓ Analysis: $OUT ($(/usr/bin/wc -c < "$OUT") bytes)"
