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

## Outside the Gate candidates (CITABLE — for direct rendering in brief)
**This subsection is different from the others.** It will be RENDERED on the public brief page in a section labeled "Outside the Gate · non-US-gov sources." Each item must be citable: a named publication, an exact-or-near-exact publish date within the last 7 days, and a working URL. Pick 5-8 candidates; the synthesizer will choose 3-5 to render.

Selection criteria — pick the signals that BEST illustrate "what the world is doing in response to / parallel to US action this week":
- Allied gov positions and coalition responses (UK / EU / NATO / Japan / Australia / Five Eyes / G7 statements and deployments)
- Adversary primary statements and moves (China MFA, Kremlin, IRNA, North Korea KCNA — when reacting to US action)
- Major operational events the US-gov feed undercovers (shipping attacks, casualties, allied ship/troop movements, coalition fractures)
- Analyst-grade operational detail from authoritative outlets (Reuters / AP / Bloomberg / FT / ISW / CSIS / Critical Threats Project)
- Skip pure punditry; the items must be ACTIONS or PRIMARY STATEMENTS, not opinion

Format each as a single line in this exact structure (one bullet per line, no sub-bullets):
- **[Lead actor + action verb, ≤8 words].** [One-clause explanation, ≤20 words.] | source: [publication name] | date: YYYY-MM-DD | url: [full URL]

Example:
- **UK PM rules out Hormuz blockade role.** Starmer tells Commons UK ships will not enforce US blockade despite Gulf-area deployments. | source: Reuters | date: 2026-05-13 | url: https://www.reuters.com/...

The URL must be the actual article URL, not a generic site root. Use WebSearch / WebFetch as needed to confirm URLs. If you cannot find a citable URL for a candidate, drop it from this list (you can still mention it in the upper sections).

Style notes:
- Bias toward structural importance, not breaking-news churn
- Concrete (named actors, events, dates) — not abstractions
- The non-"Outside the Gate" sections remain editorial signal for the synthesizer, NOT public-facing — synth never quotes them.
- The "Outside the Gate candidates" section is the SINGLE exception: it IS published-source material, used to populate the new page section.
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
