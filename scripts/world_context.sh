#!/bin/bash
# briefer.news world-context generator.
#
# Runs at the start of synthesize.sh (or standalone). Calls Claude Code
# headlessly with WebSearch enabled to assemble a compact "what does the
# world consider important today" briefing. Saved to .run/world_context.md.
#
# This file is read by both the picker (Stage 2) and synthesizer (Stage 4)
# in synthesize.sh as ambient signal — NOT as a directive. The brief still
# cites only US-gov primaries.
#
# Failure mode: if generation fails or the WebSearch quota is hit, the file
# may be stale or missing. Callers (picker/synth) should tolerate this.

set +e

REPO=/Users/maxgoshay/code/briefernewsapp
cd "$REPO"

LOG_DIR="$REPO/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/world-context-$(date +%Y%m%d).log"
exec >> "$LOG_FILE" 2>&1

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "World-context generation starting at $(date)"
echo "═══════════════════════════════════════════════════════════════"

CLAUDE=/Users/maxgoshay/.local/bin/claude
TODAY=$(date +%Y-%m-%d)
TODAY_HUMAN=$(date "+%A, %B %-d, %Y")
RUN_DIR="$REPO/.run"
mkdir -p "$RUN_DIR"

OUT="$RUN_DIR/world_context.md"
PROMPT_FILE="$RUN_DIR/prompt_world.txt"

if [ ! -x "$CLAUDE" ]; then
  echo "ERROR: claude CLI not at $CLAUDE — bailing"
  exit 0
fi

cat > "$PROMPT_FILE" <<EOF
You are generating ambient world-context for briefer.news, a daily intelligence brief on US-government output. Today is ${TODAY_HUMAN}.

Use the WebSearch tool to identify what the world's major news outlets (BBC, Reuters, AP, Al Jazeera, FT, Bloomberg, NYT, WSJ, etc.) consider today's most important global stories. Run 3-5 searches across different angles: top global news, top US news, major upcoming events.

Then write a compact markdown briefing in this exact structure (keep total ≤450 words):

# World context — ${TODAY_HUMAN}

## Dominant narrative arcs
- (3-5 short lines, one per major theme the world is focused on. Each line: theme + brief why it matters today)

## Secondary threads
- (3-5 short lines, important second-tier stories worth keeping in view)

## Calendar to watch (next 7-14 days)
- (2-4 lines, named upcoming events with dates)

Style notes:
- Bias toward structural importance, not breaking-news churn
- Concrete (named actors, events, dates) — not abstractions
- This is editorial signal for the synthesizer, NEVER public-facing — synth uses it to calibrate framing emphasis on bullets, but the brief publishes only US-gov primary sources. Do NOT propose citations for the brief.
- Do NOT recommend or instruct — just describe what the world is focused on

Save the briefing to ${OUT}. Do not output to stdout — write to the file.
EOF

echo "--- generating world context via Claude WebSearch ---"
"$CLAUDE" -p "$(cat "$PROMPT_FILE")" \
  --max-turns 25 \
  --permission-mode acceptEdits \
  --allowedTools WebSearch WebFetch Read Write Edit

if [ ! -s "$OUT" ]; then
  echo "ERROR: world_context.md not written — synth will proceed without it"
  exit 0
fi

echo ""
echo "World context produced ($(wc -c < "$OUT") bytes):"
echo "─────────────────────────────────────────────"
cat "$OUT"
echo "─────────────────────────────────────────────"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "World-context generation complete at $(date)"
echo "═══════════════════════════════════════════════════════════════"
