#!/bin/bash
# drafter.sh — Daily Drafter agent.
#
# Fires from news.briefer.drafter LaunchAgent at 09:30 PT (30 min after
# the morning Researcher). Reads today's research log + today's brief
# headlines, drafts posts for every channel, and auto-posts where the
# channel is enabled and the API is wired (Bluesky today; X once tokens
# land).
#
# Manual channels (HN, Reddit, LinkedIn, Threads) get drafts written to
# logs/drafts-YYYY-MM-DD.md for the operator to copy-paste.

set -euo pipefail

REPO="/Users/maxgoshay/code/briefernewsapp"
cd "$REPO"

TODAY=$(/bin/date +%Y-%m-%d)
LOG_DIR="$REPO/logs"
RUN_DIR="$REPO/.run"
RESEARCH_DIR="$REPO/research/loop"
mkdir -p "$LOG_DIR" "$RUN_DIR"

CONTEXT="$RUN_DIR/drafter_context.md"
PROMPT="$RUN_DIR/drafter_prompt.txt"
DRAFTS_OUT="$LOG_DIR/drafts-${TODAY}.md"

CLAUDE=/Users/maxgoshay/.local/bin/claude

# Load only the env flags we care about — `source` fails on .env values
# with unquoted spaces (e.g. EMAIL_FROM_NAME=Briefer News). Grep the
# specific keys we need.
get_env() {
  local key="$1"
  local default="$2"
  if [ -f "$REPO/.env" ]; then
    local val
    val=$(/usr/bin/grep -E "^${key}=" "$REPO/.env" | /usr/bin/tail -1 | /usr/bin/sed "s/^${key}=//; s/^[\"']//; s/[\"']$//")
    if [ -n "$val" ]; then
      echo "$val"
      return
    fi
  fi
  echo "$default"
}

BLUESKY_ENABLED=$(get_env BLUESKY_ENABLED false)
X_ENABLED=$(get_env X_ENABLED false)
DRAFTER_DRY_RUN=$(get_env DRAFTER_DRY_RUN false)

echo "═══════════════════════════════════════════════════════════════"
echo "Drafter — $TODAY"
echo "  bluesky=$BLUESKY_ENABLED · x=$X_ENABLED · dry_run=$DRAFTER_DRY_RUN"
echo "═══════════════════════════════════════════════════════════════"

# ── Stage 1: gather context ─────────────────────────────────────────────
echo "--- Stage 1: gathering context ---"

{
  echo "# Drafter context — $TODAY"
  echo ""

  echo "## This morning's research log"
  echo ""
  RESEARCH_FILE="$RESEARCH_DIR/${TODAY}-morning.md"
  if [ -f "$RESEARCH_FILE" ]; then
    /bin/cat "$RESEARCH_FILE"
  else
    echo "(no morning research log — researcher may not have run yet)"
  fi
  echo ""

  echo "## Today's brief headlines + deks"
  echo ""
  for EDITION in usa china; do
    HTML="$RUN_DIR/${EDITION}_brief_today.html"
    /usr/bin/curl -s "https://briefer.news/${EDITION}/" > "$HTML" 2>/dev/null || true
    if [ -s "$HTML" ]; then
      LABEL=$([ "$EDITION" = "usa" ] && echo "U.S." || echo "China")
      /usr/bin/python3 -c "
import re
html = open('$HTML').read()
h = re.search(r'<h2 class=\"headline\">([\s\S]+?)</h2>', html)
ul = re.search(r'<ul class=\"dek-bullets\">([\s\S]+?)</ul>', html)
if ul:
    bullets = [re.sub(r'<[^>]+>','',b).strip() for b in re.findall(r'<li[^>]*>([\s\S]+?)</li>', ul.group(1))]
    dek = ' · '.join(b for b in bullets if b)
else:
    d = re.search(r'<p class=\"dek\">([\s\S]+?)</p>', html)
    dek = re.sub(r'<[^>]+>','',d.group(1)).strip() if d else '(no dek)'
print('### $LABEL edition')
print('**Headline:** ' + (re.sub(r'<[^>]+>','',h.group(1)).strip() if h else '(no headline)'))
print('')
print('**Dek:** ' + dek)
print('')
ev_idx = html.find(\"Today's events\")
events = []
if ev_idx != -1:
    ulm = re.search(r'<ul class=\"items\">([\s\S]+?)</ul>', html[ev_idx:])
    if ulm:
        for li in re.findall(r'<li[^>]*>([\s\S]+?)</li>', ulm.group(1))[:3]:
            sm = re.search(r'<summary[^>]*>([\s\S]+?)</summary>', li)
            lead = re.sub(r'<[^>]+>','', sm.group(1)).strip() if sm else ''
            rest = li.split('</summary>',1)[1] if '</summary>' in li else li
            desc = re.sub(r'<[^>]+>','', re.split(r'<sup|<span', rest)[0]).strip()
            events.append((lead + ' ' + desc).strip())
print('**Top 3 events:**')
for e in events:
    print('- ' + e)
print('')
print('**URL:** https://briefer.news/$EDITION/')
print('')
"
    fi
  done

  echo "## Channel status"
  echo ""
  echo "| Channel | Autonomous | Status |"
  echo "|---|---|---|"
  echo "| Bluesky | yes | BLUESKY_ENABLED=$BLUESKY_ENABLED |"
  echo "| X / Twitter | yes (when tokens land) | X_ENABLED=$X_ENABLED |"
  echo "| HN | NO (ToS) | always manual |"
  echo "| Reddit | NO (ToS) | always manual |"
  echo "| LinkedIn | NO | always manual |"
  echo "| Threads | NO | always manual |"

} > "$CONTEXT"

echo "Context: $(/usr/bin/wc -c < "$CONTEXT") bytes"

# ── Stage 2: Claude drafts posts for every channel ──────────────────────
echo "--- Stage 2: Claude drafts every channel ---"

/bin/cat > "$PROMPT" <<EOF
You are the Drafter agent for briefer.news.

Read the context, then write one post per channel for $TODAY. Your output
is a single markdown file at:

    $DRAFTS_OUT

The file MUST follow this structure exactly — each H2 is one channel:

# Drafts — $TODAY

## Bluesky
<post text, ≤280 chars to be safe under the 300 limit>
URL: https://briefer.news/usa/  (or /china/ — pick one based on which story is the lead)
TITLE: <link-card title, ≤120 chars>
DESCRIPTION: <link-card description, ≤200 chars>

## X / Twitter
<Write the post in this EXACT shape, keeping the opening three sentences verbatim: "I'm a builder, I've spent a few years on this. Briefer News is a government publications brief. A new kind of news. Today: EVENT1, EVENT2, EVENT3:" Replace EVENT1/2/3 with the U.S. edition's "Top 3 events" from the context, in order, each a short plain-English phrase of 4 to 10 words. Expand every acronym ("Quad" becomes "four nations"). Refer to any official who is not globally famous by country or institution. Everything before the URL must be 255 characters or fewer and end with a colon; use only 2 events if 3 will not fit. Do not use any dashes.>
URL: https://briefer.news/usa/?utm_source=x

## HN
TITLE: <Show HN / Ask HN style if applicable, else a plain descriptive title — ≤80 chars, no clickbait>
URL: <briefer.news URL most worth submitting today; archive permalink if today's brief is the strongest>

## Reddit r/geopolitics
TITLE: <≤300 chars; conform to sub conventions>
BODY: <2-4 short paragraphs framing what's in today's brief + why it matters for that sub. End with the URL. No "thanks for reading" or self-promo cringe.>

## LinkedIn
<longer-form post, 3-6 short paragraphs, professional voice, lead with the most decision-useful claim from today's brief, end with the URL. ≤1500 chars.>

## Threads
<≤500 chars; similar to Bluesky but slightly punchier per the platform's vibe>

Channel-specific tone:
- Bluesky: matter-of-fact, journalistic, no hashtags.
- X / Twitter: use the fixed events format defined in the X section above. Plain and factual, no editorializing.
- HN: descriptive, no superlatives. The HN crowd downvotes hype.
- Reddit: contextual, sub-aware. r/geopolitics readers want analysis;
  r/news wants the lede. Default to r/geopolitics; only switch if the
  Researcher recommended otherwise.
- LinkedIn: pretend you're a former diplomat or analyst posting once
  a week. Decision-useful. Skip the "I'm thrilled to share" opener.
- Threads: terse, scannable.

UNIVERSAL RULES (brand-promise constraints):
- NEVER editorialize. Let gov sources speak. No "this is alarming",
  "this is huge", "shocking", etc.
- NEVER fabricate quotes or sources. Only paraphrase what's in today's
  brief.
- Every post must cite a primary government source IF the post makes a
  claim. The site is the citation aggregator.
- Lower-case "x", "facebook", "reddit" — no platform name pomp.
- Do not use dashes of any kind: no em-dashes, no en-dashes, no hyphen
  used as punctuation. Use commas, periods, or colons instead. Write
  like a person, not an AI.

The Researcher's "Today's hooks" section is your primary guide for
angles. If it suggested specific angles, USE THEM verbatim or close to
it (the Researcher already filtered for what'd land). If it had no
specific hooks, fall back to summarizing the headline + most newsworthy
event in the dek.

Read context: @${CONTEXT}

Write the drafts file. Do NOT post anything from this prompt — posting
is done by the shell wrapper after you return.
EOF

set +e
"$CLAUDE" -p "$(/bin/cat "$PROMPT")" \
  --allowed-tools Read,Write,Bash \
  > "$RUN_DIR/drafter_stdout.log" 2> "$RUN_DIR/drafter_stderr.log"
CLAUDE_EXIT=$?
set -e

if [ $CLAUDE_EXIT -ne 0 ]; then
  echo "Claude failed (exit $CLAUDE_EXIT). See $RUN_DIR/drafter_stderr.log"
  exit $CLAUDE_EXIT
fi

if [ ! -s "$DRAFTS_OUT" ]; then
  echo "ERROR: Drafter didn't produce $DRAFTS_OUT"
  exit 1
fi

echo "✓ Drafts written: $DRAFTS_OUT ($(/usr/bin/wc -c < "$DRAFTS_OUT") bytes)"

# ── Stage 3: auto-post where enabled ────────────────────────────────────
echo "--- Stage 3: auto-posting ---"

if [ "$DRAFTER_DRY_RUN" = "true" ]; then
  echo "DRAFTER_DRY_RUN=true — skipping all posts"
  exit 0
fi

# Extract Bluesky section, post it
if [ "$BLUESKY_ENABLED" = "true" ]; then
  echo "Posting Bluesky..."
  /usr/bin/python3 <<PYEOF
import re, sys, json
from pathlib import Path
sys.path.insert(0, '$REPO/scripts')

text_block = Path('$DRAFTS_OUT').read_text()
m = re.search(r'## Bluesky\n([\s\S]+?)(?=\n## |\Z)', text_block)
if not m:
    print("WARN: no Bluesky section in drafts")
    sys.exit(0)

section = m.group(1).strip()
url_m = re.search(r'URL:\s*(\S+)', section)
title_m = re.search(r'TITLE:\s*(.+)', section)
desc_m = re.search(r'DESCRIPTION:\s*(.+)', section)

# The post text is everything before URL/TITLE/DESCRIPTION lines
text = re.split(r'\n(?:URL|TITLE|DESCRIPTION):', section)[0].strip()

print(f"  text: {text[:80]}…")
print(f"  url:  {url_m.group(1) if url_m else '(none)'}")

import bluesky_post as bsky
result = bsky.post(
    text=text,
    url=url_m.group(1) if url_m else None,
    title=title_m.group(1).strip() if title_m else None,
    description=desc_m.group(1).strip() if desc_m else None,
)
bsky.log_post('bluesky', text, url_m.group(1) if url_m else None, result)
print(f"  posted: {result.get('uri')}")

# Annotate the drafts file: mark as POSTED
drafts = Path('$DRAFTS_OUT').read_text()
drafts = drafts.replace('## Bluesky\n', f"## Bluesky [POSTED {result.get('uri')}]\n", 1)
Path('$DRAFTS_OUT').write_text(drafts)
PYEOF
else
  echo "  bluesky: disabled (set BLUESKY_ENABLED=true to enable)"
fi

# Extract X / Twitter section, post it (skip if an X post already went out today)
X_ALREADY_TODAY=$(/usr/bin/python3 -c "
import json, datetime
from pathlib import Path
f = Path('$LOG_DIR') / ('posts-' + datetime.date.today().isoformat() + '.jsonl')
n = 0
if f.exists():
    for line in f.read_text().splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get('channel') == 'x' and r.get('type') != 'engagement':
            n += 1
print(n)
" 2>/dev/null || echo 0)
if [ "$X_ENABLED" = "true" ] && [ "${X_ALREADY_TODAY:-0}" != "0" ]; then
  echo "  x: already posted today (${X_ALREADY_TODAY}); skipping to avoid a double-post."
elif [ "$X_ENABLED" = "true" ]; then
  echo "Posting X..."
  /usr/bin/python3 <<PYEOF
import re, sys
from pathlib import Path
sys.path.insert(0, '$REPO/scripts')

text_block = Path('$DRAFTS_OUT').read_text()
m = re.search(r'## X / Twitter\n([\s\S]+?)(?=\n## |\Z)', text_block)
if not m:
    print("WARN: no X / Twitter section in drafts")
    sys.exit(0)

section = m.group(1).strip()
url_m = re.search(r'URL:\s*(\S+)', section)
# The post text is everything before URL line
text = re.split(r'\nURL:', section)[0].strip()
url = url_m.group(1) if url_m else None

print(f"  text: {text[:80]}…")
print(f"  url:  {url or '(none)'}")

import x_post as x
try:
    result = x.post(text, url=url)
    x.log_post('x', text, url, result)
    print(f"  posted: {result.get('url')}")
    # Annotate the drafts file: mark as POSTED
    drafts = Path('$DRAFTS_OUT').read_text()
    drafts = drafts.replace('## X / Twitter\n', f"## X / Twitter [POSTED {result.get('url')}]\n", 1)
    Path('$DRAFTS_OUT').write_text(drafts)
except Exception as e:
    print(f"  ERROR posting to X: {e}")
PYEOF
else
  echo "  x: disabled (set X_ENABLED=true to enable)"
fi

echo "Done."
