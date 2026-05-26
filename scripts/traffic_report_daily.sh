#!/bin/bash
# Daily traffic snapshot — fired by the news.briefer.trafficreport
# LaunchAgent every day at 10:00 PT (after most of yesterday's
# CloudFront logs have been delivered to S3). Writes a dated
# markdown report under logs/ so each day is preserved for trending.
set -euo pipefail

REPO="/Users/maxgoshay/code/briefernewsapp"
cd "$REPO"
mkdir -p logs

YESTERDAY=$(/bin/date -v-1d +%Y-%m-%d)
OUT="logs/traffic-daily-${YESTERDAY}.md"

/usr/bin/python3 scripts/traffic_report.py --date "$YESTERDAY" --out "$OUT" >/dev/null
echo "$(/bin/date -Iseconds)  wrote $OUT"
