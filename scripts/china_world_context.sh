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

Then write a compact markdown briefing in this exact structure (keep total ≤450 words):

# China world-context — ${TODAY_HUMAN}

## Inbound signals (things being done TO China)
- (3-5 short lines, each: actor + action + brief why-it-matters. Sanctions / export controls / military moves / diplomatic actions. Concrete and dated.)

## Western framing of China today
- (3-5 short lines, dominant narratives in major outlets. Cite outlet by name. What story is the world leading with on China today?)

## Politically-vital stories Chinese sources won't carry
- (2-4 short lines, named officials, named events, dated. The Wei Fenghe / Li Shangfu category — things our scrape will miss because the state press doesn't carry them.)

## Calendar to watch (next 7-14 days, China-relevant)
- (2-4 lines, named events with dates. Bilateral summits, sanctions deadlines, court rulings, Party plenums, anniversaries, scheduled diplomatic visits.)

## Outside the Gate candidates (CITABLE — for direct rendering in brief)
**This subsection is different from the others.** It will be RENDERED on the public brief page in a section labeled "Outside the Gate · non-PRC sources." Each item must be citable: a named publication, an exact-or-near-exact publish date within the last 7 days, and a working URL. Pick 5-8 candidates; the synthesizer will choose 3-5 to render.

Selection criteria — pick the inbound signals that BEST illustrate "what the world is sending toward China this week":
- Sanctions / export controls / entity-list adds (US Treasury, BIS, EU)
- Allied military activity (exercises, FONOPs, deployments)
- Major diplomatic moves China-directed (G7 / G20 statements, allied summits)
- Concrete trade actions (tariffs, tech restrictions, deals)
- Skip pure analyst commentary; the items must be ACTIONS by named actors

Format each as a single line in this exact structure (one bullet per line, no sub-bullets):
- **[Lead actor + action verb, ≤8 words].** [One-clause explanation, ≤20 words.] | source: [publication name] | date: YYYY-MM-DD | url: [full URL]

Example:
- **US Treasury sanctions 3 PRC chip firms.** New Entity List additions cover advanced-node lithography and HBM packaging suppliers. | source: Reuters | date: 2026-05-12 | url: https://www.reuters.com/...

The URL must be the actual article URL, not a generic site root. Use WebSearch / WebFetch as needed to confirm URLs. If you cannot find a citable URL for a candidate, drop it from this list (you can still mention it in the upper sections).

Style notes:
- Bias toward STRUCTURAL importance, not breaking-news churn
- Concrete: named actors, events, dates. Not abstractions.
- The non-"Outside the Gate" sections remain editorial signal for the synthesizer, NOT public-facing — synth never quotes them.
- The "Outside the Gate candidates" section is the SINGLE exception: it IS published-source material, used to populate the new page section.
- Do NOT recommend or instruct — just describe

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
