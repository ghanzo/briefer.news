#!/bin/bash
# threads_today.sh — Resolve threads.yaml → per-edition chip files.
#
# Tiny wrapper around scripts/threads_today.py for consistency with the
# other Stage-0 helpers (world_context.sh, china_world_context.sh).
# Called by synthesize.sh and synthesize_china.sh before Stage 4.
#
# Output: .run/threads_us.txt, .run/threads_china.txt
# Each line is a pre-formatted chip ("Day 76 · Iran war"). Synth wraps
# them in HTML inside the prototype's continuity strip.
#
# Failure mode: missing/malformed threads.yaml → empty chip files;
# synth tolerates an empty strip.

set +e

REPO=/Users/maxgoshay/code/briefernewsapp
cd "$REPO"

LOG_DIR="$REPO/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/threads-$(date +%Y%m%d).log"
exec >> "$LOG_FILE" 2>&1

TODAY=$(date +%Y-%m-%d)

echo ""
echo "─── threads_today $(date) ───"
python3 "$REPO/scripts/threads_today.py" "$TODAY"
