#!/usr/bin/env python3
"""
x_post.py — Post to X (Twitter) via the v2 API.

Used by the drafter to auto-publish a daily tweet (same pattern as
bluesky_post.py). Tweepy handles the OAuth 1.0a signing.

Auth: 5 keys in .env. Get them from developer.x.com → your app → Keys
and Tokens. The X_ACCESS_TOKEN + X_ACCESS_TOKEN_SECRET must be generated
with read+write permission on the app (User authentication settings).

    X_BEARER_TOKEN        — for app-only reads (validation, etc.)
    X_API_KEY             — consumer key (OAuth 1.0a)
    X_API_SECRET          — consumer secret
    X_ACCESS_TOKEN        — user access token (read+write scope)
    X_ACCESS_TOKEN_SECRET — user access token secret

CLI:
    python3 scripts/x_post.py --check                       # verify auth
    python3 scripts/x_post.py "post text https://briefer.news/usa/"
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
LOGS = REPO / "logs"
LOGS.mkdir(exist_ok=True)


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    f = REPO / ".env"
    if not f.exists():
        return env
    for line in f.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        env.setdefault(k.strip(), v)
    return env


def _client():
    """Tweepy v2 client configured with both bearer + OAuth 1.0a user creds."""
    import tweepy
    env = load_env()
    missing = [k for k in
               ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET")
               if not env.get(k)]
    if missing:
        raise RuntimeError(f"Missing X creds in .env: {missing}")
    return tweepy.Client(
        bearer_token=env.get("X_BEARER_TOKEN") or None,
        consumer_key=env["X_API_KEY"],
        consumer_secret=env["X_API_SECRET"],
        access_token=env["X_ACCESS_TOKEN"],
        access_token_secret=env["X_ACCESS_TOKEN_SECRET"],
    )


def check_creds() -> dict:
    """Verify auth + show which user we're posting as."""
    try:
        client = _client()
        me = client.get_me(user_auth=True)
        if not me.data:
            return {"ok": False, "reason": "get_me returned no data"}
        return {
            "ok": True,
            "username": me.data.username,
            "name": me.data.name,
            "id": str(me.data.id),
        }
    except Exception as e:
        return {"ok": False, "reason": str(e)[:300]}


def post(text: str, url: str | None = None) -> dict:
    """Post a tweet. If url is given, it's appended to the text (with a
    space separator) so X auto-renders the link card.

    Returns {tweet_id, url}. Raises on failure."""
    if url and url not in text:
        # X counts a URL as 23 chars regardless of length (t.co shortening)
        text = f"{text}\n{url}"

    # X enforces 280-character limit (count includes t.co-shortened URLs as 23
    # chars each). Keep client-side check loose; X's response will tell us if
    # we're over.
    if len(text) > 4000:
        raise ValueError(f"text too long for client-side cap: {len(text)} chars")

    client = _client()
    resp = client.create_tweet(text=text, user_auth=True)
    if not resp.data:
        raise RuntimeError(f"create_tweet returned no data: {resp}")

    tweet_id = resp.data["id"]

    # Log the per-post cost (MARKETING.md mandate). Pass resp so any usage /
    # rate-limit headers get captured; falls back to the ~$0.20 estimate.
    # Best-effort: a cost-logging failure must never lose the published tweet.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from x_cost_log import append_cost
        append_cost("post", units=1, note=f"tweet {tweet_id}", response=resp)
    except Exception as e:
        sys.stderr.write(f"x_cost_log append_cost failed (non-fatal): {e}\n")
    me = check_creds()
    username = me.get("username", "user")
    return {
        "tweet_id": str(tweet_id),
        "url": f"https://x.com/{username}/status/{tweet_id}",
    }


def log_post(channel: str, text: str, url: str | None, result: dict) -> None:
    log_path = LOGS / f"posts-{dt.date.today().isoformat()}.jsonl"
    with log_path.open("a") as f:
        f.write(json.dumps({
            "channel": channel,
            "text": text,
            "url": url,
            "result": result,
            "timestamp": dt.datetime.now().isoformat(),
        }) + "\n")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?", help="Tweet text (≤280 chars including URL)")
    ap.add_argument("--url", help="Optional URL appended to the text")
    ap.add_argument("--check", action="store_true", help="Verify creds without posting")
    args = ap.parse_args(argv)

    if args.check:
        result = check_creds()
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1

    if not args.text:
        print("ERROR: text required (or use --check)", file=sys.stderr)
        return 2

    try:
        result = post(args.text, url=args.url)
        log_post("x", args.text, args.url, result)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
