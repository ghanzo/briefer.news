#!/bin/bash
# briefer.news daily run — Path A (scrape only, manual brief publish).
# Triggered by ~/Library/LaunchAgents/news.briefer.daily.plist at 04:00 local time.
#
# What this does:
#   1. Ensures Postgres is up (no-op if already running)
#   2. Runs the standard RSS scrape (~10-60 min, ~40 sources)
#   3. Runs the Akamai-protected scrape (~30-150 min, 6 sources, rate-limited)
#
# Stage 2/3 (AI synthesis) NOT yet wired — brief is published manually for now.
# That comes later via a separate LaunchAgent calling headless Claude Code.

set -e

REPO=/Users/maxgoshay/code/briefernewsapp
cd "$REPO"

LOG_DIR="$REPO/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/daily-$(date +%Y%m%d).log"
exec >> "$LOG_FILE" 2>&1

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Daily run starting at $(date)"
echo "═══════════════════════════════════════════════════════════════"

DOCKER=/usr/local/bin/docker

# Make sure Docker daemon is up. Docker Desktop on macOS auto-starts at login.
# If it's not running, give it 60s before bailing.
for i in 1 2 3 4 5 6; do
  if "$DOCKER" info >/dev/null 2>&1; then
    break
  fi
  echo "Docker not ready, sleeping 10s (attempt $i/6)…"
  sleep 10
done
if ! "$DOCKER" info >/dev/null 2>&1; then
  echo "Docker is not running after 60s. Aborting."
  exit 1
fi

# Bring up postgres (no-op if already up via restart policy)
"$DOCKER" compose up -d postgres
sleep 5
"$DOCKER" compose ps postgres

# ── Stage 1: parallel scrapes (RSS + Akamai + China) ────────────────────────
# All three scrapes fire concurrently — each is mostly network-bound on a
# different set of remote servers, so they don't compete for resources. Log
# lines are prefixed so you can disentangle them. Cleanup waits for all to
# finish via the wait calls below.
echo ""
echo "--- Stage 1: parallel scrapes ---"
"$DOCKER" compose run --rm pipeline python main.py --scrape-only 2>&1 | sed 's/^/[rss]    /' &
RSS_PID=$!
"$DOCKER" compose run --rm pipeline python main.py --akamai-only 2>&1 | sed 's/^/[akamai] /' &
AKAMAI_PID=$!
"$DOCKER" compose run --rm pipeline python main.py --china-only 2>&1 | sed 's/^/[china]  /' &
CHINA_PID=$!

wait $RSS_PID;    RSS_EXIT=$?
wait $AKAMAI_PID; AKAMAI_EXIT=$?
wait $CHINA_PID;  CHINA_EXIT=$?

echo ""
echo "Scrape exit codes — rss=$RSS_EXIT  akamai=$AKAMAI_EXIT  china=$CHINA_EXIT"

# ── Stage 2: cleanup old articles (7-day retention) ─────────────────────────
echo ""
echo "--- Stage 2: cleanup ---"
"$REPO/scripts/cleanup.sh"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Daily run completed at $(date)"
echo "═══════════════════════════════════════════════════════════════"
