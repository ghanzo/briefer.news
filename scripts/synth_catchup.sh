#!/bin/bash
# synth_catchup.sh — one-shot mid-day catch-up synth.
#
# Created 2026-05-28 to recover from a stale brief: the morning synth
# was blocked by a backtick preflight failure, and debugging re-runs
# exhausted the Claude Max session quota (resets 1pm PT). This script
# runs once after the quota resets, produces + deploys both editions'
# briefs, injects the weekly preview, then removes its own LaunchAgent.
#
# Triggered by ~/Library/LaunchAgents/news.briefer.synth-catchup.plist
# at 13:05 PT. Self-deletes after a successful US synth so it never
# double-fires.

set +e

REPO=/Users/maxgoshay/code/briefernewsapp
cd "$REPO"

LOG="$REPO/logs/synth-catchup-$(date +%Y%m%d-%H%M).log"
exec >> "$LOG" 2>&1

echo "═══════════════════════════════════════════════════════════════"
echo "Synth catch-up starting at $(date)"
echo "═══════════════════════════════════════════════════════════════"

# 1. US synth (most important — default landing edition)
echo "--- US synth ---"
bash "$REPO/scripts/synthesize.sh"

# Check whether US produced a fresh brief by inspecting the live date
US_TODAY=$(date +"%b %-d, %Y" | tr '[:lower:]' '[:upper:]')
US_LIVE=$(/usr/bin/curl -s https://briefer.news/usa/ | /usr/bin/grep -oE '<div class="stamp">[^<]+</div>' | /usr/bin/head -1)
echo "  expected stamp contains: $US_TODAY"
echo "  live stamp: $US_LIVE"

# 2. China synth (only if quota survived US — synthesize_china bails
#    on its own preflight/quota failure, leaving yesterday's brief)
echo "--- China synth ---"
bash "$REPO/scripts/synthesize_china.sh"

# 3. Weekly preview injection + feeds (post-synth steps the daily flow runs)
echo "--- inject weekly preview ---"
/usr/bin/python3 "$REPO/scripts/inject_weekly_preview.py"

echo "--- build feeds + sitemap ---"
/usr/bin/python3 "$REPO/scripts/build_feeds.py" 2>/dev/null || echo "  (feeds skipped)"
/usr/bin/python3 "$REPO/scripts/build_sitemap.py" 2>/dev/null || echo "  (sitemap skipped)"

# 4. Self-cleanup: remove the one-shot LaunchAgent so it never re-fires.
#    Only remove if the US brief actually refreshed to today.
if echo "$US_LIVE" | grep -q "$US_TODAY"; then
  echo "--- US brief is fresh; removing one-shot LaunchAgent ---"
  /bin/launchctl bootout "gui/$(/usr/bin/id -u)/news.briefer.synth-catchup" 2>/dev/null
  /bin/rm -f "$HOME/Library/LaunchAgents/news.briefer.synth-catchup.plist"
  echo "  one-shot removed"
else
  echo "--- US brief NOT fresh (quota may still be limited); leaving one-shot in place to retry ---"
  echo "    (it will fire again at the next StartCalendarInterval if configured)"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Synth catch-up finished at $(date)"
echo "═══════════════════════════════════════════════════════════════"
