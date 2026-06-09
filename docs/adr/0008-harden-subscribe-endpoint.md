# 0008. Harden the /subscribe endpoint against bot signups

- **Status:** Accepted
- **Date:** 2026-06-08
- **Commit(s):** the change to `scripts/email_api_server.py`

## Context
The signup "funnel" looked broken — ~3 confirmed of ~47 signups. Investigation
showed the signups were **not real people**: ~45 signups in 2 days against only ~21
real human page loads all week (Cloudflare RUM, flat, no spike), every one tagged
"signup via API," with no external broadcast (no Hacker News post, no referrer
surge — only X/`t.co`, 2 loads). The `/subscribe` endpoint (behind Cloudflare
Tunnel at `api.briefer.news`) had **no abuse protection** — it checked only that the
email contained "@", and every hit fired a real SES confirmation send. Bots POSTing
directly created junk `pending` rows + bounces (SES-reputation risk) and an
email-bomb vector against arbitrary third parties.

## Decision
Add layered, dependency-free guards to `do_POST /subscribe`:
- **Honeypot** hidden form fields — silent accept + drop if filled.
- **Require browser context** — a bare API POST with no `Origin`/`Referer` gets 403.
  Real browser form submissions always carry one; the bots carry neither.
- **Strict email regex** + a junk-domain blocklist (`BLOCKED_DOMAINS`).
- **Rate limits** — per real client IP (`CF-Connecting-IP`) + a global hourly
  backstop (real volume is ~1/day).

## Consequences
- The bots' current pattern is blocked before any DB write or SES send. Verified
  live: bare POST → 403, honeypot/blocked-domain → silent 200, bad email → 400, no
  rows created by tests.
- Resolves the open finding in ADR-0007.
- **Follow-ups:** (1) add a hidden honeypot field to the signup form on the site to
  fully arm the honeypot; (2) enable Cloudflare Bot Fight Mode / a WAF rate-limit
  rule to block at the edge before traffic reaches the mini; (3) purge the existing
  ~39 junk `pending` + 4 `bounced` rows so the subscriber count reflects reality.
