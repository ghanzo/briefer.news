#!/usr/bin/env python3
"""
twitter_post.py — OAuth 1.0a user-context client for the X (Twitter) v2 API.

Pure stdlib — no tweepy / requests_oauthlib dependency. Reads credentials
from .env at the repo root.

Endpoints used:
  GET    /2/users/me        — verify auth + identify the account
  POST   /2/tweets          — publish a tweet
  DELETE /2/tweets/{id}     — remove a tweet (for smoke testing)

CLI:
  python3 scripts/twitter_post.py whoami
  python3 scripts/twitter_post.py post "Tweet text here"
  python3 scripts/twitter_post.py delete <tweet_id>
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
ENV_PATH = REPO / ".env"
API = "https://api.twitter.com"


def load_env() -> dict[str, str]:
    """Minimal .env parser — KEY=VALUE lines; '#' comments and blanks ignored."""
    out: dict[str, str] = {}
    if not ENV_PATH.exists():
        return out
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


def pe(s: str) -> str:
    """OAuth 1.0a percent-encoding — strict, no safe characters."""
    return urllib.parse.quote(str(s), safe="")


def oauth1_header(method: str, url: str, signing_params: dict[str, str],
                  ck: str, cs: str, tk: str, ts: str) -> str:
    """Build an OAuth 1.0a Authorization header.

    For Twitter v2 endpoints with JSON bodies, signing_params should be empty
    of body content — the body does not participate in the signature when
    Content-Type is application/json. Query-string params, if any, do.
    """
    oauth = {
        "oauth_consumer_key": ck,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": tk,
        "oauth_version": "1.0",
    }

    all_params = {**oauth, **signing_params}
    pairs = sorted((pe(k), pe(v)) for k, v in all_params.items())
    param_string = "&".join(f"{k}={v}" for k, v in pairs)
    base_string = "&".join([method.upper(), pe(url), pe(param_string)])
    signing_key = pe(cs) + "&" + pe(ts)
    sig = hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    oauth["oauth_signature"] = base64.b64encode(sig).decode()

    return "OAuth " + ", ".join(
        f'{pe(k)}="{pe(v)}"' for k, v in sorted(oauth.items())
    )


def call(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    env = load_env()
    for var in ("TWITTER_CONSUMER_KEY", "TWITTER_CONSUMER_SECRET",
                "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET"):
        if not env.get(var):
            return 0, f"missing {var} in .env"

    url = API + path
    auth = oauth1_header(
        method, url, {},
        env["TWITTER_CONSUMER_KEY"], env["TWITTER_CONSUMER_SECRET"],
        env["TWITTER_ACCESS_TOKEN"], env["TWITTER_ACCESS_TOKEN_SECRET"],
    )
    headers = {"Authorization": auth, "User-Agent": "briefer.news/1.0"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = r.read().decode()
            return r.status, (json.loads(payload) if payload else {})
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(body_text)
        except (json.JSONDecodeError, ValueError):
            return e.code, body_text
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2

    cmd = argv[1]

    if cmd == "whoami":
        status, body = call("GET", "/2/users/me")
        print(f"GET /2/users/me → HTTP {status}")
        print(json.dumps(body, indent=2) if isinstance(body, dict) else body)
        return 0 if status == 200 else 1

    if cmd == "post" and len(argv) >= 3:
        text = argv[2]
        status, body = call("POST", "/2/tweets", {"text": text})
        print(f"POST /2/tweets → HTTP {status}")
        print(json.dumps(body, indent=2) if isinstance(body, dict) else body)
        return 0 if status in (200, 201) else 1

    if cmd == "delete" and len(argv) >= 3:
        tid = argv[2]
        status, body = call("DELETE", f"/2/tweets/{tid}")
        print(f"DELETE /2/tweets/{tid} → HTTP {status}")
        print(json.dumps(body, indent=2) if isinstance(body, dict) else body)
        return 0 if status == 200 else 1

    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
