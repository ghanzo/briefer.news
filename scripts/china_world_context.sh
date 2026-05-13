#!/bin/bash
# briefer.news China-side world-context generator.
#
# Mirrors scripts/world_context.sh but tuned for the China brief.
# Generates a compact briefing on:
#   - inbound signals (sanctions, export controls, allied military moves)
#   - Western framing of China today
#   - politically-vital stories Chinese gov sources won't carry
#   - upcoming China-relevant calendar
#
# Editorial principle: this file is REFERENCE MATERIAL for the synthesizer's
# framing decisions — never publishable content. The brief still cites only
# Chinese-language primary sources. The world-context informs what the synth
# emphasizes, contextualizes, or notes as outside-the-gate.
#
# Runs at start of synthesize_china.sh (Stage 0).
# Output: .run/china_world_context.md
# Failure mode: missing or stale output — synth proceeds without it.

set +e

REPO=/Users/maxgoshay/code/briefernewsapp
cd "$REPO"

LOG_DIR="$REPO/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/china-world-context-$(date +%Y%m%d).log"
exec >> "$LOG_FILE" 2>&1

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "China world-context generation starting at $(date)"
echo "═══════════════════════════════════════════════════════════════"

CLAUDE=/Users/maxgoshay/.local/bin/claude
TODAY=$(date +%Y-%m-%d)
TODAY_HUMAN=$(date "+%A, %B %-d, %Y")
RUN_DIR="$REPO/.run"
mkdir -p "$RUN_DIR"

OUT="$RUN_DIR/china_world_context.md"
PROMPT_FILE="$RUN_DIR/prompt_china_world.txt"

if [ ! -x "$CLAUDE" ]; then
  echo "ERROR: claude CLI not at $CLAUDE — bailing"
  exit 0
fi

cat > "$PROMPT_FILE" <<EOF
You are generating ambient world-context for the China side of briefer.news, a daily intelligence brief. Today is ${TODAY_HUMAN}.

Use the WebSearch tool to identify what is being reported about China today by non-Chinese sources. Run 4-6 searches across these angles:

1. "China today" or "China May ${TODAY}" — major Western outlet coverage (Reuters, Bloomberg, FT, NYT, WSJ, AP, BBC, SCMP, Nikkei Asia, Economist)
2. US-China relations — Trump administration moves on China, China-Taiwan, Treasury / Commerce / State Dept actions
3. Sanctions / export controls / entity-list additions — what's being done TO Chinese entities by foreign governments
4. Allied military activity near China — Balikatan, Talisman Sabre, Indo-Pacific exercises, freedom-of-navigation transits, PLA-watchers' reporting
5. Politically-vital Chinese-domestic stories that Chinese state media won't lead with — senior-cadre purges, military-corruption sentencings (Wei Fenghe / Li Shangfu-style), Hong Kong NSL prosecutions, Taiwan diplomatic moves, Tibet / Xinjiang
6. Western analyst / think-tank coverage worth flagging — CSIS / RUSI / IISS / MERICS / East Asia Forum / Sinocism style commentary

Then write a compact markdown briefing in this exact structure (keep total ≤300 words):

# China world-context — ${TODAY_HUMAN}

## Inbound signals (things being done TO China)
- (3-5 short lines, each: actor + action + brief why-it-matters. Sanctions / export controls / military moves / diplomatic actions. Concrete and dated.)

## Western framing of China today
- (3-5 short lines, dominant narratives in major outlets. Cite outlet by name. What story is the world leading with on China today?)

## Politically-vital stories Chinese sources won't carry
- (2-4 short lines, named officials, named events, dated. The Wei Fenghe / Li Shangfu category — things our scrape will miss because the state press doesn't carry them.)

## Calendar to watch (next 7-14 days, China-relevant)
- (2-4 lines, named events with dates. Bilateral summits, sanctions deadlines, court rulings, Party plenums, anniversaries, scheduled diplomatic visits.)

Style notes:
- Bias toward STRUCTURAL importance, not breaking-news churn
- Concrete: named actors, events, dates. Not abstractions.
- This is editorial signal for the China-brief synthesizer, NOT public-facing content
- Do NOT recommend or instruct — just describe
- The synthesizer will use this to (a) decide framing emphasis on bullets, (b) potentially mention key inbound signals in an "outside the gate" line, (c) calibrate Strategic Backdrop card selection. It will NOT cite or quote from this file.

Save the briefing to ${OUT}. Do not output to stdout — write to the file.
EOF

echo "--- generating China world-context via Claude WebSearch ---"
"$CLAUDE" -p "$(cat "$PROMPT_FILE")" \
  --max-turns 30 \
  --permission-mode acceptEdits \
  --allowedTools WebSearch WebFetch Read Write Edit

if [ ! -s "$OUT" ]; then
  echo "ERROR: china_world_context.md not written — synth will proceed without it"
  exit 0
fi

echo ""
echo "China world-context produced ($(wc -c < "$OUT") bytes):"
echo "─────────────────────────────────────────────"
cat "$OUT"
echo "─────────────────────────────────────────────"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "China world-context generation complete at $(date)"
echo "═══════════════════════════════════════════════════════════════"
