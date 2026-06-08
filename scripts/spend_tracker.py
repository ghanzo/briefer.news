#!/usr/bin/env python3
"""
spend_tracker.py — daily project-spend snapshot -> Memex rolling note.

Part of the context-graph initiative (Phase 1a). Gathers spend across every
source and writes/updates a rolling note "Projects/Briefer/Spend.md" in Memex via
the raw MCP streamable-HTTP protocol. It makes NO `claude` call, so it never
consumes the Max-subscription quota the synth depends on.

Sources:
  - Claude Code (Max)     fixed $100/mo  (also the synth quota SPOF)
  - AWS deploy acct       Cost Explorer (month-to-date, by service)
  - .news domain          fixed annual (registrar acct has CE disabled)
  - SES email             send volume vs the free tier (cost flag)
  - Cloudflare            $0 free tier (Tunnel + RUM)
  - Anthropic API         $0 (unused)

History is kept locally in .run/spend_history.json and the whole Memex note is
re-rendered from it each run (idempotent; no fragile markdown editing).

Usage:
  python3 scripts/spend_tracker.py            # gather + write to Memex
  python3 scripts/spend_tracker.py --dry-run  # gather + print, do NOT write Memex
"""
from __future__ import annotations
import datetime
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

MEMEX_URL = "http://10.0.0.5:8765/mcp"
SPEND_NOTE = "Projects/Briefer/Spend.md"
HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.join(HERE, "..", ".run", "spend_history.json")
AWS = shutil.which("aws") or "/opt/homebrew/bin/aws"   # pinned for LaunchAgent in the plist

DEPLOY_ACCT = "462170975634"
CLAUDE_MAX_MONTHLY = 100.00
DOMAIN = {"name": "briefer.news", "annual": 30.00, "renews": "2026-08-08"}
SES_REGION = "us-east-1"
DRY = "--dry-run" in sys.argv


def sh(args, timeout=60):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:  # noqa: BLE001
        return 1, "", str(e)


# ── cost sources ────────────────────────────────────────────────────────────
def aws_mtd_by_service():
    today = datetime.date.today()
    start = today.replace(day=1).isoformat()
    end = (today + datetime.timedelta(days=1)).isoformat()
    rc, out, err = sh([AWS, "ce", "get-cost-and-usage", "--region", "us-east-1",
                       "--time-period", f"Start={start},End={end}", "--granularity", "MONTHLY",
                       "--metrics", "UnblendedCost", "--group-by", "Type=DIMENSION,Key=SERVICE",
                       "--output", "json"])
    if rc != 0:
        return None, (err or "ce error")[:120]
    try:
        d = json.loads(out)
    except Exception:  # noqa: BLE001
        return None, "ce parse error"
    svc = {}
    for r in d.get("ResultsByTime", []):
        for g in r.get("Groups", []):
            amt = float(g["Metrics"]["UnblendedCost"]["Amount"])
            if amt > 0.0001:
                svc[g["Keys"][0]] = round(amt, 2)
    return svc, None


def ses_24h():
    rc, out, _ = sh([AWS, "ses", "get-send-quota", "--region", SES_REGION, "--output", "json"])
    if rc != 0:
        return None
    try:
        d = json.loads(out)
        return {"sent24h": float(d.get("SentLast24Hours", 0)), "max24h": float(d.get("Max24HourSend", 0))}
    except Exception:  # noqa: BLE001
        return None


# ── Memex raw MCP client (no claude) ────────────────────────────────────────
class Memex:
    def __init__(self, url):
        self.url, self.sid = url, None

    def _post(self, body):
        req = urllib.request.Request(self.url, data=json.dumps(body).encode(), method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        if self.sid:
            req.add_header("Mcp-Session-Id", self.sid)
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            raw, sid = resp.read().decode("utf-8", "replace"), resp.headers.get("Mcp-Session-Id")
        except urllib.error.HTTPError as e:
            raw, sid = e.read().decode("utf-8", "replace"), e.headers.get("Mcp-Session-Id")
        if sid:
            self.sid = sid
        chunks = []
        for line in raw.splitlines():
            s = line.strip()
            if s.startswith("data:"):
                try:
                    chunks.append(json.loads(s[5:].strip()))
                except Exception:  # noqa: BLE001
                    pass
        if chunks:
            return chunks[-1]
        try:
            return json.loads(raw)
        except Exception:  # noqa: BLE001
            return {"raw": raw}

    def initialize(self):
        self._post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "spend-tracker", "version": "1.0"}}})
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _call(self, name, args):
        return self._post({"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                           "params": {"name": name, "arguments": args}})

    @staticmethod
    def _ok(resp):
        return isinstance(resp, dict) and "error" not in resp and not (resp.get("result", {}) or {}).get("isError")

    def write_note(self, path, body, frontmatter):
        # rolling note: try update; if it doesn't exist yet, create it
        if not self._ok(self._call("memex_save_note", {"path": path, "body": body})):
            self._call("memex_create_note", {"path": path, "body": body, "frontmatter": frontmatter})
        self._call("memex_push_note", {"path": path})


# ── history + render ────────────────────────────────────────────────────────
def load_history():
    try:
        with open(HISTORY) as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return []


def save_history(h):
    os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
    with open(HISTORY, "w") as f:
        json.dump(h, f, indent=2)


def render(today, aws_svc, aws_total, aws_err, ses, hist):
    sub, dom_mo = CLAUDE_MAX_MONTHLY, DOMAIN["annual"] / 12
    support = round(sum(v for k, v in (aws_svc or {}).items() if "Support" in k), 2)
    forward_aws = round((aws_total or 0) - support, 2)
    total_mo = sub + dom_mo + forward_aws
    if aws_total is None:
        aws_cell, aws_note = f"n/a ({aws_err})", "Cost Explorer unreachable"
    elif support > 0:
        aws_cell = f"~${forward_aws:.2f}/mo fwd"
        aws_note = f"MTD ${aws_total:.2f} incl. ${support:.0f} support — offset by the $35 credit at cycle-end"
    else:
        aws_cell, aws_note = f"${aws_total:.2f} MTD", "usage only; Basic support ($0)"
    ses_line = "~$0 — under free tier"
    if ses:
        ses_line = f"~$0 · {ses['sent24h']:.0f} sent/24h of {ses['max24h']:.0f} cap"
    L = [
        "# Briefer — Spend\n",
        f"_Auto-updated {today} by `scripts/spend_tracker.py` (no Claude calls)._\n",
        "## Monthly run-rate (forward — excludes one-off support being credited)\n",
        "| Source | Cost | Notes |",
        "|---|---|---|",
        f"| Claude Code (Max) | ${sub:.2f}/mo | fixed; also the synth quota SPOF |",
        f"| AWS deploy ({DEPLOY_ACCT}) | {aws_cell} | {aws_note} |",
        f"| .news domain | ${DOMAIN['annual']:.0f}/yr (~${dom_mo:.2f}/mo) | auto-renews {DOMAIN['renews']} |",
        "| Anthropic API | $0 | unused |",
        "| Cloudflare | $0 | Tunnel + RUM free tier |",
        f"| SES email | {ses_line} | watch vs free tier |",
        f"| **Total** | **~${total_mo:.2f}/mo** | ~{100 * sub / total_mo:.0f}% is the Max subscription |\n",
    ]
    if aws_svc:
        L.append("### AWS this month, by service")
        for k, v in sorted(aws_svc.items(), key=lambda x: -x[1]):
            L.append(f"- {k}: ${v:.2f}")
        L.append("")
    L.append("## Daily history (AWS month-to-date)\n")
    L.append("| Date | AWS MTD | SES sent/24h |")
    L.append("|---|---|---|")
    for row in hist[-30:]:
        s = row.get("ses_24h")
        L.append(f"| {row['date']} | ${row.get('aws_mtd', 0):.2f} | {('%.0f' % s) if s is not None else '-'} |")
    return "\n".join(L)


def main():
    today = datetime.date.today().isoformat()
    aws_svc, aws_err = aws_mtd_by_service()
    aws_total = round(sum(aws_svc.values()), 2) if aws_svc else None
    ses = ses_24h()

    hist = [r for r in load_history() if r.get("date") != today]
    hist.append({"date": today, "aws_mtd": aws_total or 0, "ses_24h": ses["sent24h"] if ses else None})
    hist.sort(key=lambda r: r["date"])

    body = render(today, aws_svc, aws_total, aws_err, ses, hist)
    _support = sum(v for k, v in (aws_svc or {}).items() if "Support" in k)
    total_mo = CLAUDE_MAX_MONTHLY + DOMAIN["annual"] / 12 + ((aws_total or 0) - _support)

    if DRY:
        print(body)
        print(f"\n[dry-run] would write {SPEND_NOTE}; total ~${total_mo:.2f}/mo")
        return

    save_history(hist)
    mx = Memex(MEMEX_URL)
    mx.initialize()
    mx.write_note(SPEND_NOTE, body, {"tags": ["briefer", "spend", "auto"], "status": "active"})
    print(f"wrote {SPEND_NOTE} to Memex; total ~${total_mo:.2f}/mo")


if __name__ == "__main__":
    main()
