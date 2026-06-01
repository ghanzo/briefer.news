#!/bin/bash
# briefer.news DB cleanup — sliding 14-day retention on articles & filter logs.
#
# Called from daily.sh after the scrape completes. Can also be run manually:
#   scripts/cleanup.sh                 # default 14-day retention (RETENTION_DAYS env-overridable)
#   scripts/cleanup.sh --dry-run       # preview only, no DB writes
#   scripts/cleanup.sh --days 21       # custom retention
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
RETENTION_DAYS="${RETENTION_DAYS:-14}"
DRY_RUN=false

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=true ;;
    --days)    RETENTION_DAYS="$2"; shift ;;
    *)         echo "Unknown arg: $1"; exit 1 ;;
  esac
  shift
done

# Guard: retention MUST be a positive integer. Rejects '--days 0' (which would
# wipe the entire scrape corpus) and any non-numeric value.
if ! printf '%s' "$RETENTION_DAYS" | grep -Eq '^[1-9][0-9]*$'; then
  echo "ERROR: RETENTION_DAYS must be a positive integer, got '${RETENTION_DAYS}'" >&2
  exit 2
fi

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
echo "--- Filesystem rotation (logs/ >${LOG_RETENTION_DAYS}d, .run/ >${RUN_LOG_RETENTION_DAYS}d) ---"
n_logs=$(find "$LOG_DIR" -type f -mtime +${LOG_RETENTION_DAYS} 2>/dev/null | wc -l | tr -d ' ')
# Prune ALL transient .run/ scratch older than the window — not just *.log. The
# synth + Claude write one-off helper scripts (extract_ids.py, dump.py, …) and
# render artifacts (html/json/txt) here every run; they otherwise accumulate
# forever. maxdepth 1 keeps any intentional subdir untouched.
n_run=$(find "$REPO/.run" -maxdepth 1 -type f -mtime +${RUN_LOG_RETENTION_DAYS} 2>/dev/null | wc -l | tr -d ' ')
echo "candidates — logs/: ${n_logs} file(s), .run/: ${n_run} file(s)"
if [ "$DRY_RUN" = "true" ]; then
  echo "DRY RUN — no files deleted."
else
  find "$LOG_DIR" -type f -mtime +${LOG_RETENTION_DAYS} -delete 2>/dev/null || true
  find "$REPO/.run" -maxdepth 1 -type f -mtime +${RUN_LOG_RETENTION_DAYS} -delete 2>/dev/null || true
  echo "Pruned ${n_logs} log(s) + ${n_run} .run file(s)."
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
# NOTE the -i: this psql reads its SQL from the heredoc on STDIN, and `docker
# exec` does NOT forward stdin to the container process without -i. Without it,
# psql got empty input, ran nothing, and exited 0 — so retention SILENTLY never
# deleted anything (the DB grew unbounded; 5k+ stale rows survived) while the log
# printed "Cleanup complete". The -c calls above don't use stdin, which is why
# only this DELETE block was broken.
"$DOCKER" exec -i briefer_postgres psql -U briefer -d briefer -v ON_ERROR_STOP=1 <<SQL
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
