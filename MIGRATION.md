# MIGRATION.md — Setting up briefer.news on the M4 Mac mini

> **Status: Deployment complete + restructured multi-edition (2026-05-12).**
> This runbook served its purpose. The system shipped on 2026-05-08 (Path B /
> autonomous synthesis, ahead of the originally-planned Path A manual brief
> schedule). Public domain `https://briefer.news` went live on 2026-05-10.
> Multi-edition restructure (selector at `/`, US at `/usa/`, China at `/china/`,
> autonomous China synth at 07:30 PDT) shipped 2026-05-12.
>
> Kept here as historical reference for the steps that worked. See the two
> postmortem sections at the bottom of this file for what we learned doing it.
> For day-to-day operations, see `CLAUDE.md`.

---

## Why the mini specifically

Akamai bot detection on DoD `.mil` subdomains (war.gov, centcom.mil,
navy.mil, jcs.mil, af.mil) blocks cloud datacenter IPs. We need a
**residential IP** — the mini's home-ISP connection is what makes the
free curl_cffi bypass actually work. Verified working from this
residential IP on 2026-05-07.

If you ever move the deploy off-mini to AWS/GCP/etc., expect the
Akamai bypass to fail and need a paid residential proxy ($50-100/mo).

---

## Prerequisites the user must do once (interactively)

These can't be automated — they require credentials, OAuth flows, etc.

### 1. Install software

```bash
# Homebrew (if not present)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Tools
brew install --cask docker          # Docker Desktop
brew install python@3.13            # System Python
brew install awscli                 # AWS CLI
brew install gh                     # GitHub CLI (optional but useful)

# Claude Code
# Install per https://claude.ai/code instructions
```

### 2. Authenticate Claude Code interactively

Open Terminal, run `claude`, sign in with your Anthropic account.
Once authenticated, the OAuth token lives in `~/.claude/` and can be
used by cron jobs via headless `claude -p "..."` invocations.

This is the one step that absolutely must be done by a human at the mini.

### 3. Configure AWS CLI

```bash
aws configure
# Paste Access Key ID, Secret, region (us-east-1), output format (json)
```

The IAM user already exists in the user's AWS account (`SamadhiMaximus`)
with sufficient permissions per work done on Windows 2026-05-07.

### 4. Set up power management

The mini needs to be awake at 04:00 daily. Either:

```bash
# Schedule wake at 03:55 every day
sudo pmset repeat wakeorpoweron MTWRFSU 03:55:00
```

Or just leave it always-on (M4 mini idles at ~3W).

---

## Project setup (can be scripted)

### 5. Clone the repo

```bash
mkdir -p ~/code
cd ~/code
git clone https://github.com/ghanzo/briefer.news.git briefernewsapp
cd briefernewsapp
```

### 6. Create the .env file

The .env file is NOT in the repo (deliberately). Create it from the example:

```bash
cp .env.example .env
```

Edit `.env` to fill in real values:

```bash
# Postgres (local)
POSTGRES_DB=briefer
POSTGRES_USER=briefer
POSTGRES_PASSWORD=<generate a strong password>
DATABASE_URL=postgresql://briefer:<password>@postgres:5432/briefer

# AI providers (optional fallback for when Claude Code on cron fails)
ANTHROPIC_API_KEY=sk-ant-...        # console.anthropic.com → API keys
GROQ_API_KEY=gsk_...                # console.groq.com → free signup, free tier
GEMINI_API_KEY=                     # optional
XAI_API_KEY=                        # optional

# AWS (for publishing)
AWS_ACCESS_KEY_ID=...               # if not using `aws configure`
AWS_SECRET_ACCESS_KEY=...
CLOUDFRONT_DISTRIBUTION_ID=         # populate after step 11
```

### 7. Bring up the Docker stack

```bash
docker compose up -d postgres
docker compose build pipeline       # builds with curl_cffi
```

Verify:

```bash
docker compose ps
# Should show briefer_postgres up
```

### 8. First scrape (validate end-to-end)

```bash
# Standard sources — ~10 min
docker compose run --rm pipeline python main.py --scrape-only

# Akamai-protected sources — ~30-60 min
docker compose run --rm pipeline python main.py --akamai-only
```

Verify articles in DB:

```bash
docker exec briefer_postgres psql -U briefer -d briefer -c \
  "SELECT s.name, COUNT(*) FROM articles a JOIN sources s ON a.source_id = s.id GROUP BY s.name ORDER BY COUNT(*) DESC LIMIT 20;"
```

If you see ~30+ source rows with article counts, the pipeline is healthy.

If war.gov / centcom.mil / etc. return 0 articles or fail with timeouts,
the Akamai bypass isn't working from this IP. Check:
- Is the mini on the residential ISP, not a VPN/cellular hotspot?
- Did `curl_cffi` install correctly in the Docker image?
- Try `docker compose run --rm pipeline python -c "from curl_cffi import requests; r = requests.get('https://www.war.gov/', impersonate='chrome120'); print(r.status_code, len(r.text))"` — should return 200 with substantial bytes.

---

## Stage 2/3 wiring (if scope allows)

Stage 2 (article summarization) and Stage 3 (brief synthesis) aren't
yet wired. Two options:

### Option A: Path A from PLAN_AUTOMATION.md (lighter)

Skip Stage 2/3 for now. Daily scrape produces articles in DB; brief
synthesis stays manual. Live deploy on Monday is "scrape works, brief
gets written by hand." Gets you to a live URL fastest.

### Option B: Path B (full autopilot)

Wire Stage 2/3 to use Claude Code in headless mode. Approximate flow:

```python
# pseudo-code, lives in pipeline/processor/synthesize.py
import subprocess
result = subprocess.run([
    "claude", "-p",
    f"@/app/BRIEF_STYLE.md @/app/lens.md\n\nGiven these articles:\n{articles_json}\n\nProduce a daily brief in May-6 cadence.",
    "--output-format", "json",
    "--max-turns", "10"
], capture_output=True, text=True)
brief_json = json.loads(result.stdout)
```

The Claude Code OAuth from step 2 is used implicitly. If Claude Code
fails (auth expired, usage cap), fall back to direct Anthropic API
using `ANTHROPIC_API_KEY` from .env.

**Recommendation: Path A for Monday, Path B as a follow-up week 2.**
Manually-synthesized briefs are good (we have May 6 + May 7 in
`research/brief_*.md` as examples). Auto-synthesis quality is the
unknown that risks shipping a bad brief Monday.

---

## AWS hosting (S3 + CloudFront + ACM + Route 53)

### 9. Create S3 bucket for the static site

```bash
aws s3api create-bucket \
  --bucket briefer-news-site \
  --region us-east-1
```

### 10. Request an ACM certificate

```bash
aws acm request-certificate \
  --domain-name briefer.news \
  --subject-alternative-names www.briefer.news \
  --validation-method DNS \
  --region us-east-1
```

ACM will return a certificate ARN. Note it down. The validation requires
adding a CNAME to Route 53 — the AWS console makes this one-click.

### 11. Create CloudFront distribution

This step is easier in the AWS console (Origin: the S3 bucket; Default
root object: `index.html`; Custom domain: `briefer.news`; SSL cert: the
ACM ARN from step 10). Note the distribution ID — put it in `.env` as
`CLOUDFRONT_DISTRIBUTION_ID`.

### 12. Update Route 53

In Route 53, add an A-record alias pointing `briefer.news` at the
CloudFront distribution.

DNS will already exist from prior cleanup (just NS + SOA in the zone
after we cleared dead aliases on 2026-05-07).

### 13. First publish

```bash
# From the mini, after the brief is generated locally
aws s3 sync ~/code/briefernewsapp/output/ s3://briefer-news-site/ --delete
aws cloudfront create-invalidation \
  --distribution-id $CLOUDFRONT_DISTRIBUTION_ID \
  --paths "/*"
```

Wait 10-30 minutes for DNS propagation + CloudFront edge cache fill.
Then `briefer.news` should serve your brief.

For Monday's first publish, you can manually copy
`research/prototype_2026-05-06.html` to `output/index.html` and push
that, then iterate from there.

---

## Cron / LaunchAgent

### 14. Daily run script

Create `~/code/briefernewsapp/scripts/daily.sh`:

```bash
#!/bin/bash
set -e
cd ~/code/briefernewsapp

LOG=logs/daily-$(date +%Y%m%d).log
exec >> "$LOG" 2>&1

echo "=== Daily run starting at $(date) ==="

docker compose up -d postgres
docker compose run --rm pipeline python main.py --scrape-only
docker compose run --rm pipeline python main.py --akamai-only

# Stage 2/3 — fill in once Path B is wired
# docker compose run --rm pipeline python main.py --process-only

# Build static site
# docker compose run --rm pipeline python main.py --build-only

# Publish to AWS
aws s3 sync output/ s3://briefer-news-site/ --delete
aws cloudfront create-invalidation \
  --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
  --paths "/*"

echo "=== Daily run completed at $(date) ==="
```

Make executable: `chmod +x scripts/daily.sh`.

### 15. LaunchAgent (preferred over cron on macOS)

Create `~/Library/LaunchAgents/news.briefer.daily.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>news.briefer.daily</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/<your-username>/code/briefernewsapp/scripts/daily.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>4</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/<your-username>/code/briefernewsapp/logs/launchd.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/<your-username>/code/briefernewsapp/logs/launchd.err</string>
</dict>
</plist>
```

Load it:

```bash
launchctl load ~/Library/LaunchAgents/news.briefer.daily.plist
```

Test it manually:

```bash
launchctl start news.briefer.daily
```

---

## Monitoring (optional but recommended)

If using Pushover (cheapest, simplest):

1. Install Pushover from the App Store ($5)
2. Get user key + create app token at pushover.net
3. Add to `.env`:
   ```
   PUSHOVER_USER_KEY=...
   PUSHOVER_APP_TOKEN=...
   ```
4. Add a notification call at end of `daily.sh`:

```bash
curl -s -F "token=$PUSHOVER_APP_TOKEN" \
        -F "user=$PUSHOVER_USER_KEY" \
        -F "message=Briefer daily run done — $(date)" \
        https://api.pushover.net/1/messages.json
```

---

## Verification checklist (run before going live)

- [ ] `docker compose ps` shows postgres up
- [ ] `python main.py --scrape-only` produces ≥300 articles
- [ ] `python main.py --akamai-only` produces ≥30 articles (war.gov + centcom.mil etc.)
- [ ] `aws s3 ls s3://briefer-news-site/` shows uploaded files
- [ ] `briefer.news` resolves and shows expected content (5-30min after upload)
- [ ] `launchctl list | grep briefer` shows the LaunchAgent loaded
- [ ] Manual `launchctl start news.briefer.daily` runs end-to-end without error
- [ ] Pushover notification arrives on phone (if monitoring enabled)

---

## What can go wrong on first cron fire

1. **Mini was asleep at 04:00** — check `pmset` schedule, verify mini woke
2. **Docker daemon not running** — `open -a Docker` to start; LaunchAgent should
   wait, but on first boot Docker may need 30s to come up
3. **Postgres password mismatch** — `.env` and `docker-compose.yml` must agree
4. **Akamai blocked us** — check `logs/daily-YYYYMMDD.log`. If 0 articles from
   any .mil source, IP got flagged. Wait 12-24h, retry.
5. **AWS sync failed** — check IAM permissions, bucket name, region
6. **Brief renders broken** — only relevant once Stage 2/3 wired. Until then,
   the static prototype publishes fine.

---

## Where to ask for help

If you're a fresh Claude session on the mini and stuck:

- Read `CLAUDE.md` first (orientation)
- Read `PLAN_AUTOMATION.md` for the why
- Read `BRIEF_STYLE.md` before generating any brief content
- Check `research/dod_bypass_findings_2026-05-07.md` for Akamai specifics
- Check `research/source_gap_analysis_2026-05-07.md` for source rationale
- Check git log for context on recent decisions

The user's name is **Max Goshay**. Project lives at
`github.com/ghanzo/briefer.news`. Domain is `briefer.news` (already in
the user's AWS via Route 53).

---

## Deployment Postmortem (2026-05-10)

What actually happened over the May 7-10 deployment window. Captured for
future-you and for any future Claude session that needs to know what to
expect on a similar deploy.

### What went smoothly

- **Compatibility**: M4 Mac mini, macOS 26, 16GB RAM, Docker Desktop arm64 all
  worked first try. `pipeline` image built cleanly (~2.96GB with playwright
  chromium); `postgres:16-alpine` migrated the schema on first boot. No surgery
  needed to anything in the existing `pipeline/` codebase.
- **Akamai bypass on residential IP**: validated within minutes against war.gov,
  then rolled to all 6 Akamai-protected sources. The earlier MIGRATION.md
  warning about residential-IP requirement was accurate; this is the single
  most important architectural constraint.
- **LaunchAgents**: both `news.briefer.daily` (04:00) and
  `news.briefer.synthesize` (07:00) fired exactly on time on first autonomous
  run. macOS launchd is reliable for this; no need for a fancier scheduler.
- **Two-stage Claude synthesis (picker + synthesizer)**: the SQL pre-filter ÷
  Claude picker ÷ Claude synthesizer architecture worked end-to-end on the
  first autonomous fire. The world-context layer (Stage 0 via `claude -p`
  + WebSearch) added meaningful framing on day-2.
- **AWS infrastructure cost stayed near zero**: Route 53 + CloudFront + S3
  combined < $1/mo at our traffic. Free tier covers everything else.

### What surprised us

1. **The pipeline service vs. LaunchAgent collision.** `docker-compose.yml`
   originally had `pipeline: restart: unless-stopped` plus `nginx: depends_on:
   - pipeline`, which auto-started the pipeline service when nginx came up.
   That ran the in-container APScheduler, which fired its own daily scrape at
   `SCHEDULE_TIME=06:00 UTC`, conflicting with the LaunchAgent. **Fix**: moved
   pipeline to `profiles: [manual]`, dropped its restart policy, removed
   nginx's `depends_on`. The pipeline image is still there for
   `docker compose run --rm pipeline …` invocations from `daily.sh`.

2. **AWS account split.** Domain was registered in account `026090521469` (root
   email max.goshay@gmail.com); deployment infrastructure built in account
   `462170975634` (root email ghanzo@gmail.com). Took a couple of hours of
   nameserver / Route 53 / IAM debugging to discover this. Now resolved by
   pointing the registrar's nameservers at the deployment account's hosted
   zone (`Z07630701MT6TMX2WHCGE`). Both accounts stay; the registrar account
   only holds the domain registration.

3. **Amplify-managed CloudFront distributions hold CNAMEs across regions.**
   This was the biggest gotcha. `CNAMEAlreadyExists` errors blocked
   `associate-alias` for two days. The conflict was an Amplify app
   `d3gh6znsloy9bt` in **us-east-2** (Ohio) — we'd been working in us-east-1
   the whole time and `cloudfront list-conflicting-aliases` masks the source
   account ID, so we couldn't locate it ourselves.

   **What worked**: opened an AWS Support case (Business+ $29/mo plan was
   needed to file a Technical case; Basic only allows Account/Billing). The
   CloudFront team triaged, identified that the source distro was Amplify-
   managed, opened a related case to the Amplify team. Kajal (Amplify) used
   internal tooling to locate the Amplify app and gave us the exact
   `delete-domain-association` command. Once we ran it (in us-east-2),
   `list-conflicting-aliases` cleared *immediately* and `associate-alias`
   succeeded. Total elapsed time across two cases: about 30 hours
   wall-clock; most of that was waiting between agent responses.

   **Generalizable lesson**: when AWS surfaces a `CNAMEAlreadyExists` and
   you can't find the offending distribution in your own account, ALWAYS
   open Support before assuming it's another tenant. AWS support is willing
   to release CNAMEs from your own historical (or differently-regioned)
   resources.

4. **AWS Support tier names changed.** What used to be "Developer Support"
   ($29/mo) is now branded "Business+". The next tier up is "Enterprise"
   ($5,000/mo). Don't be alarmed if a Cost Explorer line shows "Business
   Support+" — it's the $29 plan, not the $100 one.

5. **macOS sudo flow with Claude Code.** Several steps in the original
   runbook required `sudo` (AWS CLI installer, `pmset` wake schedule). The
   user couldn't recall their password mid-session. Workarounds: extracted
   AWS CLI v2 PKG payload to `~/aws-cli/` and symlinked into `~/.local/bin`
   (no sudo needed); skipped pmset entirely (M4 mini idles at ~3W, just
   left it always-on).

6. **Headless `claude -p` permissions.** Default headless mode does NOT have
   permission to use WebSearch, WebFetch, or write files. Had to add
   `--allowedTools WebSearch WebFetch Read Write Edit` and
   `--permission-mode acceptEdits` explicitly. Documented in
   `scripts/world_context.sh` and `scripts/synthesize.sh`.

7. **Headless `claude -p` couldn't read `/tmp/`**. The sandbox is restricted
   to the working directory. Moved all intermediates to `${REPO}/.run/`
   (added to `.gitignore`).

8. **YAML regex escape gotcha (China sources).** YAML double-quoted strings
   evaluate `\\d` as `\d`, but my initial source patterns were off-by-one
   on the date width (`\d{6}` instead of `\d{5}` for `tYYYYMMDD_NNN.shtml`).
   Easy fix once detected; flagging because Chinese gov URL patterns vary
   per site and the test cycle is "edit yaml → run scrape → no matches → debug."

### What we'd skip / change next time

- **Don't bother with the `pmset` wake schedule.** Always-on M4 mini is fine
  at ~3W idle. Saved one sudo prompt.
- **Set up AWS profiles upfront**: when we switched between deployment account
  (`maxbriefer`) and registrar account (`max`), the CLI default got
  overwritten more than once. Best practice: always use named profiles
  (`--profile registrar`, `--profile deployment`) instead of swapping
  default credentials.
- **Open the AWS Support case earlier.** We tried `associate-alias`
  workarounds for nearly a day before opening a case. Should have opened it
  at the first `CNAMEAlreadyExists` error — Edgar (CloudFront) responded
  within minutes.

---

## Multi-edition Postmortem (2026-05-12)

What happened during the multi-edition restructure. The China brief had been
running manually for a few days; this session built the autonomous side and
restructured the site so it could host more than one edition.

### What went smoothly

- **China synth shipped end-to-end in one session.** SQL pre-filter + Claude
  picker + Claude synthesizer + S3/CloudFront publish, all in one script
  (`scripts/synthesize_china.sh`). Three iterations against the same corpus
  (v1 → v2 → v3) refined the prompts in tight feedback loops.
- **Multi-edition restructure took ~45 min.** Moving the US brief from `/` to
  `/usa/`, adding a selector at `/`, adding nav strips to both country pages
  — clean migration via copying S3 objects, injecting nav HTML into existing
  briefs, deploying selector last. No data loss; old `/archive/` paths still
  serve as backstop.
- **CloudFront Function for trailing-slash rewrites.** Wrote the JS, created
  the function, published to LIVE stage, attached to the default cache
  behavior, waited for distribution-deployed. Total ~5 min including AWS
  wait time. Standard fix for S3+CloudFront sites; should have done it on
  initial deploy.
- **LaunchAgent for China synth wired without surprises.** Mirrored the
  existing `news.briefer.synthesize.plist` structure, loaded via `launchctl
  load`, verified active via `launchctl list`. New time 07:30 PDT chosen to
  offset 30 min from US synth so they don't compete for Claude API quota.

### What surprised us

1. **SQL pre-filter priority ordering shut MFA out entirely.** The original
   `ORDER BY priority ASC, pub_date DESC ... LIMIT 200` filled all 200 slots
   with priority-1 through priority-3 sources, never reaching MFA at
   priority 5. Without MFA in the candidate pool, the picker had no
   spokesperson transcripts to draw from. Fix: split the SQL into two CTEs —
   `internal_pool` (175 slots, priority-ordered, MFA excluded) and
   `voices_pool` (25 reserved MFA slots, sub-quota 15 Daily Press
   Conference + 10 Foreign Minister Activities). Without the sub-quota,
   whichever MFA source was scraped more recently filled all 25 slots and
   shut out the other.

2. **Picker read "MFA shouldn't dominate" as "skip MFA entirely."** Even
   after the SQL fix put MFA into the pool, the picker's prompt phrasing
   produced zero MFA picks in two consecutive runs. Replaced with hard-rule
   language: "MUST include AT LEAST 6 MFA Daily Press Conference items in
   your 50 picks. This is a hard requirement, not a preference." That
   worked — v3 picker landed exactly 7 MFA picks.

3. **`briefer.news/china/` (with trailing slash) returned a CloudFront 403
   that fell back to the root US brief.** CloudFront's DefaultRootObject
   only applies to `/`, not to `/<dir>/`. S3 has no directory-index support
   for OAC-fronted buckets. The fallback behavior masquerades as "the URL
   works" — content-length 31845 (US brief) instead of 29989 (China brief).
   Caught by checking `x-cache: Error from cloudfront` header. Fix: a
   CloudFront Function that rewrites `/<dir>/` → `/<dir>/index.html` at the
   viewer-request edge.

4. **CloudFront Functions need both create AND publish steps.** Creating
   the function puts it in DEVELOPMENT stage; you have to explicitly
   `publish-function` to move it to LIVE before attaching it to a
   distribution. The CLI returns a clean ARN from `publish-function` that's
   what goes into the distribution config.

5. **Same-prefix S3 paths in two AWS accounts caused no issues.** The
   migration moved `s3://briefer-news-site/index.html` content to
   `s3://briefer-news-site/usa/index.html` and replaced the root with the
   selector. Both old `/archive/` (now legacy) and new `/usa/archive/`
   serve correctly without redirect rules. Kept the old archives as a
   backstop for any external links.

6. **Nav strip injection via Python was simpler than editing prototype +
   re-synth.** v3 China brief was already deployed; the US brief was last
   synthesized 12 hours earlier. Rather than wait for the next 07:00 synth
   to pick up nav-strip changes, wrote a small Python script that injects
   the nav HTML + CSS into existing rendered HTML. Idempotent (re-running
   strips and re-injects). Used in both staging (preview) and the live
   migration.

### What we'd skip / change next time

- **Add CloudFront Function at initial deploy**, not as a retrofit. Any
  S3-backed CloudFront site with subdirectories needs it.
- **Don't use absolute paths in cross-page nav** unless you're SURE the site
  will always be served from the root. The initial nav strip used `/usa/`
  and `/china/` which broke when staged at `/preview/`. Relative paths
  (`../usa/`, `../china/`, `../`) work in both production and preview.
- **Sanity-check SQL pre-filter distributions before debugging synth
  output.** If voices look weak or imbalanced, the first question should be
  "what's in the candidate pool" — not "what's the picker doing." A 30-sec
  `jq` on `china_candidates_meta.json` would have caught the MFA-zero issue
  before any synth ran.
