#!/bin/bash
# briefer.news — synth A/B SHADOW-TEST harness.
#
# Preview what an EDITED synth prompt WOULD produce, WITHOUT deploying. Use this
# before any risky synthesize.sh / synthesize_china.sh prompt change: it runs the
# synth in shadow mode (BRIEFER_SHADOW=1), so the script renders to
# .run/shadow_<edition>.html, SKIPS the nginx-volume deploy + archive write, and
# only ECHOES the S3 / CloudFront commands instead of running them (per
# scripts/lib/deploy.sh). It then validates the candidate and prints a
# side-by-side structural diff vs the CURRENT LIVE brief.
#
#   *** THIS HARNESS NEVER DEPLOYS. ***
#   No S3 upload, no CloudFront invalidation, no nginx-volume write, and the real
#   working files (.run/today.html, .run/china_today.html) are left untouched —
#   the candidate goes to .run/shadow_<edition>.html.
#
# Usage:
#   scripts/synth_shadow.sh [us|china|both]    (default: both)
#
# WARNING: each edition runs a REAL synth, which calls Claude (real cost). This
# harness is for deliberate A/B previews of a prompt change, not routine use.

set -uo pipefail

REPO=/Users/maxgoshay/code/briefernewsapp
PY=/usr/bin/python3
RUN_DIR="$REPO/.run"

EDITIONS_ARG="${1:-both}"

case "$EDITIONS_ARG" in
  us)    EDITIONS="us" ;;
  china) EDITIONS="china" ;;
  both)  EDITIONS="us china" ;;
  *)
    echo "usage: synth_shadow.sh [us|china|both]   (default both)"
    exit 2
    ;;
esac

echo "═══════════════════════════════════════════════════════════════"
echo "SYNTH SHADOW-TEST — A/B preview, NO DEPLOY"
echo "  editions : $EDITIONS"
echo "  candidate renders to .run/shadow_<edition>.html (working files untouched)"
echo "  S3 / CloudFront / nginx volume are all SKIPPED"
echo "═══════════════════════════════════════════════════════════════"

for ED in $EDITIONS; do
  if [ "$ED" = "us" ]; then
    SYNTH_SCRIPT="$REPO/scripts/synthesize.sh"
    SHADOW_FILE="$RUN_DIR/shadow_us.html"
    VALIDATE_ED="us"
    LIVE_URL="https://briefer.news/usa/"
  else
    SYNTH_SCRIPT="$REPO/scripts/synthesize_china.sh"
    SHADOW_FILE="$RUN_DIR/shadow_china.html"
    VALIDATE_ED="china"
    LIVE_URL="https://briefer.news/china/"
  fi

  echo ""
  echo "───────────────────────────────────────────────────────────────"
  echo "[$ED] running shadow synth (BRIEFER_SHADOW=1) — this calls Claude"
  echo "───────────────────────────────────────────────────────────────"

  # Shadow synth: renders to $SHADOW_FILE, deploys nothing. The synth scripts
  # log to their own logs/ file and exec >> redirect there, so we don't see
  # their stage chatter here — that's fine; the verdict + diff below are the
  # operator-facing summary. We export BRIEFER_SHADOW for THIS edition only and
  # unset it after, so the env never leaks to a later edition's environment.
  export BRIEFER_SHADOW=1
  bash "$SYNTH_SCRIPT"
  SYNTH_RC=$?
  unset BRIEFER_SHADOW

  if [ ! -s "$SHADOW_FILE" ]; then
    echo "[$ED] ERROR: shadow synth produced no $SHADOW_FILE (synth rc=$SYNTH_RC)."
    echo "[$ED] Check the synth log (logs/synthesize*-$(date +%Y%m%d).log). Skipping diff."
    continue
  fi
  echo "[$ED] shadow brief rendered: $SHADOW_FILE ($(wc -c < "$SHADOW_FILE") bytes)"

  echo ""
  echo "[$ED] === validate_brief on the CANDIDATE (shadow) ==="
  # --no-proof so the candidate validation does not overwrite the live brief's
  # .run/brief_proof_<edition>.txt that the operator may be eyeballing.
  "$PY" "$REPO/scripts/validate_brief.py" "$SHADOW_FILE" --edition "$VALIDATE_ED" --no-proof
  CAND_VERDICT_RC=$?

  echo ""
  echo "[$ED] === A/B STRUCTURAL DIFF: candidate (shadow) vs current (live) ==="
  CAND_RC="$CAND_VERDICT_RC" SHADOW_FILE="$SHADOW_FILE" LIVE_URL="$LIVE_URL" \
  "$PY" - <<'PYDIFF'
import os, sys
sys.path.insert(0, "/Users/maxgoshay/code/briefernewsapp/scripts")
from brief_parser import parse_file, parse_url

shadow_file = os.environ["SHADOW_FILE"]
live_url = os.environ["LIVE_URL"]
cand_rc = os.environ.get("CAND_RC", "?")

cand = parse_file(shadow_file)
try:
    live = parse_url(live_url)
except Exception as e:
    live = None
    live_err = str(e)

def words(s):
    return len((s or "").split())

def visible_ledes(d):
    # The 5 visible event ledes (tier 'visible'), in order.
    return [e.get("lead", "") for e in d.get("events", []) if e.get("tier") == "visible"]

def fmt(label, cand_val, live_val):
    flag = "" if str(cand_val) == str(live_val) else "  <-- differs"
    print("  %-22s candidate=%-28s current=%-28s%s" % (
        label, str(cand_val), str(live_val), flag))

print("  %-22s %-30s %-30s" % ("field", "CANDIDATE (shadow)", "CURRENT (live)"))
print("  " + "-" * 84)

if live is None:
    print("  could not fetch live brief from %s: %s" % (live_url, live_err))
    print("  showing CANDIDATE values only:")
    print("    headline       : %s  (%d words)" % (cand["headline"], cand["headline_words"]))
    print("    visible events : %d" % cand["events_visible_count"])
    print("    more events    : %d" % cand["events_more_count"])
    print("    voices         : %d" % len(cand["voices"]))
    print("    sources        : %d" % len(cand["sources"]))
    cv = "PASS" if cand_rc == "0" else ("FAIL" if cand_rc != "?" else "?")
    print("    validate       : %s (rc=%s)" % (cv, cand_rc))
    sys.exit(0)

fmt("headline words", cand["headline_words"], live["headline_words"])
print("    candidate headline : %s" % cand["headline"])
print("    current   headline : %s" % live["headline"])
fmt("visible events", cand["events_visible_count"], live["events_visible_count"])
fmt("more events", cand["events_more_count"], live["events_more_count"])
fmt("voices", len(cand["voices"]), len(live["voices"]))
fmt("sources", len(cand["sources"]), len(live["sources"]))
fmt("sections", ", ".join(cand["section_labels"]) or "-",
    ", ".join(live["section_labels"]) or "-")

print("")
print("  5 visible event ledes (candidate vs current):")
c_led = visible_ledes(cand)
l_led = visible_ledes(live)
for i in range(max(len(c_led), len(l_led), 5)):
    if i >= 5 and i >= len(c_led) and i >= len(l_led):
        break
    c = c_led[i] if i < len(c_led) else "(none)"
    l = l_led[i] if i < len(l_led) else "(none)"
    same = "" if c == l else "  <-- differs"
    print("   %d. CAND: %s" % (i + 1, c))
    print("      LIVE: %s%s" % (l, same))

print("")
# Validate verdict: candidate from this run's rc, live is informational only.
cv = "PASS" if cand_rc == "0" else ("FAIL" if cand_rc != "?" else "?")
print("  validate verdict   candidate=%s (rc=%s)   current=LIVE (already deployed)" % (cv, cand_rc))
PYDIFF

  echo ""
  echo "[$ED] shadow A/B complete — NOTHING WAS DEPLOYED."
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Shadow-test done. No S3 upload, no CloudFront invalidation, no nginx"
echo "write occurred. Live briefs are unchanged. To promote a candidate, run"
echo "the normal 'make synth' / 'make synth-china' (which DO deploy)."
echo "═══════════════════════════════════════════════════════════════"
