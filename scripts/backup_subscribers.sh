#!/usr/bin/env bash
# backup_subscribers.sh — off-box backup of the ONLY irreplaceable data.
#
# The whole stack runs on one Mac mini against a single Docker postgres
# volume. The scraped corpus is reconstructable; the `email_subscribers`
# table (real confirmed newsletter subscribers + double-opt-in / unsubscribe
# tokens) is NOT. A disk failure or a bad `cleanup.sh` would lose it forever.
# Nothing backed it up until this script. (See the 2026-05-29 audit.)
#
# What it does, every run:
#   1. pg_dump the email_subscribers table (plain SQL) -> gzip -> backups/
#   2. VERIFY the dump's row count matches the live table (fail loud if not)
#   3. prune local dumps to the most recent $KEEP_LOCAL
#   4. push the dump off-box to s3://$BACKUP_BUCKET/subscribers/<date>/
#   5. any hard failure routes through scripts/alert.sh (off-box notify)
#
# With --full it ALSO writes a whole-DB pg_dump (custom format) for complete
# disaster recovery; the subscriber table is always the verified primary.
#
# Usage:
#   scripts/backup_subscribers.sh            # subscriber table, local + S3
#   scripts/backup_subscribers.sh --full     # + whole-DB dump
#   scripts/backup_subscribers.sh --local    # skip the S3 push
#
# Env:
#   BACKUP_S3_BUCKET  override the destination bucket (default below)
#   KEEP_LOCAL        local dumps to retain (default 30)
#
# Restore the subscriber list:
#   gunzip -c backups/subscribers/email_subscribers-<ts>.sql.gz \
#     | docker exec -i briefer_postgres psql -U briefer -d briefer
#
# Exit: 0 on success (local dump written + verified); 1 on a real failure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$SCRIPT_DIR/lib/env.sh"   # AWS, DOCKER, REPO, REGION

CONTAINER="briefer_postgres"
DB="briefer"
PGUSER="briefer"
TABLE="email_subscribers"

BACKUP_BUCKET="${BACKUP_S3_BUCKET:-briefer-news-backups}"
KEEP_LOCAL="${KEEP_LOCAL:-30}"

WANT_FULL=0
WANT_S3=1
for arg in "$@"; do
  case "$arg" in
    --full)  WANT_FULL=1 ;;
    --local) WANT_S3=0 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

TS="$(date +%Y%m%d-%H%M%S)"
DATE="$(date +%Y-%m-%d)"
OUT_DIR="$REPO/backups/subscribers"
mkdir -p "$OUT_DIR"
SUB_FILE="$OUT_DIR/${TABLE}-${TS}.sql.gz"

# alert helper — alert.sh always exits 0, never breaks us.
alert() { bash "$SCRIPT_DIR/alert.sh" "$1" "$2" "${3:-}" || true; }
log()   { echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] $*"; }

log "backup starting (bucket=$BACKUP_BUCKET keep_local=$KEEP_LOCAL full=$WANT_FULL s3=$WANT_S3)"

# ── 0. postgres reachable? ────────────────────────────────────────────────
if ! "$DOCKER" exec "$CONTAINER" pg_isready -U "$PGUSER" -d "$DB" >/dev/null 2>&1; then
  alert crit "Subscriber backup FAILED" "postgres container '$CONTAINER' not ready — no backup taken"
  log "ERROR: postgres not ready; aborting"
  exit 1
fi

# ── 1. dump the subscriber table ──────────────────────────────────────────
if ! "$DOCKER" exec "$CONTAINER" pg_dump -U "$PGUSER" -d "$DB" \
      -t "public.$TABLE" --no-owner --no-privileges 2>/dev/null \
      | gzip > "$SUB_FILE"; then
  rm -f "$SUB_FILE"
  alert crit "Subscriber backup FAILED" "pg_dump of $TABLE failed"
  log "ERROR: pg_dump failed; aborting"
  exit 1
fi

# ── 2. verify: dump data-row count == live row count ──────────────────────
LIVE_COUNT="$("$DOCKER" exec "$CONTAINER" psql -U "$PGUSER" -d "$DB" -tAc \
  "select count(*) from $TABLE;" 2>/dev/null | tr -d '[:space:]')"
# rows live between the COPY header and the terminating "\."
DUMP_COUNT="$(gunzip -c "$SUB_FILE" \
  | awk '/^COPY public\.'"$TABLE"' /{f=1;next} /^\\\.$/{f=0} f' \
  | grep -c . || true)"

if [ -z "$LIVE_COUNT" ] || [ "$LIVE_COUNT" != "$DUMP_COUNT" ]; then
  alert crit "Subscriber backup VERIFY FAILED" \
    "live=$LIVE_COUNT dump=$DUMP_COUNT in $SUB_FILE — dump kept for inspection"
  log "ERROR: verify mismatch (live=$LIVE_COUNT dump=$DUMP_COUNT); aborting"
  exit 1
fi
log "verified: $DUMP_COUNT rows dumped, matches live ($(du -h "$SUB_FILE" | cut -f1))"

# ── 3. optional whole-DB dump (custom format, for full DR) ─────────────────
FULL_FILE=""
if [ "$WANT_FULL" = "1" ]; then
  FULL_FILE="$OUT_DIR/../fulldb-${TS}.dump"
  if "$DOCKER" exec "$CONTAINER" pg_dump -U "$PGUSER" -d "$DB" -Fc \
        --no-owner --no-privileges > "$FULL_FILE" 2>/dev/null; then
    log "full-DB dump written ($(du -h "$FULL_FILE" | cut -f1))"
  else
    rm -f "$FULL_FILE"; FULL_FILE=""
    alert warn "Full-DB backup failed" "subscriber dump still succeeded"
    log "WARN: full-DB dump failed (subscriber dump is fine)"
  fi
fi

# ── 4. prune local subscriber dumps to the newest $KEEP_LOCAL ──────────────
# (no `mapfile`/`readarray` — macOS /bin/bash is 3.2 and lacks them)
PRUNED=0
while IFS= read -r old; do
  [ -n "$old" ] || continue
  rm -f "$old" && PRUNED=$((PRUNED + 1))
done < <(ls -1t "$OUT_DIR/${TABLE}-"*.sql.gz 2>/dev/null | tail -n +"$((KEEP_LOCAL + 1))")
if [ "$PRUNED" -gt 0 ]; then log "pruned $PRUNED local dump(s) beyond newest $KEEP_LOCAL"; fi

# ── 5. push off-box to S3 ──────────────────────────────────────────────────
if [ "$WANT_S3" = "0" ]; then
  log "S3 push skipped (--local); local backup at $SUB_FILE"
  log "backup done (local-only)"
  exit 0
fi

if [ ! -x "$AWS" ] || ! "$AWS" sts get-caller-identity >/dev/null 2>&1; then
  alert warn "Subscriber backup is local-only" "aws CLI missing/unauthed — $SUB_FILE not pushed off-box"
  log "WARN: aws unavailable; local backup kept, no off-box copy"
  exit 0
fi

if ! "$AWS" s3api head-bucket --bucket "$BACKUP_BUCKET" >/dev/null 2>&1; then
  alert warn "Subscriber backup is local-only" \
    "S3 bucket '$BACKUP_BUCKET' missing/inaccessible — create it to enable off-box backups"
  log "WARN: bucket '$BACKUP_BUCKET' not reachable; local backup kept, no off-box copy"
  exit 0
fi

S3_KEY="subscribers/${DATE}/${TABLE}-${TS}.sql.gz"
if "$AWS" s3 cp "$SUB_FILE" "s3://${BACKUP_BUCKET}/${S3_KEY}" --no-progress >/dev/null; then
  log "pushed off-box: s3://${BACKUP_BUCKET}/${S3_KEY}"
else
  alert crit "Subscriber backup S3 push FAILED" "$SUB_FILE written locally but not off-box"
  log "ERROR: s3 cp failed (local backup is fine)"
  exit 1
fi

if [ -n "$FULL_FILE" ]; then
  "$AWS" s3 cp "$FULL_FILE" "s3://${BACKUP_BUCKET}/fulldb/${DATE}/$(basename "$FULL_FILE")" \
    --no-progress >/dev/null && log "pushed full-DB dump off-box" || log "WARN: full-DB S3 push failed"
fi

log "backup done"
