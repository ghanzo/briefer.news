# X (Twitter) Posting — Implementation State

> **Status: tabled 2026-05-22.** All code, credentials, and design are
> in place. The single remaining blocker is purchasing API credits from
> X (their new pay-per-use credit model returned `HTTP 402 CreditsDepleted`
> on the first smoke-test post). Once credits are funded, this becomes a
> ~30-minute finish-and-test job.

---

## Goal

Auto-post a single short tweet from **@SamadhiMaximus** per edition,
right after each daily synth publishes. Two posts per day (US + China).
This is the primary outbound traffic channel for briefer.news.

---

## What is built

### Code
- **`scripts/twitter_post.py`** — pure-stdlib OAuth 1.0a v2 client for X.
  No `tweepy` / `requests_oauthlib` dependency. Reads credentials from
  `.env`. Three CLI commands:
  - `whoami` — `GET /2/users/me`; identifies the authenticated account.
  - `post "..."` — `POST /2/tweets`; publishes a tweet.
  - `delete <id>` — `DELETE /2/tweets/{id}`; removes a tweet.

### Credentials (in `.env`, never committed)
All eight `TWITTER_*` variables are populated and current:
```
TWITTER_HANDLE
TWITTER_CONSUMER_KEY
TWITTER_CONSUMER_SECRET
TWITTER_BEARER_TOKEN
TWITTER_ACCESS_TOKEN
TWITTER_ACCESS_TOKEN_SECRET
TWITTER_OAUTH2_CLIENT_ID         (unused; kept for future OAuth-2 flexibility)
TWITTER_OAUTH2_CLIENT_SECRET     (same)
```
`.env` is in `.gitignore`. Verified clean: no token strings appear in
any tracked file.

### Developer-portal state
- **App permissions:** Read and Write.
- **Type of App:** Web App, Automated App or Bot.
- **Callback URI:** `https://briefer.news/` (required field; unused —
  we use pre-generated OAuth 1.0a tokens, not the OAuth flow).
- **Account verified by `whoami`:** `@SamadhiMaximus`, X user id `97796721`.

---

## What is NOT yet built (pending credits)

- A production poster wrapper — call it `scripts/auto_tweet.py` — that
  fetches the latest archived brief (`/usa/archive/<today>.html` or
  `/china/archive/<today>.html`), extracts the headline + first sentence
  of the dek, and assembles the tweet text.
- Two LaunchAgents (`news.briefer.tweet.usa.plist`,
  `news.briefer.tweet.china.plist`) firing ~5 minutes after each
  synth's normal completion time:
  - US: ~07:15 PT (after the 07:00 synth)
  - China: ~07:45 PT (after the 07:30 synth)
- A live POST round-trip ever succeeding. The smoke test on 2026-05-22
  returned the credits error before posting anything.

---

## The blocker

```
POST /2/tweets → HTTP 402
{
  "type": "https://api.twitter.com/2/problems/credits",
  "title": "CreditsDepleted",
  "detail": "Your enrolled account does not have any credits to fulfill this request."
}
```

X moved to a **pay-per-use credit model**. The Free tier's initial credit
allocation is effectively zero for write endpoints; `POST /2/tweets`
requires purchased credits.

**Credentials, OAuth signing, and Read+Write permissions are all
confirmed working** — auth was verified separately via `whoami` (`HTTP
200`, account returned). The 402 is purely a quota/billing layer above
auth.

---

## To resume — checklist

1. **Purchase API credits** in the X Developer Portal → Products /
   Plans (or Usage / Billing). Even a small starter pack is enough to
   verify the round-trip.
2. **Re-run the smoke test:**
   ```bash
   cd /Users/maxgoshay/code/briefernewsapp
   python3 -c "
   import sys, json
   sys.path.insert(0, 'scripts')
   from twitter_post import call
   status, body = call('POST', '/2/tweets',
       {'text': 'briefer.news — connectivity check, deleting in a moment.'})
   print(f'POST → HTTP {status}'); print(json.dumps(body, indent=2))
   if status not in (200, 201): sys.exit(1)
   tid = body['data']['id']
   status, body = call('DELETE', f'/2/tweets/{tid}')
   print(f'DELETE → HTTP {status}'); print(json.dumps(body, indent=2))
   "
   ```
   Expect HTTP 201 from POST, HTTP 200 with `"deleted": true` from DELETE.
3. **Build the production poster** (per the design below) and the two
   LaunchAgents.
4. **First live post** with explicit user OK before automation goes
   on a schedule.

---

## Design decisions (confirmed during setup)

### Cadence
One tweet per edition, posted right after each synth finishes — never
on a separate fixed schedule. This guarantees the tweet is in sync with
what's actually on the page.

### Content shape (proposed default)
```
[headline]

[first sentence of the dek, trimmed to fit ~280 chars total]

briefer.news/usa/   (or /china/)
```
- Lead with the headline (verbatim from `<h2 class="headline">`).
- One sentence of the dek — the natural lede.
- Plain URL, no shortener (X expands them anyway, and a clean
  `briefer.news` URL is part of the brand).
- **No hashtags by default.** Iterate after the first few days based
  on what gets engagement.

### Failure handling
- If the tweet POST fails, log the error and exit non-zero — do not
  retry within the same run. The LaunchAgent fires once a day; a
  failed run silently does nothing, exactly like the synth scripts'
  failure model.
- If the brief itself is missing (synth failed earlier in the morning),
  skip the tweet entirely — never tweet a stale brief.

---

## Open considerations

### X Premium for @SamadhiMaximus's reach
Separate from the API. X Premium ($8–$22/mo depending on tier) is a
subscription on the **user's account**, not the developer account.
Benefits relevant to a news project:
- Algorithmic boost in replies / search.
- Longer tweets (4,000 characters on Premium+) — could let us post a
  fuller summary rather than just the headline + lede.
- Edit window — useful if a typo lands in an auto-post.
- The verification mark — varies in perceived value depending on
  audience but is the visible signal of paid-account status.

**Worth exploring once auto-posting is actually running.** The signal
the Premium tier should help amplify only exists once posts are
flowing.

### Fallback if API credit pricing is prohibitive
The site already publishes per-edition RSS feeds at
`briefer.news/usa/feed.xml` and `/china/feed.xml`. IFTTT, Zapier free,
and Buffer free all have RSS-to-X recipes that post on behalf of the
user (not the dev account) — these don't touch the paid X API. If
purchased credits work out to materially more than ~$0.10 per post,
the IFTTT route is the rational fallback.

---

## Credential safety — do not break

- `.env` is the **only** place TWITTER_* values live in the working
  tree. It is gitignored.
- If keys ever need to be regenerated, update `.env` in place
  (don't paste tokens into chat, commit messages, or any tracked
  file).
- The `xapi` filename was used as a one-off paste-target during
  initial setup and was deleted; do not re-create it. If a future
  paste is needed, write directly into `.env` or paste to the
  assistant in the chat.

---

## Files touched

- New: `scripts/twitter_post.py`
- New: `X_POSTING.md` (this file)
- Edited: `.env` (eight `TWITTER_*` variables added; NOT committed)
