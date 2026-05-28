#!/bin/bash
# briefer.news DB cleanup — sliding 7-day retention on articles & filter logs.
#
# Called from daily.sh after the scrape completes. Can also be run manually:
#   scripts/cleanup.sh                 # default 7-day retention
#   scripts/cleanup.sh --dry-run       # preview only, no DB writes
#   scripts/cleanup.sh --days 14       # custom retention
#
# What gets deleted (older than $RETENTION_DAYS):
#   - article_summaries (deleted first to satisfy article_id FK)
#   - articles
#   - rejected_url_hashes (filter log, no FK)
#
# What stays (never touched):
#   - sources (master data)
#   - daily_briefings (historical record of published briefs)
#   - scrape_runs (operational telemetry)
#   - The rendered brief HTML in the nginx volume's /archive/ (separate from DB)

set +e

REPO=/Users/maxgoshay/code/briefernewsapp
LOG_DIR="$REPO/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/cleanup-$(date +%Y%m%d).log"
exec >> "$LOG_FILE" 2>&1

DOCKER=/usr/local/bin/docker
RETENTION_DAYS=7
DRY_RUN=false

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=true ;;
    --days)    RETENTION_DAYS="$2"; shift ;;
    *)         echo "Unknown arg: $1"; exit 1 ;;
  esac
  shift
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Cleanup starting at $(date) — retention: ${RETENTION_DAYS} days, dry-run: ${DRY_RUN}"
echo "═══════════════════════════════════════════════════════════════"

# ── Filesystem rotation (runs regardless of DB state) ───────────────────────
# logs/ accrues one dated file per job per day; .run/ accrues stray *.log
# scratch. Prune by age so incident forensics stays a fast scan, not an mtime
# hunt across hundreds of files. NOTE: live .run state (*.html/.json/.md/.py)
# is deliberately NOT touched — only *.log there. Today's files (mtime now)
# and the constantly-appended daemon logs are always younger than the window.
LOG_RETENTION_DAYS=14
RUN_LOG_RETENTION_DAYS=7
echo ""
echo "--- Filesystem rotation (logs/ >${LOG_RETENTION_DAYS}d, .run/*.log >${RUN_LOG_RETENTION_DAYS}d) ---"
n_logs=$(find "$LOG_DIR" -type f -mtime +${LOG_RETENTION_DAYS} 2>/dev/null | wc -l | tr -d ' ')
n_runlogs=$(find "$REPO/.run" -maxdepth 1 -type f -name '*.log' -mtime +${RUN_LOG_RETENTION_DAYS} 2>/dev/null | wc -l | tr -d ' ')
echo "candidates — logs/: ${n_logs} file(s), .run/*.log: ${n_runlogs} file(s)"
if [ "$DRY_RUN" = "true" ]; then
  echo "DRY RUN — no files deleted."
else
  find "$LOG_DIR" -type f -mtime +${LOG_RETENTION_DAYS} -delete 2>/dev/null || true
  find "$REPO/.run" -maxdepth 1 -type f -name '*.log' -mtime +${RUN_LOG_RETENTION_DAYS} -delete 2>/dev/null || true
  echo "Pruned ${n_logs} log(s) + ${n_runlogs} run-log(s)."
fi

if ! "$DOCKER" ps --format '{{.Names}}' | grep -q briefer_postgres; then
  echo "ERROR: briefer_postgres not running — bailing"
  exit 0
fi

PSQL='"$DOCKER" exec briefer_postgres psql -U briefer -d briefer'

# ── Pre-counts ──────────────────────────────────────────────────────────────
echo ""
echo "--- Pre-cleanup state ---"
"$DOCKER" exec briefer_postgres psql -U briefer -d briefer -c "
  SELECT 'articles' AS table, COUNT(*) AS rows, pg_size_pretty(pg_total_relation_size('articles')) AS size FROM articles
  UNION ALL SELECT 'article_summaries', COUNT(*), pg_size_pretty(pg_total_relation_size('article_summaries')) FROM article_summaries
  UNION ALL SELECT 'rejected_url_hashes', COUNT(*), pg_size_pretty(pg_total_relation_size('rejected_url_hashes')) FROM rejected_url_hashes
  ORDER BY 1;
"

# ── Counts of rows that WOULD be deleted ────────────────────────────────────
echo ""
echo "--- Rows older than ${RETENTION_DAYS} days (delete candidates) ---"
"$DOCKER" exec briefer_postgres psql -U briefer -d briefer -c "
  SELECT
    (SELECT COUNT(*) FROM articles            WHERE scraped_at  < NOW() - INTERVAL '${RETENTION_DAYS} days') AS articles_to_delete,
    (SELECT COUNT(*) FROM article_summaries s
       JOIN articles a ON a.id = s.article_id WHERE a.scraped_at < NOW() - INTERVAL '${RETENTION_DAYS} days') AS summaries_to_delete,
    (SELECT COUNT(*) FROM rejected_url_hashes WHERE rejected_at < NOW() - INTERVAL '${RETENTION_DAYS} days') AS rejected_to_delete;
"

if [ "$DRY_RUN" = "true" ]; then
  echo ""
  echo "DRY RUN — no rows deleted."
  exit 0
fi

# ── Delete in a single transaction ──────────────────────────────────────────
echo ""
echo "--- Deleting (transaction) ---"
"$DOCKER" exec briefer_postgres psql -U briefer -d briefer -v ON_ERROR_STOP=1 <<SQL
BEGIN;

DELETE FROM article_summaries
  WHERE article_id IN (
    SELECT id FROM articles
    WHERE scraped_at < NOW() - INTERVAL '${RETENTION_DAYS} days'
  );

DELETE FROM articles
  WHERE scraped_at < NOW() - INTERVAL '${RETENTION_DAYS} days';

DELETE FROM rejected_url_hashes
  WHERE rejected_at < NOW() - INTERVAL '${RETENTION_DAYS} days';

COMMIT;
SQL

DELETE_EXIT=$?
if [ "$DELETE_EXIT" -ne 0 ]; then
  echo "ERROR: delete transaction failed (exit $DELETE_EXIT) — DB rolled back"
  exit 0
fi

# ── VACUUM ANALYZE outside transaction (reclaim disk + refresh stats) ──────
# Each VACUUM runs in its own psql call. Multi-statement `psql -c` wraps in
# an implicit transaction, which VACUUM is not allowed to run inside.
echo ""
echo "--- VACUUM ANALYZE (reclaim disk + refresh planner stats) ---"
"$DOCKER" exec briefer_postgres psql -U briefer -d briefer -c "VACUUM ANALYZE articles"
"$DOCKER" exec briefer_postgres psql -U briefer -d briefer -c "VACUUM ANALYZE article_summaries"
"$DOCKER" exec briefer_postgres psql -U briefer -d briefer -c "VACUUM ANALYZE rejected_url_hashes"

# ── Post-counts ─────────────────────────────────────────────────────────────
echo ""
echo "--- Post-cleanup state ---"
"$DOCKER" exec briefer_postgres psql -U briefer -d briefer -c "
  SELECT 'articles' AS table, COUNT(*) AS rows, pg_size_pretty(pg_total_relation_size('articles')) AS size FROM articles
  UNION ALL SELECT 'article_summaries', COUNT(*), pg_size_pretty(pg_total_relation_size('article_summaries')) FROM article_summaries
  UNION ALL SELECT 'rejected_url_hashes', COUNT(*), pg_size_pretty(pg_total_relation_size('rejected_url_hashes')) FROM rejected_url_hashes
  ORDER BY 1;
"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Cleanup complete at $(date)"
echo "═══════════════════════════════════════════════════════════════"
