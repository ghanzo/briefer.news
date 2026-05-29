#!/bin/bash
# apply_cloudfront_404.sh — flip the CloudFront error responses from the
# SEO-harmful soft-404 (403/404 -> 200 /index.html, which made every missing
# URL masquerade as a real page) to a real 404 (403/404 -> 404 /404.html).
#
# This is the one piece of edge config that lived only in the CloudFront console;
# this script records + applies it. It is IDEMPOTENT (safe to re-run — it fetches
# the current ETag each time) and SAFE (it refuses to apply unless /404.html
# already serves 200, so errors can never point at a missing page).
#
#   bash scripts/apply_cloudfront_404.sh           # apply the fix
#   bash scripts/apply_cloudfront_404.sh --check    # show current state only
#   bash scripts/apply_cloudfront_404.sh --revert   # restore the old 200 /index.html
#
# Requires the default aws profile (deployment account 462170975634).

set -uo pipefail

AWS=/Users/maxgoshay/.local/bin/aws
DIST=EMV1VIFYTSI3U
REGION=us-east-1
SITE=https://briefer.news

MODE=apply
case "${1:-}" in
  --check)  MODE=check ;;
  --revert) MODE=revert ;;
  "")       MODE=apply ;;
  *)        echo "usage: $0 [--check|--revert]"; exit 2 ;;
esac

TMP=$(mktemp -t cf_dist.XXXXXX); NEW="$TMP.new"; RESP="$TMP.resp"
trap 'rm -f "$TMP" "$NEW" "$RESP"' EXIT

echo "Fetching distribution config ($DIST)…"
if ! "$AWS" cloudfront get-distribution-config --id "$DIST" --region "$REGION" > "$TMP" 2>"$RESP"; then
  echo "ERROR: get-distribution-config failed:"; cat "$RESP"; exit 1
fi
ETAG=$(python3 -c "import json;print(json.load(open('$TMP'))['ETag'])")
echo "  ETag: $ETAG"
echo "  current error responses:"
python3 -c "
import json
for it in json.load(open('$TMP'))['DistributionConfig']['CustomErrorResponses']['Items']:
    print('    %s -> %s  %s' % (it['ErrorCode'], it['ResponseCode'], it['ResponsePagePath']))
"
[ "$MODE" = "check" ] && exit 0

if [ "$MODE" = "apply" ]; then
  code=$(/usr/bin/curl -s -o /dev/null -w '%{http_code}' "$SITE/404.html")
  if [ "$code" != "200" ]; then
    echo "ERROR: $SITE/404.html returns $code (need 200). Upload 404.html first. Aborting."; exit 1
  fi
  echo "  /404.html serves 200 ✓"
  RC=404; PATHV=/404.html; TTL=10
else
  echo "  --revert: restoring 200 /index.html"
  RC=200; PATHV=/index.html; TTL=0
fi

python3 -c "
import json
d=json.load(open('$TMP')); cfg=d['DistributionConfig']
for it in cfg['CustomErrorResponses']['Items']:
    it['ResponseCode']='$RC'; it['ResponsePagePath']='$PATHV'; it['ErrorCachingMinTTL']=$TTL
json.dump(cfg, open('$NEW','w'))
"

echo "Applying update…"
if ! "$AWS" cloudfront update-distribution --id "$DIST" --region "$REGION" \
     --distribution-config "file://$NEW" --if-match "$ETAG" > "$RESP" 2>&1; then
  echo "ERROR: update-distribution failed:"; cat "$RESP"; exit 1
fi
python3 -c "
import json
d=json.load(open('$RESP'))
print('  -> new ETag:', d['ETag'], '| Status:', d['Distribution']['Status'])
"
echo "Deployment takes a few minutes (InProgress -> Deployed)."
echo "Verify:  curl -sI $SITE/this-page-does-not-exist   # expect 404"
echo "         curl -sI $SITE/usa/                        # expect 200"
