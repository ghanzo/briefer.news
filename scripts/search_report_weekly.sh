#!/bin/bash
# Weekly Search Console snapshot — fired by the
# news.briefer.searchreport LaunchAgent every Monday 09:00 PT.
# Pulls the prior 7 days and saves a dated markdown file under logs/
# so each week's report is preserved for diffing over time.
set -euo pipefail

REPO="/Users/maxgoshay/code/briefernewsapp"
cd "$REPO"
mkdir -p logs
OUT="logs/search-weekly-$(date +%Y-%m-%d).md"

/usr/bin/python3 scripts/search_report.py --days 7 --out "$OUT" >/dev/null
echo "$(date -Iseconds)  wrote $OUT"
