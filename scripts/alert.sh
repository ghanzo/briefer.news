#!/bin/bash
# alert.sh — the single off-box notifier for briefer.news.
#
# Before this, the ONLY alerting in the whole system was healthcheck.py's
# osascript banner, which never leaves the Mac — so synth bail-outs, the
# 2-day morning_brief outage, swallowed post failures, etc. were all silent.
# Route every "this failed and a human needs to know" branch through here.
#
#   scripts/alert.sh <severity> <message...>
#   scripts/alert.sh crit "synth bailed: preflight backtick lint failed"
#   some_command 2>&1 | scripts/alert.sh warn -        # message from stdin
#   scripts/alert.sh --dry-run info "test"             # build payload, don't send
#
#   severity : info | warn | crit  (free-form; shown in the subject)
#   message  : the rest of the args, or "-" / empty to read from stdin
#
# Delivery: emails via the same SESv2 path the newsletter uses (production
# SES, From news@briefer.news, default AWS profile / us-east-1). Always logs
# to logs/alerts.log. Falls back to a local osascript banner if SES fails so
# the alert is never lost. Exit 0 if any channel delivered, 1 if none did.
#
# Recipient: $ALERT_EMAIL env  ->  ALERT_EMAIL in .env  ->  max.goshay@gmail.com
# This is an OPERATIONAL alert, NOT a subscriber send: it is deliberately NOT
# gated by EMAIL_ENABLED / EMAIL_DAILY_CAP (those guard the newsletter blast).

set -uo pipefail

REPO="/Users/maxgoshay/code/briefernewsapp"
ENV_FILE="$REPO/.env"
LOG_DIR="$REPO/logs"
AWS="/Users/maxgoshay/.local/bin/aws"   # absolute — PATH isn't set under launchd
REGION="us-east-1"
mkdir -p "$LOG_DIR"

# Read a key from .env without sourcing it (.env has unquoted spaces).
get_env() {
  local key="$1" default="${2:-}" val=""
  if [ -f "$ENV_FILE" ]; then
    val="$(grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | sed 's/^"//; s/"$//')"
  fi
  printf '%s' "${val:-$default}"
}

DRY_RUN=false
if [ "${1:-}" = "--dry-run" ]; then DRY_RUN=true; shift; fi

SEVERITY="${1:-info}"; shift || true
MESSAGE="$*"
# Pull message from stdin when asked ("-") or when no message arg was given.
if [ "$MESSAGE" = "-" ] || { [ -z "$MESSAGE" ] && [ ! -t 0 ]; }; then
  MESSAGE="$(cat)"
fi
[ -z "$MESSAGE" ] && MESSAGE="(no message)"

FROM_ADDR="$(get_env EMAIL_FROM_ADDRESS news@briefer.news)"
FROM_NAME="$(get_env EMAIL_FROM_NAME 'Briefer News')"
FROM="\"$FROM_NAME\" <$FROM_ADDR>"
TO="${ALERT_EMAIL:-$(get_env ALERT_EMAIL max.goshay@gmail.com)}"

HOST="$(hostname -s 2>/dev/null || echo mac)"
TS="$(date '+%Y-%m-%d %H:%M:%S %Z')"
FIRST_LINE="$(printf '%s' "$MESSAGE" | head -1 | cut -c1-90)"
SUBJECT="[briefer.news][$(printf '%s' "$SEVERITY" | tr '[:lower:]' '[:upper:]')] ${FIRST_LINE}"
BODY="$(printf 'severity: %s\nhost: %s\ntime: %s\n\n%s\n' "$SEVERITY" "$HOST" "$TS" "$MESSAGE")"

# Build the SES payload with python (json.dumps handles all escaping safely).
PAYLOAD="$(mktemp -t briefer_alert.XXXXXX.json)"
trap 'rm -f "$PAYLOAD"' EXIT
FROM="$FROM" TO="$TO" SUBJECT="$SUBJECT" BODY="$BODY" python3 - "$PAYLOAD" <<'PY'
import json, os, sys
json.dump({
    "FromEmailAddress": os.environ["FROM"],
    "Destination": {"ToAddresses": [os.environ["TO"]]},
    "Content": {"Simple": {
        "Subject": {"Data": os.environ["SUBJECT"], "Charset": "UTF-8"},
        "Body": {"Text": {"Data": os.environ["BODY"], "Charset": "UTF-8"}},
    }},
}, open(sys.argv[1], "w"))
PY

log_line() { printf '%s\t%s\t%s\t%s\n' "$TS" "$SEVERITY" "$1" "$FIRST_LINE" >> "$LOG_DIR/alerts.log"; }

if [ "$DRY_RUN" = "true" ]; then
  echo "DRY RUN — would send to $TO as: $SUBJECT"
  cat "$PAYLOAD"; echo
  log_line "dryrun"
  exit 0
fi

# ── Delivery mode ──────────────────────────────────────────────────────────
# Every alert is ALWAYS logged to alerts.log (above) regardless of mode. This
# gates only the IMMEDIATE email, to end alert-email fatigue. The once-a-day
# digest (scripts/alert_digest.sh) then emails ONE readable summary of the day.
#   digest : never email immediately — log only            (the quiet default)
#   crit   : email immediately only when severity is crit  (safety net)
#   all    : email every alert immediately                 (legacy; used by the
#            digest itself, which sets ALERT_EMAIL_MODE=all to force its send)
MODE="${ALERT_EMAIL_MODE:-$(get_env ALERT_EMAIL_MODE digest)}"
SEV_LC="$(printf '%s' "$SEVERITY" | tr '[:upper:]' '[:lower:]')"
case "$MODE" in
  all) ;;  # fall through to the immediate send
  crit)
    if [ "$SEV_LC" != "crit" ]; then
      log_line "log-only(mode=crit)"
      echo "alert logged (mode=crit, severity=$SEVERITY) — no immediate email; in the daily digest"
      exit 0
    fi
    ;;
  digest|*)
    log_line "log-only(mode=$MODE)"
    echo "alert logged (mode=$MODE) — no immediate email; in the daily digest"
    exit 0
    ;;
esac

# Primary channel: SES email (off-box).
if OUT="$("$AWS" sesv2 send-email --region "$REGION" \
        --cli-input-json "file://$PAYLOAD" --output json 2>&1)"; then
  MID="$(printf '%s' "$OUT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("MessageId",""))' 2>/dev/null || true)"
  echo "alert sent to $TO (MessageId=$MID)"
  log_line "ses:$MID"
  exit 0
fi

# Fallback: local banner so the alert is never lost, and record the SES error.
echo "ALERT: SES send failed, falling back to local notification" >&2
printf '%s\n' "$OUT" >&2
osascript -e "display notification \"$FIRST_LINE\" with title \"briefer.news $SEVERITY\"" 2>/dev/null || true
log_line "ses-FAILED-osascript-fallback"
exit 1
