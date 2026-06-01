#!/bin/bash
# redeploy_today.sh — re-publish TODAY's already-generated brief WITHOUT re-running
# the synth (no Claude calls).
#
# Why this exists: the synth generates a correct brief into .run/, then validates,
# then deploys. If the deploy is aborted by a downstream bug (e.g. the 2026-06-01
# validate_brief month-format bug that kept both editions pinned to MAY 31) but the
# .run artifact is actually fine, you don't want to burn Claude quota regenerating
# it — you just want to re-run the validate + deploy on the existing artifact.
#
# It mirrors Stage 5/6 of synthesize.sh + synthesize_china.sh EXACTLY (same
# deploy_artifact/invalidate_paths helpers, same S3 keys, cache headers, archive
# canonical rewrite, and nginx volume copy), and re-validates first — a brief that
# fails validation is skipped, never force-pushed.
#
#   scripts/redeploy_today.sh            # both editions
#   scripts/redeploy_today.sh us         # one edition
#   scripts/redeploy_today.sh china

set -uo pipefail

REPO="/Users/maxgoshay/code/briefernewsapp"
RUN_DIR="$REPO/.run"
TODAY=$(date +%Y-%m-%d)
DOCKER=/usr/local/bin/docker

# Shared infra constants + deploy helpers (deploy_artifact / invalidate_paths /
# aws_ready), same source of truth the synth scripts use.
. "$REPO/scripts/lib/deploy.sh"

redeploy_edition() {  # <edition us|china> <out_file> <url_seg>
  local ed="$1" out="$2" seg="$3"
  local archive="$RUN_DIR/${seg}_redeploy-archive.html"

  if [ ! -f "$out" ]; then
    echo "[$ed] SKIP — $out does not exist"; return 1
  fi

  # Re-validate the existing artifact; never deploy a brief that fails the gate.
  local verdict
  verdict=$(python3 "$REPO/scripts/validate_brief.py" "$out" --edition "$ed" 2>&1)
  if ! printf '%s' "$verdict" | grep -q "VERDICT : PASS"; then
    echo "[$ed] SKIP — validation did NOT pass for $out:"
    printf '%s\n' "$verdict" | grep -E 'ERROR|VERDICT'
    return 1
  fi
  echo "[$ed] validation PASS — deploying $out"

  # Archive copy gets a canonical pointing at its own dated URL (matches synth).
  /usr/bin/sed "s|<link rel=\"canonical\" href=\"https://briefer.news/${seg}/\">|<link rel=\"canonical\" href=\"https://briefer.news/${seg}/archive/${TODAY}.html\">|" "$out" > "$archive"

  # Stage 5 — local nginx volume (same volume + layout the synth writes).
  "$DOCKER" run --rm \
    -v "$RUN_DIR":/src:ro \
    -v briefernewsapp_site_output:/dst \
    alpine sh -c "
      mkdir -p /dst/${seg} /dst/${seg}/archive
      cp '/src/$(basename "$out")' /dst/${seg}/index.html
      cp '/src/$(basename "$archive")' /dst/${seg}/archive/${TODAY}.html
    " && echo "[$ed] nginx volume updated"

  # Stage 6 — S3 + CloudFront, byte-identical args to the synth.
  if aws_ready; then
    deploy_artifact "$out" "${seg}/index.html" \
      "text/html; charset=utf-8" "no-store, no-cache" \
      "[$ed] S3: ${seg}/index.html uploaded" \
      "[$ed] S3: ${seg}/index.html upload FAILED"
    deploy_artifact "$archive" "${seg}/archive/${TODAY}.html" \
      "text/html; charset=utf-8" "public, max-age=31536000, immutable" \
      "[$ed] S3: ${seg}/archive uploaded" \
      "[$ed] S3: ${seg}/archive upload FAILED"
    invalidate_paths \
      "[$ed] CloudFront: invalidation created" \
      "[$ed] CloudFront: invalidation FAILED" \
      -- "/${seg}/index.html" "/${seg}/archive/${TODAY}.html"
  else
    echo "[$ed] Stage 6 skipped — AWS CLI unavailable/unauthenticated"
  fi
}

target="${1:-both}"
case "$target" in
  us)    redeploy_edition us    "$RUN_DIR/today.html"       usa   ;;
  china) redeploy_edition china "$RUN_DIR/china_today.html" china ;;
  both)
    redeploy_edition us    "$RUN_DIR/today.html"       usa
    redeploy_edition china "$RUN_DIR/china_today.html" china
    ;;
  *) echo "usage: $0 [us|china|both]"; exit 2 ;;
esac
