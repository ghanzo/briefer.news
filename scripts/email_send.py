#!/usr/bin/env python3
"""
email_send.py — Daily send pipeline for briefer.news.

Reads today's US + China content from the live site, renders the
per-subscriber email (with their unique unsubscribe URL), sends via
AWS SES, logs each send result to logs/email-sends-YYYY-MM-DD.jsonl.

Safety gates:
  1. EMAIL_ENABLED=true must be set in .env (default false).
  2. EMAIL_DAILY_CAP not exceeded (default 5000).
  3. SES production-access enabled OR --test-mode + recipient is a
     verified SES identity.
  4. If unsubscribe endpoint not yet live (Step 6 pending), production
     sends refuse with a loud error.

Usage:
  python3 scripts/email_send.py --test         # smoke test — sends to
                                                # verified SES identities only
  python3 scripts/email_send.py --dry-run      # render but don't send
  python3 scripts/email_send.py                # production send to all
                                                # confirmed subscribers

Environment (in .env at repo root):
  EMAIL_ENABLED=false                          # master kill switch
  EMAIL_DAILY_CAP=5000                         # hard ceiling per day
  EMAIL_FROM_ADDRESS=news@briefer.news         # SES From
  EMAIL_FROM_NAME="Briefer News"               # Display name
  EMAIL_UNSUBSCRIBE_BASE=https://briefer.news/unsubscribe?t=
                                                # appended with token per subscriber
  EMAIL_UNSUBSCRIBE_LIVE=false                 # set true once Step 6 ships
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import urllib.request
import html as html_lib
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
LOGS = REPO / "logs"
LOGS.mkdir(exist_ok=True)

AWS = "/Users/maxgoshay/.local/bin/aws"
SES_REGION = "us-east-1"
TODAY = dt.date.today()

# Share the exact stamp rule + parser with the rest of the system so the
# freshness gate can never drift from healthcheck.py / brief_parser.py.
sys.path.insert(0, str(REPO / "scripts"))
from healthcheck import expected_stamp  # noqa: E402  same "MAY 28, 2026" format
from brief_parser import parse_brief  # noqa: E402  single source of truth
from notify import notify  # noqa: E402  off-box operational alert (SES + log)


# ── Helpers ─────────────────────────────────────────────────────────────────

def load_env() -> dict[str, str]:
    env = {}
    f = REPO / ".env"
    if not f.exists():
        return env
    for line in f.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        # Strip surrounding quotes if present
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        env[k.strip()] = v
    return env


def fetch_brief(edition: str) -> dict:
    """Pull headline + top 3 event leads (the <b>Lead.</b> prefix of each <li>
    in the visible items list — NOT the items-more collapsed block)."""
    url = f"https://briefer.news/{edition}/"
    html = urllib.request.urlopen(url, timeout=20).read().decode("utf-8", errors="replace")
    h = re.search(r'<h2 class="headline">([\s\S]+?)</h2>', html)
    ul = re.search(r'<ul class="items"(?! items-more)[^>]*>([\s\S]+?)</ul>', html)
    events = []
    if ul:
        items = re.findall(r'<li[^>]*>([\s\S]+?)</li>', ul.group(1))
        for item in items[:3]:
            lead = re.search(r'<b>([\s\S]+?)</b>', item)
            if lead:
                text = re.sub(r"<[^>]+>", "", lead.group(1)).strip().rstrip(".")
                events.append(html_lib.unescape(text))
    return {
        "headline": html_lib.unescape(re.sub(r"<[^>]+>", "", h.group(1)).strip()) if h else "(headline missing)",
        "events": events,
        "url": url,
        # Keep the raw HTML so the freshness gate reuses this single fetch
        # (via brief_parser.parse_brief) instead of curling the brief again.
        "html": html,
    }


def freshness_ok(edition: str, html: str, today: dt.date) -> tuple[bool, str]:
    """Gate the subscriber send on brief freshness, using the shared parser.

    Passes only when, for the fetched HTML:
      (a) the stamp date == today, computed via healthcheck.expected_stamp so
          the two scripts share one rule and cannot drift; and
      (b) the brief is non-empty: events_visible_count >= 1 AND a headline is
          present (parse_brief returns "" for a missing headline).

    Returns (ok, detail). The detail string describes the failure for the alert/log.
    """
    parsed = parse_brief(html or "")
    stamp = parsed.get("date") or ""
    expected = expected_stamp(today)
    visible = parsed.get("events_visible_count", 0)
    headline = (parsed.get("headline") or "").strip()

    if stamp != expected:
        return False, f"{edition}: stamp='{stamp}' expected='{expected}'"
    if visible < 1:
        return False, f"{edition}: stamp OK ({stamp}) but 0 visible events (empty brief)"
    if not headline:
        return False, f"{edition}: stamp OK ({stamp}) but headline is missing (empty brief)"
    return True, f"{edition}: fresh (stamp={stamp}, visible={visible}, headline present)"


def today_send_count() -> int:
    """How many sends already logged today."""
    log = LOGS / f"email-sends-{TODAY.isoformat()}.jsonl"
    if not log.exists():
        return 0
    return sum(1 for line in log.read_text().splitlines()
               if line.strip() and json.loads(line).get("status") == "sent")


def log_send(record: dict) -> None:
    log = LOGS / f"email-sends-{TODAY.isoformat()}.jsonl"
    record["timestamp"] = dt.datetime.now().isoformat()
    with log.open("a") as f:
        f.write(json.dumps(record) + "\n")


def first_clause(headline: str) -> str:
    for sep in [";", ":", " — ", " as ", " while "]:
        if sep in headline:
            return headline.split(sep, 1)[0].strip()
    return headline[:60].rsplit(" ", 1)[0] + "…" if len(headline) > 60 else headline


def get_confirmed_subscribers() -> list[dict]:
    """Pull confirmed subscribers from postgres via the existing helper."""
    sys.path.insert(0, str(REPO / "scripts"))
    from email_subscribers import list_confirmed
    return list_confirmed()


def get_verified_ses_identities() -> set[str]:
    """For test mode — which addresses can we send to in sandbox."""
    out = subprocess.check_output(
        [AWS, "sesv2", "list-email-identities", "--region", SES_REGION,
         "--query", "EmailIdentities[?VerifiedForSendingStatus==`true`].IdentityName",
         "--output", "json"],
        text=True, timeout=15,
    )
    return set(json.loads(out))


def ses_production_enabled() -> bool:
    out = subprocess.check_output(
        [AWS, "sesv2", "get-account", "--region", SES_REGION,
         "--query", "ProductionAccessEnabled", "--output", "text"],
        text=True, timeout=15,
    ).strip()
    return out.lower() == "true"


def send_one(env: dict, recipient: str, html_body: str, text_body: str, subject: str) -> dict:
    """Call SES SendEmail. Returns {status, message_id|error}."""
    from_addr = env.get("EMAIL_FROM_ADDRESS", "news@briefer.news")
    from_name = env.get("EMAIL_FROM_NAME", "Briefer News")
    source = f'"{from_name}" <{from_addr}>'

    # Use sesv2 send-email with Simple message format
    payload = {
        "FromEmailAddress": source,
        "Destination": {"ToAddresses": [recipient]},
        "Content": {
            "Simple": {
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                },
            }
        },
    }
    payload_path = Path("/tmp/ses_payload.json")
    payload_path.write_text(json.dumps(payload))
    try:
        out = subprocess.check_output(
            [AWS, "sesv2", "send-email", "--region", SES_REGION,
             "--cli-input-json", f"file://{payload_path}",
             "--output", "json"],
            text=True, timeout=30, stderr=subprocess.STDOUT,
        )
        return {"status": "sent", "message_id": json.loads(out).get("MessageId", "?")}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "error": e.output[-400:] if e.output else str(e)}
    finally:
        if payload_path.exists():
            payload_path.unlink()


# ── Main ────────────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true",
                    help="Test mode — send only to SES-verified identities, allow broken unsubscribe URL")
    ap.add_argument("--dry-run", action="store_true",
                    help="Render but don't send; print what would happen")
    args = ap.parse_args(argv)

    env = load_env()
    enabled = env.get("EMAIL_ENABLED", "false").lower() == "true"
    cap = int(env.get("EMAIL_DAILY_CAP", "5000"))
    unsub_base = env.get("EMAIL_UNSUBSCRIBE_BASE", "https://briefer.news/unsubscribe?t=")
    unsub_live = env.get("EMAIL_UNSUBSCRIBE_LIVE", "false").lower() == "true"

    print(f"=== email_send · {TODAY.isoformat()} ===")
    print(f"  EMAIL_ENABLED:           {enabled}")
    print(f"  EMAIL_DAILY_CAP:         {cap} (used today: {today_send_count()})")
    print(f"  EMAIL_UNSUBSCRIBE_LIVE:  {unsub_live}")
    print(f"  test mode:               {args.test}")
    print(f"  dry-run:                 {args.dry_run}")

    # Safety gates
    if not enabled and not args.test and not args.dry_run:
        print("\nABORT: EMAIL_ENABLED=false in .env. Set true to send for real.")
        return 1

    in_production = ses_production_enabled()
    print(f"  SES production access:   {in_production}")

    if not in_production and not args.test and not args.dry_run:
        print("\nABORT: SES still in sandbox. Use --test mode or wait for production access.")
        return 1

    if in_production and not unsub_live and not args.test and not args.dry_run:
        print("\nABORT: Production sends require working unsubscribe endpoint (Step 6).")
        print("Either set EMAIL_UNSUBSCRIBE_LIVE=true once wired, or use --test mode.")
        return 1

    # Today's content
    us = fetch_brief("usa")
    china = fetch_brief("china")
    today_iso = TODAY.isoformat()
    subject = f"Briefer News — {first_clause(us['headline'])}"

    # ── Freshness gate ───────────────────────────────────────────────────────
    # IN ADDITION to the EMAIL_ENABLED / EMAIL_DAILY_CAP / unsubscribe gates
    # above. The synth often finishes hours after the 08:30 send, so a stale or
    # empty brief must never go to subscribers. Gated per edition (both ship in
    # one email — if EITHER is stale/empty we skip the whole send).
    stale = []
    for edition, brief in (("USA", us), ("China", china)):
        ok, detail = freshness_ok(edition, brief.get("html", ""), TODAY)
        print(f"  freshness {detail}")
        if not ok:
            stale.append(detail)

    if stale:
        expected = expected_stamp(TODAY)
        for detail in stale:
            edition = detail.split(":", 1)[0]
            msg = (f"{edition} brief is stale/empty ({detail}; expected={expected}) "
                   f"— skipped the 08:30 send")
            print(f"\nABORT (freshness): {msg}")
            notify("crit", msg, dry_run=args.dry_run)
        # Do NOT send to subscribers; exit non-zero so launchd records failure.
        return 1

    # Render template (import lazily so syntax check is faster)
    sys.path.insert(0, str(REPO / "scripts"))
    from email_template import render_email, render_text_fallback

    # Subscriber list
    if args.test:
        verified = get_verified_ses_identities()
        recipients = [{"email": e, "unsubscribe_token": "TEST_TOKEN_NOT_LIVE"} for e in sorted(verified)]
        print(f"\nTEST MODE — recipients = verified SES identities ({len(recipients)}): {[r['email'] for r in recipients]}")
    else:
        recipients = get_confirmed_subscribers()
        print(f"\nConfirmed subscribers: {len(recipients)}")

    if not recipients:
        print("No recipients. Nothing to send.")
        return 0

    if today_send_count() + len(recipients) > cap:
        print(f"\nABORT: would exceed daily cap ({cap}). Already sent {today_send_count()}; about to send {len(recipients)}.")
        return 1

    # Send loop
    sent = 0
    failed = 0
    for sub in recipients:
        unsub_url = f"{unsub_base}{sub['unsubscribe_token']}"
        html = render_email(us, china, today_iso, unsub_url)
        text = render_text_fallback(us, china, today_iso, unsub_url)
        if args.dry_run:
            print(f"  DRY-RUN would send to {sub['email']}")
            continue
        result = send_one(env, sub["email"], html, text, subject)
        log_send({"recipient": sub["email"], "subject": subject, **result})
        if result["status"] == "sent":
            sent += 1
            print(f"  ✓ {sub['email']:40s} {result['message_id']}")
        else:
            failed += 1
            print(f"  ✗ {sub['email']:40s} ERROR: {result.get('error', '?')[:120]}")

    print(f"\n=== sent: {sent} · failed: {failed} ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
