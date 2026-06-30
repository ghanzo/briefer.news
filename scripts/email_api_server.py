#!/usr/bin/env python3
"""
email_api_server.py — Minimal HTTP server for email subscriber lifecycle.

Endpoints (all return HTML for human visitors; /subscribe also accepts
form-encoded POST from the signup form on briefer.news):

    GET  /                         — health check
    POST /subscribe                — body: email=...&edition=us|china|both
                                     creates pending subscriber, sends confirmation email
    GET  /confirm?token=...        — promotes pending → confirmed
    GET  /unsubscribe?t=...        — flips confirmed → unsubscribed

Designed to run behind Cloudflare Tunnel (api.briefer.news → this server)
or any reverse proxy. Listens on 0.0.0.0:8765 by default; override with
EMAIL_API_PORT env var.

Local test:
    python3 scripts/email_api_server.py
    # Then in another shell:
    curl -X POST localhost:8765/subscribe -d "email=test@example.com&edition=both"
    curl 'localhost:8765/confirm?token=<token_from_response>'

Production deployment (Cloudflare Tunnel from the briefer.news Cloudflare
account → api.briefer.news → http://mini:8765). See EMAIL.md.
"""

from __future__ import annotations

import base64
import datetime as dt
import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import time
import urllib.parse
from collections import defaultdict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
LOGS = REPO / "logs"
LOGS.mkdir(exist_ok=True)

PORT = int(os.environ.get("EMAIL_API_PORT", "8765"))
AWS = "/Users/maxgoshay/.local/bin/aws"

# Lazy-import the subscriber helpers (path setup)
sys.path.insert(0, str(REPO / "scripts"))
import email_subscribers as subs  # type: ignore


# ── Env loading (for SES config) ────────────────────────────────────────────

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
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        env[k.strip()] = v
    return env

ENV = load_env()
UNSUB_BASE = ENV.get("EMAIL_UNSUBSCRIBE_BASE", "https://api.briefer.news/unsubscribe?t=")
CONFIRM_BASE = ENV.get("EMAIL_CONFIRM_BASE", "https://api.briefer.news/confirm?token=")
FROM_ADDR = ENV.get("EMAIL_FROM_ADDRESS", "news@briefer.news")
FROM_NAME = ENV.get("EMAIL_FROM_NAME", "Briefer News")


# ── Abuse guards for /subscribe (added 2026-06-08 after bot signups) ─────────
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
# Known disposable / junk domains seen abusing the open endpoint. Extend as needed.
BLOCKED_DOMAINS = {
    "immenseignite.info",
}
# Hidden form fields a real user never fills; a bot that fills one is dropped.
HONEYPOT_FIELDS = ("website", "company", "url", "phone")
RATE_PER_IP_HR = 3      # max accepted signups per client IP per rolling hour
RATE_GLOBAL_HR = 15     # global backstop per hour (real volume is ~1/day)
_ip_hits: dict[str, list[float]] = defaultdict(list)
_global_hits: list[float] = []


def _client_ip(handler) -> str:
    """Real client IP behind Cloudflare Tunnel (CF-Connecting-IP), then XFF."""
    return (handler.headers.get("CF-Connecting-IP")
            or handler.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or handler.client_address[0])


def _rate_check(ip: str) -> str | None:
    """Return None if allowed, else 'ip' / 'global'."""
    global _global_hits
    cutoff = time.time() - 3600
    _ip_hits[ip] = [t for t in _ip_hits[ip] if t > cutoff]
    _global_hits = [t for t in _global_hits if t > cutoff]
    if len(_ip_hits[ip]) >= RATE_PER_IP_HR:
        return "ip"
    if len(_global_hits) >= RATE_GLOBAL_HR:
        return "global"
    return None


def _rate_record(ip: str) -> None:
    now = time.time()
    _ip_hits[ip].append(now)
    _global_hits.append(now)


# ── Page rendering helpers (inline HTML, branded to match the site) ─────────

PAGE_CSS = """
  body { margin:0; padding:0; background:#FFFFFF; color:#1A1614;
         font-family: Georgia, 'Times New Roman', serif; line-height:1.55; }
  .wrap { max-width:600px; margin:48px auto; padding:0 24px; }
  .masthead { background:#14110F; color:#F2EBD9; text-align:center;
              padding:28px 24px 22px; border-radius:3px; margin-bottom:32px; }
  .masthead h1 { font-size:30px; font-weight:600; margin:0; line-height:1; }
  .masthead p  { font-style:italic; font-size:12px; color:#C9BFA7;
                 letter-spacing:0.02em; margin:10px 0 0; }
  h2 { font-size:24px; font-weight:500; margin:0 0 12px; }
  p  { font-size:17px; color:#3D332C; margin:0 0 16px; }
  a  { color:#7A4F2E; }
  .nav { text-align:center; margin-top:32px; padding-top:18px;
         border-top:1px solid #3D332C;
         font-family: Menlo, monospace; font-size:11px; letter-spacing:0.12em;
         color:#6B5D52; }
  .nav a { color:#6B5D52; text-decoration:none; margin:0 8px; }
"""

def page(title: str, body_html: str, status: int = 200) -> tuple[int, bytes]:
    html = f"""<!doctype html>
<html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="only light">
<title>{title} — Briefer News</title>
<style>{PAGE_CSS}</style>
</head><body>
<div class="wrap">
  <div class="masthead">
    <h1>Briefer News</h1>
    <p>All sourcing from government &middot; Everything cited &middot; News without opinion</p>
  </div>
  {body_html}
  <div class="nav">
    <a href="https://briefer.news/">briefer.news</a>
    <a href="https://briefer.news/usa/">U.S.</a>
    <a href="https://briefer.news/china/">China</a>
    <a href="https://briefer.news/about/">about</a>
  </div>
</div>
</body></html>"""
    return status, html.encode("utf-8")


# ── SES send for confirmation email ─────────────────────────────────────────

def send_confirmation(email: str, confirmation_token: str, unsubscribe_token: str = "") -> bool:
    confirm_url = f"{CONFIRM_BASE}{confirmation_token}"
    subject = "Confirm your Briefer News subscription"
    text = f"""Welcome to Briefer News.

Click below to confirm your subscription. This makes sure no one
signed you up without your permission.

{confirm_url}

If you didn't subscribe, ignore this email — no further messages.
"""
    html = f"""<!doctype html><html><head>
<meta charset="utf-8">
<meta name="color-scheme" content="only light">
<style>{PAGE_CSS}</style>
</head><body><div class="wrap">
<div class="masthead"><h1>Briefer News</h1>
<p>All sourcing from government &middot; Everything cited &middot; News without opinion</p></div>
<h2>Confirm your subscription</h2>
<p>Click the button below to confirm. This makes sure no one signed you up without your permission.</p>
<p style="margin:24px 0;text-align:center;">
  <a href="{confirm_url}" style="display:inline-block;padding:14px 28px;background:#14110F;color:#F2EBD9;
     text-decoration:none;border-radius:3px;font-family:Menlo,monospace;font-size:12px;
     letter-spacing:0.18em;text-transform:uppercase;font-weight:600;">Confirm subscription</a>
</p>
<p style="font-size:14px;color:#6B5D52;">If the button doesn't work, paste this URL:<br>
<a href="{confirm_url}" style="word-break:break-all;">{confirm_url}</a></p>
<p style="font-size:14px;color:#6B5D52;margin-top:32px;">If you didn't subscribe, ignore this email — no further messages.</p>
</div></body></html>"""

    # Raw MIME so the confirmation can carry a List-Unsubscribe one-click header
    # for Gmail deliverability — mirrors the newsletter send (email_send.send_one).
    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((FROM_NAME, FROM_ADDR))
    msg["To"] = email
    msg["Subject"] = subject
    if unsubscribe_token:
        unsub_url = f"{UNSUB_BASE}{unsubscribe_token}"
        msg["List-Unsubscribe"] = f"<{unsub_url}>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    payload = {
        "FromEmailAddress": f'"{FROM_NAME}" <{FROM_ADDR}>',
        "Destination": {"ToAddresses": [email]},
        "Content": {"Raw": {"Data": base64.b64encode(msg.as_bytes()).decode("ascii")}},
    }
    payload_path = Path("/tmp/ses_confirm_payload.json")
    payload_path.write_text(json.dumps(payload))
    try:
        subprocess.check_output(
            [AWS, "sesv2", "send-email", "--region", "us-east-1",
             "--cli-input-json", f"file://{payload_path}", "--output", "json"],
            text=True, timeout=30, stderr=subprocess.STDOUT,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"  SES error: {e.output[-200:]}", file=sys.stderr)
        return False
    finally:
        if payload_path.exists():
            payload_path.unlink()


# ── HTTP handler ────────────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "BrieferEmailAPI/1.0"

    def log_message(self, fmt, *args):
        """Log to date-stamped file rather than stderr."""
        log_path = LOGS / f"api-{dt.date.today().isoformat()}.log"
        with log_path.open("a") as f:
            f.write(f"[{dt.datetime.now().isoformat()}] {self.address_string()} - {fmt % args}\n")

    def _send(self, status: int, body: bytes, content_type: str = "text/html; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # Permissive CORS so the signup form on briefer.news can POST cross-origin
        self.send_header("Access-Control-Allow-Origin", "https://briefer.news")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, b"")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/health":
            self._send(*page("Health", "<h2>OK</h2><p>Briefer News email API is up.</p>"))
            return

        if path == "/confirm":
            tokens = params.get("token", [])
            if not tokens:
                self._send(*page("Missing token",
                    "<h2>Missing token</h2><p>This confirmation URL is incomplete. Check the link in your email.</p>",
                    status=400))
                return
            # Show a confirm BUTTON (which POSTs) rather than confirming on GET.
            # Corporate email-security scanners auto-fetch (GET) links, which was
            # auto-confirming subscriptions in 1-2s. Requiring a human to click a
            # button that POSTs stops those non-human confirmations.
            tok = urllib.parse.quote(tokens[0], safe="")
            self._send(*page("Confirm your subscription",
                "<h2>Confirm your subscription</h2>"
                "<p>One click to start receiving Briefer News.</p>"
                f"<form method=\"POST\" action=\"/confirm?token={tok}\" style=\"margin:24px 0;\">"
                "<button type=\"submit\" style=\"display:inline-block;padding:14px 28px;"
                "background:#14110F;color:#F2EBD9;border:0;border-radius:3px;font-family:Menlo,monospace;"
                "font-size:12px;letter-spacing:0.18em;text-transform:uppercase;font-weight:600;cursor:pointer;\">"
                "Confirm subscription</button></form>"))
            return

        if path == "/unsubscribe":
            tokens = params.get("t", [])
            if not tokens:
                self._send(*page("Missing token",
                    "<h2>Missing token</h2><p>This unsubscribe URL is incomplete.</p>",
                    status=400))
                return
            result = subs.unsubscribe(tokens[0])
            if result:
                self._send(*page("Unsubscribed",
                    f"<h2>You're unsubscribed.</h2>"
                    f"<p><code>{result['email']}</code> won't receive further emails. "
                    "No follow-up. Thanks for reading.</p>"))
            else:
                self._send(*page("Already unsubscribed",
                    "<h2>Already unsubscribed</h2><p>This address isn't on the list. "
                    "Nothing more to do.</p>", status=404))
            return

        self._send(*page("Not found", "<h2>Not found</h2>", status=404))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        # RFC 8058 one-click unsubscribe: mail clients POST here with body
        # "List-Unsubscribe=One-Click"; the token is in the ?t= query param.
        if path == "/unsubscribe":
            try:
                self.rfile.read(int(self.headers.get("Content-Length", "0") or 0))
            except Exception:
                pass
            tokens = params.get("t", [])
            if tokens:
                subs.unsubscribe(tokens[0])
            self._send(204, b"")
            return

        # Confirmation happens on POST (the button on the GET /confirm page),
        # never on GET — so email-security scanners that auto-fetch the link
        # cannot auto-confirm. The token is in the ?token= query param.
        if path == "/confirm":
            try:
                self.rfile.read(int(self.headers.get("Content-Length", "0") or 0))
            except Exception:
                pass
            tokens = params.get("token", [])
            if not tokens:
                self._send(*page("Missing token",
                    "<h2>Missing token</h2><p>This confirmation URL is incomplete.</p>", status=400))
                return
            result = subs.confirm_subscriber(tokens[0])
            if result:
                self._send(*page("Confirmed",
                    f"<h2>You're confirmed.</h2><p>Welcome, <code>{result['email']}</code>. "
                    "Tomorrow's brief arrives at 08:30 PT.</p>"))
            else:
                self._send(*page("Already confirmed",
                    "<h2>Already confirmed (or expired link)</h2>"
                    "<p>This link has been used or has expired. If you meant to subscribe, "
                    "<a href=\"https://briefer.news/about/\">resubscribe from briefer.news</a>.</p>",
                    status=404))
            return

        if path != "/subscribe":
            self._send(*page("Not found", "<h2>Not found</h2>", status=404))
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        content_type = self.headers.get("Content-Type", "").split(";")[0].strip().lower()

        # Parse either form-encoded or JSON body
        if content_type == "application/json":
            try:
                data = json.loads(raw)
            except Exception:
                self._send(*page("Bad request", "<h2>Bad request</h2><p>Invalid JSON.</p>", status=400))
                return
        else:
            data = {k: v[0] for k, v in urllib.parse.parse_qs(raw).items()}

        email = (data.get("email") or "").strip().lower()
        edition = (data.get("edition") or "both").strip().lower()
        if edition not in ("us", "china", "both"):
            edition = "both"

        # ── Abuse guards: honeypot → browser-context → email shape → rate ───
        # Honeypot: hidden fields a human leaves blank. Silently accept + drop.
        if any((data.get(f) or "").strip() for f in HONEYPOT_FIELDS):
            self.log_message("honeypot tripped ip=%s", _client_ip(self))
            self._send(*page("Check your inbox",
                "<h2>Check your inbox.</h2><p>If that address is valid, a "
                "confirmation link is on its way.</p>"))
            return
        # A real browser submission always carries Origin or Referer; the
        # current bot pattern is a bare API POST with neither.
        if not (self.headers.get("Origin") or self.headers.get("Referer")):
            self._send(*page("Forbidden", "<h2>Forbidden</h2>", status=403))
            return
        if not EMAIL_RE.match(email):
            self._send(*page("Invalid email",
                "<h2>Invalid email</h2><p>Please enter a valid email address.</p>",
                status=400))
            return
        if email.rsplit("@", 1)[-1] in BLOCKED_DOMAINS:
            self.log_message("blocked-domain signup dropped ip=%s email=%s", _client_ip(self), email)
            self._send(*page("Check your inbox",
                "<h2>Check your inbox.</h2><p>If that address is valid, a "
                "confirmation link is on its way.</p>"))
            return
        ip = _client_ip(self)
        reason = _rate_check(ip)
        if reason:
            self.log_message("rate-limited (%s) ip=%s email=%s", reason, ip, email)
            self._send(*page("Slow down",
                "<h2>One moment.</h2><p>Too many signups from your network just "
                "now — try again shortly.</p>", status=429))
            return
        _rate_record(ip)

        try:
            sub = subs.add_subscriber(email, edition=edition,
                                     notes=f"signup via API at {dt.datetime.now().isoformat()} ip={ip}")
        except ValueError as e:
            self._send(*page("Invalid email", f"<h2>Invalid email</h2><p>{e}</p>", status=400))
            return

        # If newly created, send confirmation email
        if sub.get("status") == "pending" and sub.get("confirmation_token"):
            ok = send_confirmation(email, sub["confirmation_token"], sub.get("unsubscribe_token", ""))
            if not ok:
                self._send(*page("Send failed",
                    "<h2>Hmm, something went wrong.</h2>"
                    "<p>We couldn't send the confirmation email. Try again in a minute, "
                    "or email <a href=\"mailto:news@briefer.news\">news@briefer.news</a>.</p>",
                    status=500))
                return
            self._send(*page("Check your inbox",
                f"<h2>Check your inbox.</h2>"
                f"<p>We sent a confirmation link to <code>{email}</code>. "
                "Click it to start receiving Briefer News.</p>"))
        else:
            # Already exists — confirm or remind
            self._send(*page("Already subscribed",
                f"<h2>Already on the list.</h2>"
                f"<p><code>{email}</code> is already subscribed (status: {sub.get('status')}). "
                "If you want to manage your subscription, the unsubscribe link is in every email.</p>"))


def main() -> int:
    # Allow reuse of the address so quick restarts don't block
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Briefer News email API listening on 0.0.0.0:{PORT}", file=sys.stderr)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
