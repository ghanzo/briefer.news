#!/bin/bash
# alert_digest.sh — once a day, email ONE readable summary of every alert logged
# today, instead of a separate email per alert.
#
# Pairs with alert.sh's default log-only mode (ALERT_EMAIL_MODE=digest): all
# alerts still land in logs/alerts.log immediately, and this rolls them into a
# single grouped digest email. Skips silently on a day with no alerts, so you
# only ever get the digest when something actually happened.
#
#   scripts/alert_digest.sh          # email today's digest (or nothing)
#   scripts/alert_digest.sh --dry-run

set -uo pipefail

REPO="/Users/maxgoshay/code/briefernewsapp"
LOG="$REPO/logs/alerts.log"
TODAY="$(date '+%Y-%m-%d')"
DRY=""
[ "${1:-}" = "--dry-run" ] && DRY="--dry-run"

[ -f "$LOG" ] || { echo "no alerts.log yet — nothing to digest"; exit 0; }

# Today's alerts, excluding the digest's own log lines (severity 'digest') so it
# never reports on itself.
LINES="$(awk -F'\t' -v d="$TODAY" 'index($1, d)==1 && tolower($2) != "digest"' "$LOG")"
if [ -z "$LINES" ]; then
  echo "no alerts logged today ($TODAY) — no digest sent"
  exit 0
fi

N=$(printf '%s\n' "$LINES" | grep -c .)
NCRIT=$(printf '%s\n' "$LINES" | awk -F'\t' 'tolower($2)=="crit"' | grep -c . || true)
NWARN=$(printf '%s\n' "$LINES" | awk -F'\t' 'tolower($2)=="warn"' | grep -c . || true)
NOTHER=$(( N - NCRIT - NWARN ))

BODY="$(
  printf 'briefer.news — alert digest for %s\n\n' "$TODAY"
  printf '%d alert(s) today: %d crit, %d warn, %d other\n' "$N" "$NCRIT" "$NWARN" "$NOTHER"
  printf '(full detail: logs/alerts.log. Alerts are log-only by default; set ALERT_EMAIL_MODE=crit or =all in .env to also email immediately.)\n'
  for sev in crit warn other; do
    sect="$(printf '%s\n' "$LINES" | awk -F'\t' -v s="$sev" '
      { l=tolower($2) }
      (s=="crit" && l=="crit") || (s=="warn" && l=="warn") || (s=="other" && l!="crit" && l!="warn") {
        ts=$1; sub(/^[0-9-]+ /,"",ts); sub(/ [A-Z]+$/,"",ts);   # -> HH:MM:SS
        printf "  %s  %s\n", ts, $4 }')"
    if [ -n "$sect" ]; then
      label="$(printf '%s' "$sev" | tr '[:lower:]' '[:upper:]')"
      printf '\n%s:\n%s\n' "$label" "$sect"
    fi
  done
)"

# Send exactly one email through the shared SES path, forcing it past the
# log-only gate (the digest IS the email the gate is saving up for).
ALERT_EMAIL_MODE=all bash "$REPO/scripts/alert.sh" $DRY digest "$BODY"
