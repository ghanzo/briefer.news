#!/bin/bash
# synth_catchup.sh — re-runnable mid-day catch-up synth + recovery.
#
# Originally created 2026-05-28 to recover from a stale brief: the morning
# synth was blocked by a backtick preflight failure, and debugging re-runs
# exhausted the Claude Max session quota (resets 1pm PT). It produces +
# deploys both editions' briefs and injects the weekly preview.
#
# It used to install a one-shot LaunchAgent and SELF-DESTRUCT (launchctl
# bootout + rm of its own plist) after a successful US synth, so it could
# only ever fire once — which meant healthcheck.py could detect staleness
# but had nothing left to call. That teardown is GONE.
#
# This script is now idempotent and re-runnable, intended to be invoked by
# healthcheck.py whenever it detects a stale edition. It self-limits to at
# most ONE real synth per calendar day via a sentinel file:
#
#     ${REPO}/.run/catchup-$(date +%Y-%m-%d).done
#
# If the sentinel for today exists, it logs "already ran today" and exits 0
# without touching the synth (protects the Claude quota). Otherwise it
# creates the sentinel and runs the catch-up.
#
# Usage:
#   scripts/synth_catchup.sh            # run the catch-up (once/day)
#   scripts/synth_catchup.sh --dry-run  # check sentinel + print plan, no synth

set +e

REPO=/Users/maxgoshay/code/briefernewsapp
cd "$REPO" || exit 1

DRY_RUN=false
if [ "${1:-}" = "--dry-run" ]; then DRY_RUN=true; fi

RUN_DIR="$REPO/.run"
SENTINEL="$RUN_DIR/catchup-$(date +%Y-%m-%d).done"
mkdir -p "$RUN_DIR"

# In a real run, append to a timestamped log. In a dry run, keep output on
# stdout so the caller (and the verifier) can see the plan directly.
if [ "$DRY_RUN" = "false" ]; then
  LOG="$REPO/logs/synth-catchup-$(date +%Y%m%d-%H%M).log"
  mkdir -p "$REPO/logs"
  exec >> "$LOG" 2>&1
fi

echo "==============================================================="
echo "Synth catch-up invoked at $(date) (dry_run=$DRY_RUN)"
echo "  sentinel: $SENTINEL"
echo "==============================================================="

# --- Once-per-day guard ----------------------------------------------------
# If today's sentinel already exists, the catch-up has already fired today.
# Re-running would burn Claude quota for no benefit, so bail out cleanly.
if [ -f "$SENTINEL" ]; then
  echo "already ran today (sentinel present: $SENTINEL) — nothing to do, exiting 0"
  exit 0
fi

if [ "$DRY_RUN" = "true" ]; then
  echo "DRY RUN — sentinel for today does NOT exist, so a real run WOULD:"
  echo "  1. create sentinel: $SENTINEL"
  echo "  2. run US synth:    bash $REPO/scripts/synthesize.sh"
  echo "  3. run China synth: bash $REPO/scripts/synthesize_china.sh"
  echo "  4. inject weekly:   python3 $REPO/scripts/inject_weekly_preview.py"
  echo "  5. build feeds:     python3 $REPO/scripts/build_feeds.py"
  echo "  6. build sitemap:   python3 $REPO/scripts/build_sitemap.py"
  echo "DRY RUN — no sentinel created, no synth run."
  exit 0
fi

# --- Claim today's slot BEFORE running -------------------------------------
# Create the sentinel up front so that even if the synth crashes or the quota
# is exhausted mid-run, we do not re-fire the (expensive) synth again today.
# healthcheck.py will still detect the staleness tomorrow and retry then.
echo "--- claiming today's catch-up slot (creating sentinel) ---"
date '+%Y-%m-%d %H:%M:%S %Z' > "$SENTINEL"
echo "  sentinel created: $SENTINEL"

# 1. US synth (most important — default landing edition)
echo "--- US synth ---"
bash "$REPO/scripts/synthesize.sh"

# Check whether US produced a fresh brief by inspecting the live date.
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

# 4. Re-stamp the sentinel after the run so its mtime reflects completion.
#    (No self-teardown: this script is re-runnable; the sentinel — not a
#     removed LaunchAgent — is what prevents a second fire today.)
if echo "$US_LIVE" | grep -q "$US_TODAY"; then
  echo "--- US brief is fresh; catch-up succeeded ---"
  date '+%Y-%m-%d %H:%M:%S %Z (US fresh)' > "$SENTINEL"
else
  echo "--- US brief NOT fresh (quota may still be limited) ---"
  echo "    sentinel stays in place; healthcheck will retry on the next day."
fi

echo ""
echo "==============================================================="
echo "Synth catch-up finished at $(date)"
echo "==============================================================="
