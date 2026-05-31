#!/bin/bash
# briefer.news daily run — the scrape stage. Runs TWICE a day:
#   MODE=full   (default) — overnight run via news.briefer.daily.plist (04:00).
#                Scrapes, then runs Stage 2 cleanup (DB retention).
#   MODE=midday           — bonus daytime refresh via news.briefer.midday.plist
#                (~12:30). Same scrape block, NO cleanup (the window is
#                re-enforced at the next full run), and failures alert at 'warn'
#                not 'crit' because the morning brief already shipped.
#
# What the scrape does:
#   1. Ensures Postgres is up (no-op if already running)
#   2. Runs the standard RSS scrape (~10-60 min, ~40 sources)
#   3. Runs the Akamai-protected scrape (~30-150 min, 6 sources, rate-limited)
#   (the China scrape runs in the same parallel block; see below.)
# Dedup is by url_hash, so a second daily pass only adds genuinely-new articles.
#
# AI synthesis IS fully wired and autonomous (as of 2026-05-09): the separate
# news.briefer.synthesize / .synthesize.china LaunchAgents call headless Claude
# Code and deploy each brief on their own. No manual publish.

set -e

MODE="${1:-full}"
case "$MODE" in
  full|midday) ;;
  *) echo "usage: daily.sh [full|midday]" >&2; exit 2 ;;
esac

REPO=/Users/maxgoshay/code/briefernewsapp
cd "$REPO"

LOG_DIR="$REPO/logs"
mkdir -p "$LOG_DIR"
if [ "$MODE" = "midday" ]; then
  LOG_FILE="$LOG_DIR/daily-midday-$(date +%Y%m%d).log"
else
  LOG_FILE="$LOG_DIR/daily-$(date +%Y%m%d).log"
fi
exec >> "$LOG_FILE" 2>&1

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Daily run (mode=$MODE) starting at $(date)"
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
# lines are prefixed so you can disentangle them.
#
# Capture each scraper's REAL exit code, not the prefixing sed's. Each scrape
# is a `docker … | sed` pipeline; the old `wait $!; $?` returned the sed exit
# (≈always 0), which on 2026-05-27 SILENTLY masked a total ingest failure —
# the akamai+china containers failed to even launch (lens.md mount race) yet
# the run reported "rss=0 akamai=0 china=0 … completed". We now run each scrape
# in its own backgrounded subshell that records ${PIPESTATUS[0]} (the
# docker/python exit, 127 if it never ran) to a file, then read those back and
# alert off-box on any non-zero. No `set -o pipefail`: with `set -e` it would
# abort the subshell before the code is recorded; PIPESTATUS[0] is the robust
# capture instead.
echo ""
echo "--- Stage 1: parallel scrapes ---"

RC_DIR="$(mktemp -d "${TMPDIR:-/tmp}/briefer-scrape.XXXXXX")"

run_scrape() {  # <label> <rc_file> <main.py args…>
  local label="$1" rc_file="$2"; shift 2
  "$DOCKER" compose run --rm pipeline python main.py "$@" 2>&1 | sed "s/^/[$label] /"
  echo "${PIPESTATUS[0]}" > "$rc_file"
}

run_scrape rss    "$RC_DIR/rss"    --scrape-only &
run_scrape akamai "$RC_DIR/akamai" --akamai-only &
run_scrape china  "$RC_DIR/china"  --china-only  &
wait

RSS_EXIT="$(cat "$RC_DIR/rss"    2>/dev/null || echo 127)"
AKAMAI_EXIT="$(cat "$RC_DIR/akamai" 2>/dev/null || echo 127)"
CHINA_EXIT="$(cat "$RC_DIR/china"  2>/dev/null || echo 127)"
rm -rf "$RC_DIR"

echo ""
echo "Scrape exit codes — rss=$RSS_EXIT  akamai=$AKAMAI_EXIT  china=$CHINA_EXIT"

# Alert off-box on any scrape failure. 127 = the subshell never recorded a
# code (container failed to launch) — also a failure. alert.sh always exits 0;
# the `if` guard keeps `set -e` happy.
SCRAPE_FAILED=""
for pair in "rss=$RSS_EXIT" "akamai=$AKAMAI_EXIT" "china=$CHINA_EXIT"; do
  if [ "${pair#*=}" != "0" ]; then SCRAPE_FAILED="$SCRAPE_FAILED ${pair%%=*}(exit=${pair#*=})"; fi
done
if [ -n "$SCRAPE_FAILED" ]; then
  echo "ALERT: scrape failure —$SCRAPE_FAILED"
  if [ "$MODE" = "midday" ]; then
    "$REPO/scripts/alert.sh" warn "Midday refresh scrape FAILED:$SCRAPE_FAILED" \
      "daily.sh midday run on the mini — a scraper exited non-zero. The morning brief already shipped; today's corpus just did not get its bonus daytime refresh. See logs/daily-midday-$(date +%Y%m%d).log." || true
  else
    "$REPO/scripts/alert.sh" crit "Overnight scrape FAILED:$SCRAPE_FAILED" \
      "daily.sh on the mini — a scraper exited non-zero (127 = container never launched). Corpus may be stale; the 07:00/07:30 synth keeps yesterday's brief if too few fresh articles land. See logs/daily-$(date +%Y%m%d).log." || true
  fi
fi

# ── Stage 2: cleanup old articles (14-day retention) ────────────────────────
# Only on the full overnight run. Midday is a bonus corpus refresh; the
# retention window is re-enforced at the next full run, and a midday VACUUM x3
# would be wasteful churn.
if [ "$MODE" = "midday" ]; then
  echo ""
  echo "--- Stage 2: cleanup SKIPPED (midday mode) ---"
else
  echo ""
  echo "--- Stage 2: cleanup ---"
  "$REPO/scripts/cleanup.sh"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Daily run (mode=$MODE) completed at $(date)"
echo "═══════════════════════════════════════════════════════════════"

# Surface scrape failure in the LaunchAgent's exit status (read by morning_brief
# + launchctl) — after cleanup + the off-box alert have already run.
if [ -n "$SCRAPE_FAILED" ]; then
  echo "Exiting non-zero due to scrape failure(s):$SCRAPE_FAILED"
  exit 1
fi
