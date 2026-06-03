#!/bin/bash
# editorial_critique.sh — the daily editorial self-critique LOOP (Phase 1).
#
# A judgment loop (not a cron job): Claude critiques each day's published U.S.
# brief against the rubric AND the candidate pool it was drawn from, then distills
# the result into guidance the NEXT synth reads — so brief quality compounds
# without a human editing prompts daily. The five parts of the loop:
#
#   TRIGGER   : daily 14:00 PT (news.briefer.critique) — OFF-PEAK on purpose, to
#               stay clear of the morning Claude-quota crunch. Output has until
#               the 02:30 synth tomorrow to land.
#   JUDGMENT  : compare what got PUBLISHED (today.html) vs what was AVAILABLE
#               (candidates_meta.json) vs the RULES (BRIEF_STYLE.md + lens.md).
#   FEEDBACK  : writes the top 1-3 actionable notes to research/editorial_notes.md
#               (overwritten daily, so it's self-bounding) — Phase 2 wires the
#               synth to read it. THAT closes the loop.
#   GUARDRAIL : only writes a critique + the notes. Never republishes, never edits
#               the style guide. Notes are SOFT guidance to the next synth.
#   BUDGET    : one claude -p call/day, gated by a once-a-day sentinel so a retry
#               can't double-spend the shared CLI quota.
#
# You tune the LOOP (the rubric below, the cadence, the notes cap) — not each
# day's brief. Read research/critiques/ periodically to see what it's catching
# and adjust the prompt.
#
#   scripts/editorial_critique.sh          # run if not already run today
#   scripts/editorial_critique.sh --force  # run regardless of the sentinel

set -uo pipefail

REPO=/Users/maxgoshay/code/briefernewsapp
CLAUDE=/Users/maxgoshay/.local/bin/claude
RUN_DIR="$REPO/.run"
LOG_DIR="$REPO/logs"; mkdir -p "$LOG_DIR"
CRIT_DIR="$REPO/research/critiques"; mkdir -p "$CRIT_DIR"
NOTES="$REPO/research/editorial_notes.md"
TODAY=$(date +%Y-%m-%d)
SENTINEL="$RUN_DIR/critique-${TODAY//-/}.done"

FORCE=false; [ "${1:-}" = "--force" ] && FORCE=true

# ── Budget guard: at most one run/day ───────────────────────────────────────
if [ "$FORCE" = false ] && [ -f "$SENTINEL" ]; then
  echo "critique already ran today (sentinel: $SENTINEL) — exiting 0"; exit 0
fi
[ -x "$CLAUDE" ] || { echo "ERROR: claude CLI not at $CLAUDE — bailing"; exit 1; }

# ── Preconditions: need today's brief + the pool the synth actually used ─────
BRIEF="$RUN_DIR/today.html"
META="$RUN_DIR/candidates_meta.json"
PICKED="$RUN_DIR/picked_ids.json"
for f in "$BRIEF" "$META" "$PICKED"; do
  [ -s "$f" ] || { echo "missing $f — synth artifacts not present yet; skipping (exit 0)"; exit 0; }
done

CRIT_FILE="$CRIT_DIR/critique-${TODAY}.md"
PROMPT="$RUN_DIR/prompt_critique.txt"

cat > "$PROMPT" <<EOF
You are an exacting editorial critic for briefer.news — a daily U.S. intelligence
brief built ONLY from government primary sources. Critique TODAY's published U.S.
brief against the rules and the candidate pool it was drawn from. Be specific and
unsparing; quote the actual text. This critique feeds tomorrow's synthesizer.

Read these:
1. @${REPO}/BRIEF_STYLE.md   — binding editorial rules (5-8 word headline, 9 events,
   6 voices, <=2 DOJ items, <=3 purely-domestic items, citation + priority rules).
2. @${REPO}/lens.md          — the interpretive frame.
3. @${BRIEF}                 — TODAY's published brief (the OUTPUT under review).
4. @${META}                  — the ~200-article candidate pool the picker saw
   (everything that was AVAILABLE to choose from).
5. @${PICKED}                — the article IDs actually picked into the brief.

Critique on these axes, each with concrete examples quoted from the brief/pool:
- SELECTION: were the 9 most consequential items chosen? Is there anything in the
  candidate pool that was NOT picked but clearly outranks a chosen item? Name the
  specific missed item + its source.
- HEADLINE: 5-8 words, one sharp clause, accurate to the genuine lead story?
- CITATIONS: does every event trace to a government source? any uncited/mismatched
  claim?
- BALANCE: <=2 DOJ, <=3 purely-domestic, a mix of registers across the 6 voices,
  not over-indexed on a single agency?
- WRITING: plain English, named actors, no hedging or editorializing?

THEN write TWO files (you have edit permission — use it):
1. Write the FULL critique to: ${CRIT_FILE}
   Format: a one-line VERDICT, then a short section per axis with quoted examples,
   then a "What worked" line. Markdown.
2. OVERWRITE this rolling file: ${NOTES}
   with ONLY the top 1-3 MOST actionable directives for TOMORROW's synth — each a
   single imperative line a synthesizer can act on (e.g. "Lead with the highest-
   consequence security item, not the first chronological one"; "Drop the 2nd DOJ
   item — a Treasury sanctions release outranked it"). No preamble, no analysis.
   Exact format:
   # Editorial feedback for the next synth (from ${TODAY})
   - <directive 1>
   - <directive 2>
   - <directive 3>

Constraints: do NOT edit any other file. Do NOT republish or modify the brief.
Do NOT edit BRIEF_STYLE.md or lens.md. Only the two files above.
EOF

echo "Running editorial critique for ${TODAY}…"
"$CLAUDE" -p "$(cat "$PROMPT")" --max-turns 30 --permission-mode acceptEdits 2>&1 | tail -15

# ── Verify both files were written; only then set the sentinel ──────────────
ok=true
[ -s "$CRIT_FILE" ] || { echo "WARN: critique not written: $CRIT_FILE"; ok=false; }
[ -s "$NOTES" ]     || { echo "WARN: notes not written: $NOTES"; ok=false; }
if [ "$ok" = true ]; then
  touch "$SENTINEL"
  echo ""
  echo "✓ critique  -> $CRIT_FILE"
  echo "✓ next-synth notes -> $NOTES"
  echo "── editorial_notes.md ──"; cat "$NOTES"
else
  echo "critique incomplete — sentinel NOT set; will retry next run"
  exit 1
fi
