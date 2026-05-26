#!/usr/bin/env python3
"""
bluesky_post.py — Post to Bluesky via the AT Protocol.

Importable from the drafter; also a CLI for manual posts.

Auth: Bluesky "app password" (NOT your account password). Generate at
https://bsky.app/settings/app-passwords — gives you a one-off password
specific to API access that you can revoke without touching your main
login. Store in .env:

    BLUESKY_HANDLE=briefernews.bsky.social
    BLUESKY_APP_PASSWORD=abcd-efgh-ijkl-mnop

The createSession call costs nothing; tokens last ~2 hours. We re-auth
every call (simpler than cache management for once-daily posting).

CLI:
    python3 scripts/bluesky_post.py "post text" \
        --url https://briefer.news/usa/ \
        --title "U.S. Brief — 2026-05-26" \
        --description "Today's top story..."

    python3 scripts/bluesky_post.py --check    # verify creds work
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
LOGS = REPO / "logs"
LOGS.mkdir(exist_ok=True)

BSKY_PDS = "https://bsky.social"


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


def _post_json(url: str, body: dict, headers: dict | None = None) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Bluesky API {url} → {e.code}: {err_body[:400]}")


def create_session(handle: str, app_password: str) -> dict:
    """Returns {accessJwt, refreshJwt, did, handle, ...}."""
    return _post_json(
        f"{BSKY_PDS}/xrpc/com.atproto.server.createSession",
        {"identifier": handle, "password": app_password},
    )


def post(text: str,
         url: str | None = None,
         title: str | None = None,
         description: str | None = None,
         handle: str | None = None,
         app_password: str | None = None) -> dict:
    """Post to Bluesky. Returns {uri, cid} from the create-record response.

    If url is given, attaches an "external" embed (link card with title +
    description) so the post renders as a clickable card.
    """
    env = load_env()
    handle = handle or env.get("BLUESKY_HANDLE")
    app_password = app_password or env.get("BLUESKY_APP_PASSWORD")
    if not handle or not app_password:
        raise RuntimeError(
            "Bluesky creds missing — set BLUESKY_HANDLE and "
            "BLUESKY_APP_PASSWORD in .env (app password from "
            "bsky.app/settings/app-passwords)"
        )

    if len(text) > 300:
        raise ValueError(f"Bluesky post too long: {len(text)} chars (max 300)")

    sess = create_session(handle, app_password)
    did = sess["did"]
    jwt = sess["accessJwt"]

    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": dt.datetime.utcnow().isoformat() + "Z",
    }

    if url:
        record["embed"] = {
            "$type": "app.bsky.embed.external",
            "external": {
                "uri": url,
                "title": (title or "")[:300],
                "description": (description or "")[:1000],
            },
        }

    payload = {
        "repo": did,
        "collection": "app.bsky.feed.post",
        "record": record,
    }
    return _post_json(
        f"{BSKY_PDS}/xrpc/com.atproto.repo.createRecord",
        payload, headers={"Authorization": f"Bearer {jwt}"},
    )


def check_creds() -> dict:
    """Verify creds work — returns session info if successful."""
    env = load_env()
    handle = env.get("BLUESKY_HANDLE", "")
    app_password = env.get("BLUESKY_APP_PASSWORD", "")
    if not handle or not app_password:
        return {"ok": False, "reason": "BLUESKY_HANDLE or BLUESKY_APP_PASSWORD not set in .env"}
    try:
        sess = create_session(handle, app_password)
        return {"ok": True, "did": sess["did"], "handle": sess.get("handle", handle)}
    except Exception as e:
        return {"ok": False, "reason": str(e)[:300]}


def log_post(channel: str, text: str, url: str | None, result: dict) -> None:
    """Append a record to logs/posts-YYYY-MM-DD.jsonl."""
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
    ap.add_argument("text", nargs="?", help="Post text (≤300 chars)")
    ap.add_argument("--url", help="Optional URL for the embed card")
    ap.add_argument("--title", help="Embed card title")
    ap.add_argument("--description", help="Embed card description")
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
        result = post(args.text, url=args.url, title=args.title, description=args.description)
        log_post("bluesky", args.text, args.url, result)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
