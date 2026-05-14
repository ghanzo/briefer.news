#!/bin/bash
# daily_digests.sh — Refresh the rolling 7-day digest pages each morning.
#
# Runs every day at 08:00 PDT via ~/Library/LaunchAgents/news.briefer.digests.plist,
# after both daily synths complete (US 07:10 PDT, China 07:43 PDT).
#
# Both digest scripts use a "today − 6 days" rolling window, so each
# daily run slides the window forward by one day. The /weekly/ and
# /og-week/ URLs are always fresh — never stale — and always reflect
# the past seven days of archived dailies.
#
# Sequence:
#   1. og_weekly.sh  — aggregates the week's Outside the Gate items
#                       (cheap, ~30s, no Claude calls)
#   2. weekly.sh     — full weekly digest with Claude synthesis per
#                       edition (~3-5 min total)
#
# Failure mode: each child script logs its own failures; this wrapper
# continues to the next stage either way.

set +e

REPO=/Users/maxgoshay/code/briefernewsapp
cd "$REPO"

LOG_DIR="$REPO/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/daily-digests-$(date +%Y%m%d).log"
exec >> "$LOG_FILE" 2>&1

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Daily digests refresh starting at $(date)"
echo "═══════════════════════════════════════════════════════════════"

echo ""
echo "── Stage 1/2: og_weekly.sh ──"
"$REPO/scripts/og_weekly.sh"

echo ""
echo "── Stage 2/2: weekly.sh ──"
"$REPO/scripts/weekly.sh"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Daily digests refresh complete at $(date)"
echo "═══════════════════════════════════════════════════════════════"
