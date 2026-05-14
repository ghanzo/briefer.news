#!/bin/bash
# og_weekly.sh — Build and deploy the Outside the Gate weekly digest pages.
#
# Reads the past 7 days of archived daily briefs (from the nginx docker
# volume), pulls all Outside the Gate items, and renders one HTML page
# per edition. Pages publish at:
#   briefer.news/usa/og-week/
#   briefer.news/china/og-week/
#
# Intended cadence: Saturday morning (LaunchAgent setup deferred — for
# now this script is invoked manually or via the scheduled remote agent
# during the rollout phase).
#
# Failure mode: any stage fails → log, exit 0, leave previous page live.

set +e

REPO=/Users/maxgoshay/code/briefernewsapp
cd "$REPO"

LOG_DIR="$REPO/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/og-weekly-$(date +%Y%m%d).log"
exec >> "$LOG_FILE" 2>&1

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "OG weekly build starting at $(date)"
echo "═══════════════════════════════════════════════════════════════"

DOCKER=/usr/local/bin/docker
TODAY=$(date +%Y-%m-%d)
RUN_DIR="$REPO/.run"
mkdir -p "$RUN_DIR"

if ! "$DOCKER" ps --format '{{.Names}}' | grep -q briefer_nginx; then
  echo "ERROR: briefer_nginx not running — cannot read archives; bailing"
  exit 0
fi

# ── Stage 1: aggregate the week's OG items ─────────────────────────────────
echo "--- Stage 1: aggregating last 7 days of OG items ---"
python3 "$REPO/scripts/og_weekly_aggregate.py" "$TODAY" "$RUN_DIR/og_weekly.json"

if [ ! -s "$RUN_DIR/og_weekly.json" ]; then
  echo "ERROR: aggregator produced no output — bailing"
  exit 0
fi

# ── Stage 2: render per-edition HTML pages ─────────────────────────────────
echo "--- Stage 2: rendering HTML pages ---"
python3 "$REPO/scripts/og_weekly_render.py" "$RUN_DIR/og_weekly.json"

US_PAGE="$RUN_DIR/og_week_usa.html"
CN_PAGE="$RUN_DIR/og_week_china.html"

for p in "$US_PAGE" "$CN_PAGE"; do
  if [ ! -s "$p" ]; then
    echo "ERROR: missing rendered page $p — bailing"
    exit 0
  fi
done

US_BYTES=$(wc -c < "$US_PAGE")
CN_BYTES=$(wc -c < "$CN_PAGE")
echo "  usa:   $US_BYTES bytes"
echo "  china: $CN_BYTES bytes"

# ── Stage 3: deploy to local nginx volume /usa/og-week/ + /china/og-week/ ──
echo "--- Stage 3: deploying to nginx volume ---"
"$DOCKER" run --rm \
  -v "$RUN_DIR":/src:ro \
  -v briefernewsapp_site_output:/dst \
  alpine sh -c "
    mkdir -p /dst/usa/og-week /dst/china/og-week
    cp /src/og_week_usa.html   /dst/usa/og-week/index.html
    cp /src/og_week_china.html /dst/china/og-week/index.html
    echo 'nginx volume layout:'
    ls -la /dst/usa/og-week /dst/china/og-week
  "

# ── Stage 4: publish to S3 + CloudFront invalidate ─────────────────────────
S3_BUCKET=briefer-news-site
DIST_ID=EMV1VIFYTSI3U
AWS=/Users/maxgoshay/.local/bin/aws

if [ -x "$AWS" ] && "$AWS" sts get-caller-identity >/dev/null 2>&1; then
  echo ""
  echo "--- Stage 4: publishing to S3 + CloudFront ---"

  "$AWS" s3 cp "$US_PAGE" "s3://${S3_BUCKET}/usa/og-week/index.html" \
    --content-type "text/html; charset=utf-8" \
    --cache-control "no-store, no-cache" \
    && echo "S3: usa/og-week uploaded" \
    || echo "S3: usa/og-week upload FAILED (non-fatal)"

  "$AWS" s3 cp "$CN_PAGE" "s3://${S3_BUCKET}/china/og-week/index.html" \
    --content-type "text/html; charset=utf-8" \
    --cache-control "no-store, no-cache" \
    && echo "S3: china/og-week uploaded" \
    || echo "S3: china/og-week upload FAILED (non-fatal)"

  "$AWS" cloudfront create-invalidation \
    --distribution-id "$DIST_ID" \
    --paths "/usa/og-week/index.html" "/china/og-week/index.html" \
            "/usa/og-week/" "/china/og-week/" \
    --query 'Invalidation.Id' --output text \
    && echo "CloudFront: invalidation created" \
    || echo "CloudFront: invalidation FAILED (non-fatal)"
else
  echo "--- Stage 4: skipped — AWS CLI unavailable or unauthenticated ---"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "OG weekly build complete at $(date)"
echo "  US:    https://briefer.news/usa/og-week/"
echo "  China: https://briefer.news/china/og-week/"
echo "═══════════════════════════════════════════════════════════════"
