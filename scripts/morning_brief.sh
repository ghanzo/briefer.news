#!/bin/bash
# morning_brief.sh — Daily site-state report. Fires from the
# news.briefer.morningbrief LaunchAgent at 08:30 PT each morning.
#
# Stage 1: gather pipeline status + traffic + search + live-brief checks
# Stage 2: Claude reads the data, writes a morning-brief markdown
# Stage 3: save to logs/morning-brief-YYYY-MM-DD.md
#
# Output is plain markdown — open it in any editor or render to HTML
# if you ever want it in a browser.

set -euo pipefail

REPO="/Users/maxgoshay/code/briefernewsapp"
cd "$REPO"

LOG_DIR="$REPO/logs"
RUN_DIR="$REPO/.run"
mkdir -p "$LOG_DIR" "$RUN_DIR"

TODAY=$(/bin/date +%Y-%m-%d)
YESTERDAY=$(/bin/date -v-1d +%Y-%m-%d)
DATA="$RUN_DIR/morning_brief_data.json"
PROMPT="$RUN_DIR/morning_brief_prompt.txt"
OUT="$LOG_DIR/morning-brief-${TODAY}.md"

CLAUDE=/Users/maxgoshay/.local/bin/claude

echo "═══════════════════════════════════════════════════════════════"
echo "Morning brief — $TODAY"
echo "═══════════════════════════════════════════════════════════════"

# ── Stage 1: gather data ────────────────────────────────────────────────
echo "--- Stage 1: gathering data ---"
/usr/bin/python3 "$REPO/scripts/morning_brief_gather.py"

if [ ! -s "$DATA" ]; then
  echo "ERROR: gather script produced no data — bailing"
  exit 1
fi

# ── Stage 2: Claude synthesizes the morning brief ───────────────────────
echo "--- Stage 2: Claude synthesizes the morning brief ---"

cat > "$PROMPT" <<EOF
You are writing the daily morning brief for the OPERATOR of briefer.news.
This is NOT the public news brief — this is an internal status report I (the
operator) read every morning to know how the site performed yesterday + last
night's pipeline run, plus what to think about today.

Read this data file (the only input you need): @${DATA}

It contains:
  - generated_at, today, yesterday timestamps
  - pipeline section: status of today's scrape / US synth / China synth /
    digests / weekly / healthcheck (each with an "ok | errors | incomplete"
    status, error lines if any, and the last 15 log lines for context)
  - live_briefs: structural check of what actually rendered on /usa/ and
    /china/ — headline, dek word count, section labels present, whether
    Outside the Gate / Allied Governments / This week / more-events
    collapsible rendered, the canonical URL declared
  - traffic: yesterday's CloudFront log summary (totals, top pages, top
    referrers) — may be partial if logs are still delivering
  - search: most recent weekly Search Console snapshot (impressions,
    clicks, top queries, average position)
  - errors_today: every ERROR / FAIL / Traceback line found across all
    of today's logs

Write a morning brief in this exact structure. Use plain markdown. Keep it
~600-900 words total. Be specific, name numbers, name URLs, name what
moved. Write like a co-founder briefing me, not like a status dashboard.

# briefer.news — morning brief · ${TODAY}

## Reminders for today
ONLY include this section if data.reminders_for_today is non-empty.
If it is, render each reminder as a bullet at the TOP of the brief
(before TL;DR) so the operator can't miss it. If empty, omit the
section entirely — don't write "no reminders" or anything.

## TL;DR
ONE LINE. Status badge + the single most important thing about today.
Pick from: ✓ all green / ⚠ N issues to look at / ✗ critical issue.

## Last night's pipeline + site quality
What ran, what worked, what didn't. Lead with anomalies if any. Reference
specific log lines when something is off. If everything is clean, say so in
one sentence and move on — don't pad.

Then surface today's mechanical **site-quality score** from
data.site_quality (both US and China have a .score_pct out of 100, plus
itemized checks). Format the score line like:
  "Site quality: US 100% (8/8), China 87% (7/8) — `outside_gate_present`
  failed (expected, sources parked)."
If any non-conditional check failed, NAME IT and explain what it means.
The mechanical checks cover: dek banned-patterns (DEK.md), dek 30-55
word count, headline word count (US 12-16, China ≤12), voices /
more-events / This week structural presence, canonical URL declares the
live URL, stamp matches today. Conditional checks (allied_present for
US, outside_gate_present for China) are NOT in the score denominator
— they vary by day intentionally; just call them out separately as
present/absent.

Then editorial-level dek + headline checks (Claude's eye, not the
mechanical pattern scan):
  - Did today's US dek read factual or did it slip into editorial framing
    in ways the mechanical scan misses? (subtle interpretive verbs,
    cause-and-effect framings the regex doesn't catch).
  - Did today's China dek pass the same check?

## Yesterday's traffic
Pull the numbers from data.traffic. Lead with totals (requests / unique
visitor buckets / bytes / humans-vs-bots). Then top 3 pages. Then top
referrers (only if there are external referrers — many days will be empty
which is fine). Then anything notable (a spike, a new referrer, a 5xx
status). If traffic data is missing or "no traffic recorded," say so
plainly — it's normal for the first few days after enabling logging.

## Costs
From data.costs. Lead with the deployment account's month-to-date total
(usd) and yesterday's daily total. Then call out the 2-3 biggest line
items by service. Distinguish SITE costs (Route 53, S3, CloudFront,
Cost Explorer queries) from NON-SITE costs (AWS Business Support+,
WorkMail, anything else AWS is charging for that isn't briefer.news
infrastructure). If a non-site cost is dominant, flag it explicitly
("$N of MTD is X, which isn't site-related — consider cancelling if
unused"). Mention any offsite known costs from
data.costs.known_offsite_costs only if non-zero or operationally
relevant. Skip the section in one line if everything is trivial
("~\$N MTD, site infrastructure is ~\$N — within budget").

## Search performance (week)
From data.search. Only include if the snapshot is from this week or last
week. Lead with impressions / clicks / avg position. Flag the trend if
visible (impressions climbing, position improving).

## SERP CTR — week-over-week (per page)
From data.search_wow. Two 7-day windows compared with a 3-day gap (GSC
reports lag 2-3 days). Report MUST include:

- Site totals row: this-week impressions / clicks / CTR vs last-week's,
  with deltas. Name the percentage CTR — at our scale 0% is the relevant
  number to track.
- A per-page table for ANY URL that had ≥3 impressions in either window.
  Columns: URL · this-imp · last-imp · imp Δ · this-clicks · last-clicks ·
  this-CTR · last-CTR · CTR Δ · this-pos · pos Δ.
- ALWAYS surface /usa and /china specifically (even at low volume) since
  those are the two pages we just shortened meta descriptions on (lift
  expected 24-72h after each Googlebot re-crawl). A non-zero clicks_delta
  on either is the signal we're watching for.
- One sentence interpretation: "/china jumped from X to Y impressions
  but CTR is still 0%, position improved by N" — write so the operator
  sees the meta-description lift the moment it shows up.

If data.search_wow.status != "ok", say so in one line and continue.

## Notable signals
3-5 bullets. Only the things that ACTUALLY MATTER today — not a list of
everything. Examples that would qualify: a query showed up that suggests
intent ("us government brief"), traffic from a new geography, an error
pattern in logs, a successful first-render of a feature shipped recently.

## Today's three moves
EXACTLY THREE. One bullet each.
  1. **Build viewership** — the single concrete thing to do today (or this
     week) to bring more readers in. Could be: post on a specific subreddit,
     reach out to a specific person, write a specific tweet, etc. Be
     specific — not "post more on social media." Pick from real options
     given yesterday's traffic + search + recent activity.
  2. **Improve the site** — the single concrete UX / editorial / content
     change worth shipping next. Could be: new section, copy tweak,
     missing feature. Pick from the obvious candidates in the project's
     pending state (CHINA_ALLIED.md direct scrapers, email signup form
     deployment, a CSS issue spotted on the live page, etc.).
  3. **Improve the analytics** — the single concrete thing to do today
     to make the brief-of-the-brief tighter / more useful. Could be:
     a metric we're missing, a noise pattern we should filter, a
     data source we should add (e.g., reach Cloudflare API for richer
     data once token is available).

Write the brief now. Save it directly to ${OUT} — do NOT print to stdout.
EOF

if [ ! -x "$CLAUDE" ]; then
  echo "ERROR: claude binary not found at $CLAUDE"
  exit 1
fi

"$CLAUDE" -p "$(cat "$PROMPT")" --max-turns 30 --permission-mode acceptEdits

if [ ! -s "$OUT" ]; then
  echo "ERROR: claude did not write the brief — bailing"
  exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Morning brief produced: $(wc -c < "$OUT") bytes"
echo "Path: $OUT"
echo "═══════════════════════════════════════════════════════════════"
