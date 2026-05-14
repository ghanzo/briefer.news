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
#   1. og_weekly.sh    — aggregates the week's Outside the Gate items
#                         (cheap, ~30s, no Claude calls)
#   2. weekly.sh       — full weekly digest with Claude synthesis per
#                         edition (~3-5 min total)
#   3. archive_index   — rebuild the per-edition archive index pages
#                         so any new brief published this morning is
#                         listed there (~5s, no Claude calls)
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
echo "── Stage 2/3: weekly.sh ──"
"$REPO/scripts/weekly.sh"

echo ""
echo "── Stage 3/3: archive_index ──"
DOCKER=/usr/local/bin/docker
AWS=/Users/maxgoshay/.local/bin/aws
RUN_DIR="$REPO/.run"
python3 "$REPO/scripts/archive_index.py"

if [ -s "$RUN_DIR/archive_index_usa.html" ] && [ -s "$RUN_DIR/archive_index_china.html" ]; then
  "$DOCKER" run --rm \
    -v "$RUN_DIR":/src:ro \
    -v briefernewsapp_site_output:/dst \
    alpine sh -c "
      cp /src/archive_index_usa.html   /dst/usa/archive/index.html
      cp /src/archive_index_china.html /dst/china/archive/index.html
    "
  if [ -x "$AWS" ] && "$AWS" sts get-caller-identity >/dev/null 2>&1; then
    "$AWS" s3 cp "$RUN_DIR/archive_index_usa.html"   s3://briefer-news-site/usa/archive/index.html   --content-type "text/html; charset=utf-8" --cache-control "no-store, no-cache" >/dev/null && echo "S3: usa/archive/index uploaded"
    "$AWS" s3 cp "$RUN_DIR/archive_index_china.html" s3://briefer-news-site/china/archive/index.html --content-type "text/html; charset=utf-8" --cache-control "no-store, no-cache" >/dev/null && echo "S3: china/archive/index uploaded"
    "$AWS" cloudfront create-invalidation \
      --distribution-id EMV1VIFYTSI3U \
      --paths "/usa/archive/index.html" "/usa/archive/" "/china/archive/index.html" "/china/archive/" \
      --query 'Invalidation.Id' --output text \
      && echo "CloudFront: invalidation created" \
      || echo "CloudFront: invalidation FAILED (non-fatal)"
  else
    echo "AWS CLI unavailable — archive index deployed only to nginx volume"
  fi
else
  echo "archive_index.py produced no output — skipping deploy"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Daily digests refresh complete at $(date)"
echo "═══════════════════════════════════════════════════════════════"
