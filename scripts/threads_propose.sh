#!/bin/bash
# threads_propose.sh — Stage 2 of the auto-thread proposer.
#
# Calls threads_propose.py to collect bullets, then runs Claude
# headlessly with the collected material + the current threads.yaml
# to propose candidate new threads. Output is markdown for editor
# review — NEVER auto-merged into threads.yaml.
#
# Output: .run/threads_proposed.md
# Cadence: runs from daily_digests.sh after weekly + archive_index.

set +e

REPO=/Users/maxgoshay/code/briefernewsapp
cd "$REPO"

LOG_DIR="$REPO/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/threads-propose-$(date +%Y%m%d).log"
exec >> "$LOG_FILE" 2>&1

CLAUDE=/Users/maxgoshay/.local/bin/claude
TODAY=$(date +%Y-%m-%d)
RUN_DIR="$REPO/.run"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Threads proposer starting at $(date)"
echo "═══════════════════════════════════════════════════════════════"

# Stage 1: collect bullets
echo "--- Stage 1: collecting recent bullets ---"
python3 "$REPO/scripts/threads_propose.py" "$TODAY"

INPUT="$RUN_DIR/threads_collected.md"
OUTPUT="$RUN_DIR/threads_proposed.md"
PROMPT_FILE="$RUN_DIR/prompt_threads_propose.txt"

if [ ! -s "$INPUT" ]; then
  echo "ERROR: collection produced no input — skipping"
  exit 0
fi

if [ ! -x "$CLAUDE" ]; then
  echo "ERROR: claude CLI not at $CLAUDE — skipping"
  exit 0
fi

# Stage 2: Claude analysis
cat > "$PROMPT_FILE" <<EOF
You are the auto-thread proposer for briefer.news.

Read these references:
1. @${INPUT} — bullets from the past 14 days of daily briefs across both editions, grouped by date.
2. @${REPO}/pipeline/config/threads.yaml — the current curated thread list with Day-N counters.

Your job: identify TOPICS or ARCS that appear in 3+ days of recent bullets across the 14-day window but are NOT already tracked in threads.yaml. Propose them as candidate new threads for editor review.

Selection criteria (a candidate must be ALL of these):
- Appears in bullet leads or descriptions across 3+ separate dates within the 14-day window
- Is a long-arc event (war, summit cycle, ongoing crisis, multi-month policy push, multi-day exercise, etc.) — NOT a one-off announcement, NOT a routine recurring item (CCDI weekly summaries, monthly economic data drops, etc.)
- Has a plausible "Day N" semantic — a reader returning to the brief would care about the counter
- Is editorially distinctive — not redundant with an existing tracked thread (e.g., if "Iran war" is already tracked, do not propose "Hormuz coalition" or "Iran oil sanctions" as separate threads — they are sub-arcs of the same parent)

For each candidate, output a YAML snippet matching the existing threads.yaml format, plus a brief justification.

Output format — write to ${OUTPUT}. Use this structure exactly:

# Proposed threads — ${TODAY}

## Candidates

### \`<id>\` — <name>
**Days observed:** dates where this topic appeared, e.g., "2026-05-08, 2026-05-10, 2026-05-12, 2026-05-14"
**Justification:** 30-60 words on why this looks like an arc worth tracking
**Proposed YAML entry:**
\`\`\`yaml
  - id: <id-kebab-case>
    name: <Display name>
    start_date: <YYYY-MM-DD — earliest observed date in the window, or a known arc-start date if you can infer one>
    end_date: null
    editions: [us]  # or [china] or [us, china]
    display_format: day  # or month / year / event
\`\`\`

## Already tracked (no action needed)
- list each existing thread from threads.yaml with a note: "<id> — still active" or "<id> — no recent bullets, consider end_date"

## Notes
Free-text observations about patterns or topics that ALMOST qualified but did not quite meet the criteria.

---

If NO candidates qualify (the editor is already tracking everything that is arc-worthy), write:

# Proposed threads — ${TODAY}

## No new candidates this cycle

All long-arc topics with 3+ day coverage in the past 14 days are already represented in threads.yaml. No proposed additions.

[Optional notes section on near-miss topics.]

---

The editor reads this file and manually edits threads.yaml. Your output is a SUGGESTION, never auto-merged.
EOF

echo "--- Stage 2: Claude analysis ---"
"$CLAUDE" -p "$(cat "$PROMPT_FILE")" \
  --max-turns 30 \
  --permission-mode acceptEdits \
  --allowedTools Read Write Edit

if [ ! -s "$OUTPUT" ]; then
  echo "ERROR: claude did not write $OUTPUT"
  exit 0
fi

echo ""
echo "Proposed threads written ($(wc -c < "$OUTPUT") bytes):"
echo "─────────────────────────────────────────────"
head -40 "$OUTPUT"
echo "..."
echo "─────────────────────────────────────────────"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Threads proposer complete at $(date)"
echo "  Review:  $OUTPUT"
echo "═══════════════════════════════════════════════════════════════"
