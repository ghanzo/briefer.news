# briefer.news — shared deploy helpers.
#
# Sourced by the pipeline shells (synthesize.sh, synthesize_china.sh,
# weekly.sh, daily_digests.sh). Centralizes the two AWS operations that
# were copy-pasted across all of them:
#   1. 'aws s3 cp <local> s3://<bucket>/<key>' with content-type + cache-control
#   2. 'aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths ...'
#
# SHADOW MODE: if $BRIEFER_SHADOW is non-empty, every helper ECHOES the exact
# command it WOULD run (prefixed "+ ") and SKIPS the real s3 cp / invalidation.
# This is the no-deploy mode reused by the shadow-test harness — a shadow run
# produces the brief and prints the deploy commands without touching S3 or
# CloudFront.
#
# This file sources env.sh (single source of truth for DIST_ID, S3_BUCKET,
# AWS path) so callers get the constants for free after sourcing deploy.sh.

# Resolve env.sh relative to THIS file so it works regardless of caller cwd.
_BRIEFER_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$_BRIEFER_LIB_DIR/env.sh"

# aws_ready — true iff the aws CLI is present and authenticated.
# Mirrors the historical '[ -x "$AWS" ] && "$AWS" sts get-caller-identity' gate.
# In shadow mode we always return true so the echo path runs without needing
# real credentials.
aws_ready() {
  if [ -n "$BRIEFER_SHADOW" ]; then
    return 0
  fi
  [ -x "$AWS" ] && "$AWS" sts get-caller-identity >/dev/null 2>&1
}

# deploy_artifact <local_file> <s3_key> <content_type> <cache_control> [ok_msg] [fail_msg]
#
# Runs the EXACT 'aws s3 cp' the scripts ran by hand:
#   "$AWS" s3 cp <local_file> s3://<S3_BUCKET>/<s3_key> \
#     --content-type <content_type> --cache-control <cache_control>
# then echoes ok_msg on success / fail_msg on failure (both optional).
#
# <s3_key> is the path WITHIN the bucket, e.g. "usa/index.html". Do NOT include
# the bucket or the s3:// scheme — this helper prepends s3://$S3_BUCKET/.
#
# Shadow mode: prints the command and returns 0 without uploading.
deploy_artifact() {
  local local_file="$1"
  local s3_key="$2"
  local content_type="$3"
  local cache_control="$4"
  local ok_msg="$5"
  local fail_msg="$6"
  local dest="s3://${S3_BUCKET}/${s3_key}"

  if [ -n "$BRIEFER_SHADOW" ]; then
    echo "+ $AWS s3 cp $local_file $dest --content-type $content_type --cache-control $cache_control"
    return 0
  fi

  if "$AWS" s3 cp "$local_file" "$dest" \
      --content-type "$content_type" \
      --cache-control "$cache_control"; then
    [ -n "$ok_msg" ] && echo "$ok_msg"
    return 0
  else
    [ -n "$fail_msg" ] && echo "$fail_msg"
    return 1
  fi
}

# deploy_artifact_quiet <local_file> <s3_key> <content_type> <cache_control> [ok_msg] [fail_msg]
#
# Same as deploy_artifact but redirects the aws stdout to /dev/null (the
# archive-index / sitemap / feeds deploys did '... >/dev/null && echo ...').
# Preserves that exact form: the '>/dev/null' is applied to the s3 cp, ok_msg
# prints on success, and the OPTIONAL fail_msg prints on failure (the sitemap
# upload had a '|| echo ... FAILED'; the archive-index / feeds uploads did
# not — pass fail_msg only where the original had one).
deploy_artifact_quiet() {
  local local_file="$1"
  local s3_key="$2"
  local content_type="$3"
  local cache_control="$4"
  local ok_msg="$5"
  local fail_msg="$6"
  local dest="s3://${S3_BUCKET}/${s3_key}"

  if [ -n "$BRIEFER_SHADOW" ]; then
    echo "+ $AWS s3 cp $local_file $dest --content-type $content_type --cache-control $cache_control >/dev/null"
    [ -n "$ok_msg" ] && echo "$ok_msg"
    return 0
  fi

  if "$AWS" s3 cp "$local_file" "$dest" \
      --content-type "$content_type" \
      --cache-control "$cache_control" >/dev/null; then
    [ -n "$ok_msg" ] && echo "$ok_msg"
    return 0
  else
    [ -n "$fail_msg" ] && echo "$fail_msg"
    return 1
  fi
}

# invalidate_paths [ok_msg] [fail_msg] -- <path> [<path> ...]
#
# Runs the EXACT 'aws cloudfront create-invalidation' the scripts ran:
#   "$AWS" cloudfront create-invalidation \
#     --distribution-id <DIST_ID> --paths <path>... \
#     --query 'Invalidation.Id' --output text
# then echoes ok_msg / fail_msg (optional).
#
# Usage: invalidate_paths "CloudFront: invalidation created" \
#                         "CloudFront: invalidation FAILED (non-fatal)" \
#                         -- "/usa/index.html" "/usa/archive/${TODAY}.html"
# The "--" separates the two message args from the variadic path list.
#
# Shadow mode: prints the command and returns 0 without invalidating.
invalidate_paths() {
  local ok_msg="$1"
  local fail_msg="$2"
  shift 2
  if [ "$1" = "--" ]; then
    shift
  fi
  local paths=("$@")

  if [ -n "$BRIEFER_SHADOW" ]; then
    echo "+ $AWS cloudfront create-invalidation --distribution-id $DIST_ID --paths ${paths[*]} --query Invalidation.Id --output text"
    return 0
  fi

  if "$AWS" cloudfront create-invalidation \
      --distribution-id "$DIST_ID" \
      --paths "${paths[@]}" \
      --query 'Invalidation.Id' --output text; then
    [ -n "$ok_msg" ] && echo "$ok_msg"
    return 0
  else
    [ -n "$fail_msg" ] && echo "$fail_msg"
    return 1
  fi
}
