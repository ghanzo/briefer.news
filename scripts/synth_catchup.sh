#!/bin/bash
# synth_catchup.sh — re-runnable mid-day catch-up synth + recovery.
#
# Recovers a STALE brief: re-runs both editions' synths, injects the weekly
# preview, and rebuilds feeds/sitemap. Each synth deploys to the live site.
#
# Triggered by:
#   - healthcheck.py (06:30) when it detects a stale edition
#   - its own LaunchAgent (news.briefer.synthcatchup) at 11:15 / 13:05 / 15:30
#   - manually: scripts/synth_catchup.sh
#
# SELF-HEALING DESIGN (2026-06-10): the ONLY reason this skips is that today's
# brief is already fresh. Freshness is read from the LOCALLY rendered US brief
# (.run/daily_with_weekly_us.html) — synthesize.sh writes it only on success,
# with today's stamp, so it is authoritative and (unlike a live curl) never
# fooled by CloudFront cache. A failed earlier attempt NO LONGER blocks a
# later same-day retry. The previous once-per-day ".done" sentinel DID block
# it — which is exactly why a quota-exhausted morning could not recover after
# the midday quota reset and had to be rescued by hand on 2026-06-10.
# Concurrency is guarded by an atomic mkdir lock instead of that sentinel.
#
# (Prior bug also fixed here: the old freshness check used `date +%b` → "JUN",
#  but the stamp is the full month "JUNE", so it always false-negatived.)
#
# Usage:
#   scripts/synth_catchup.sh            # recover if (and only if) stale
#   scripts/synth_catchup.sh --dry-run  # print the plan, no synth

set +e

REPO=/Users/maxgoshay/code/briefernewsapp
cd "$REPO" || exit 1

DRY_RUN=false
if [ "${1:-}" = "--dry-run" ]; then DRY_RUN=true; fi

RUN_DIR="$REPO/.run"
mkdir -p "$RUN_DIR"

# Reliable "is today's brief done?" signal: the LOCALLY rendered US brief.
US_LOCAL="$RUN_DIR/daily_with_weekly_us.html"
TODAY_STAMP=$(date +"%B %-d, %Y" | tr '[:lower:]' '[:upper:]')   # e.g. "JUNE 10, 2026"
LOCK="$RUN_DIR/catchup.lock"

us_fresh() { [ -f "$US_LOCAL" ] && grep -q "stamp\">$TODAY_STAMP" "$US_LOCAL"; }

# In a real run, append to a timestamped log. In a dry run, keep output on
# stdout so the caller (and the verifier) can see the plan directly.
if [ "$DRY_RUN" = "false" ]; then
  LOG="$REPO/logs/synth-catchup-$(date +%Y%m%d-%H%M).log"
  mkdir -p "$REPO/logs"
  exec >> "$LOG" 2>&1
fi

echo "==============================================================="
echo "Synth catch-up invoked at $(date) (dry_run=$DRY_RUN)"
echo "  today stamp: $TODAY_STAMP"
echo "==============================================================="

# --- Guard 1: skip ONLY if the brief is already fresh ----------------------
if us_fresh; then
  echo "US brief already fresh ($TODAY_STAMP) — nothing to do, exiting 0"
  exit 0
fi

if [ "$DRY_RUN" = "true" ]; then
  echo "DRY RUN — US brief is NOT fresh, so a real run WOULD:"
  echo "  1. acquire lock:    $LOCK"
  echo "  2. run US synth:    bash $REPO/scripts/synthesize.sh"
  echo "  3. run China synth: bash $REPO/scripts/synthesize_china.sh"
  echo "  4. inject weekly:   python3 $REPO/scripts/inject_weekly_preview.py"
  echo "  5. build feeds:     python3 $REPO/scripts/build_feeds.py"
  echo "  6. build sitemap:   python3 $REPO/scripts/build_sitemap.py"
  echo "DRY RUN — no lock taken, no synth run."
  exit 0
fi

# --- Guard 2: concurrency lock (atomic mkdir; reclaim if >30 min stale) ----
if [ -d "$LOCK" ] && [ -z "$(find "$LOCK" -mmin -30 2>/dev/null)" ]; then
  echo "--- reclaiming stale lock (>30 min old) ---"
  rmdir "$LOCK" 2>/dev/null
fi
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "another catch-up is already running (lock held) — exiting 0"
  exit 0
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT
echo "--- lock acquired: $LOCK ---"

# 1. US synth (most important — default landing edition)
echo "--- US synth ---"
bash "$REPO/scripts/synthesize.sh"
if us_fresh; then
  echo "  US brief rendered fresh ($TODAY_STAMP) ✓"
else
  echo "  US brief still NOT fresh — quota may still be limited; a later trigger will retry."
fi

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

# 4. Final verdict (reliable local signal; lock auto-released by the EXIT trap)
if us_fresh; then
  echo "--- US brief is fresh; catch-up succeeded ---"
else
  echo "--- US brief NOT fresh; will retry on the next trigger (no sentinel blocks it now) ---"
fi

echo ""
echo "==============================================================="
echo "Synth catch-up finished at $(date)"
echo "==============================================================="
