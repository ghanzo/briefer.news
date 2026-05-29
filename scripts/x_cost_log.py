#!/usr/bin/env python3
"""x_cost_log.py — append-only cost ledger for X (Twitter) API usage.

Mandated by MARKETING.md: a $25 X API credit was funded 2026-05-27. Each
write (post) costs ~$0.20 on the Basic tier (~125 posts); reads are ~free.
This logger records one JSON line per metered call to
logs/x-costs-YYYY-MM-DD.jsonl and keeps a running total across all
x-costs-*.jsonl files so we never silently burn through the credit.

X's API does NOT currently expose a per-call dollar cost in its response
(tweepy's create_tweet returns a (data, includes, errors, meta) namedtuple
with no .headers). So append_cost() will:
  1. capture whatever usage/rate-limit headers ARE available (passed as a
     dict, or pulled off a raw requests.Response-like object) into
     raw_headers for forensics, and
  2. fall back to the MARKETING.md estimate for est_usd (writes=$0.20,
     reads=$0.00) — overridable if a future header ever exposes real cost.

When the remaining budget (X_CREDIT_BUDGET - running_total) drops below
X_CREDIT_WARN, fire a notify("warn", ...).

CLI:
    python3 scripts/x_cost_log.py --summary      # total spent + remaining
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notify import notify  # off-box SES alerter (best-effort, never raises)

REPO = Path(__file__).resolve().parent.parent
LOGS = REPO / "logs"

# Per MARKETING.md money authority: $25 credit funded 2026-05-27, ~$0.20/write.
X_CREDIT_BUDGET = float(os.environ.get("X_CREDIT_BUDGET", "25.00"))
X_CREDIT_WARN = float(os.environ.get("X_CREDIT_WARN", "5.00"))

# Estimated USD per metered call when X exposes no real per-call cost.
_EST_USD = {"post": 0.20, "read": 0.0}

# Response headers worth recording for forensics (X publishes rate-limit
# headers; if a usage/cost header ever appears it'll be captured too).
_HEADER_KEYS = (
    "x-rate-limit-limit",
    "x-rate-limit-remaining",
    "x-rate-limit-reset",
    "x-app-limit-24hour-limit",
    "x-app-limit-24hour-remaining",
    "x-app-limit-24hour-reset",
    "x-user-limit-24hour-limit",
    "x-user-limit-24hour-remaining",
    "x-user-limit-24hour-reset",
)


def _cost_path(day: str | None = None) -> Path:
    day = day or dt.date.today().isoformat()
    return LOGS / f"x-costs-{day}.jsonl"


def _extract_headers(resp_headers, response) -> dict:
    """Best-effort pull of usage/rate-limit headers from either an explicit
    dict (resp_headers) or a response-like object.

    tweepy's create_tweet Response namedtuple has no .headers, so this most
    often returns {} for posts — but a raw requests.Response (which has
    .headers) or a future tweepy that surfaces them will be captured."""
    headers = None
    if resp_headers is not None:
        headers = resp_headers
    elif response is not None:
        # raw requests.Response or anything exposing a .headers mapping
        h = getattr(response, "headers", None)
        if h is not None:
            headers = h
    if not headers:
        return {}
    out = {}
    try:
        # case-insensitively pull the keys we care about
        lower = {str(k).lower(): v for k, v in dict(headers).items()}
    except Exception:
        return {}
    for k in _HEADER_KEYS:
        if k in lower:
            out[k] = lower[k]
    return out


def _running_total(upto_path: Path | None = None) -> float:
    """Sum est_usd across every x-costs-*.jsonl file (today + prior).

    If upto_path is given, only that file (and same-dir siblings) is scanned
    — used so unit tests can point at a tmp dir instead of logs/."""
    base = Path(upto_path).parent if upto_path is not None else LOGS
    total = 0.0
    if not base.exists():
        return 0.0
    for f in sorted(base.glob("x-costs-*.jsonl")):
        try:
            for line in f.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                total += float(rec.get("est_usd", 0.0) or 0.0)
        except Exception:
            continue
    return round(total, 4)


def append_cost(
    kind: str,
    units: int = 1,
    note: str = "",
    resp_headers=None,
    response=None,
    est_usd: float | None = None,
    path: Path | None = None,
    notify_dry_run: bool = False,
) -> dict:
    """Append one cost line to logs/x-costs-YYYY-MM-DD.jsonl and return it.

    kind         "post" (write, ~$0.20/unit) or "read" (~free).
    units        number of metered calls this line represents (default 1).
    note         free-text context (e.g. tweet id, collector run).
    resp_headers explicit headers dict to record under raw_headers.
    response     a response object to probe for .headers (e.g. tweepy's
                 create_tweet result — it has none today, captured anyway).
    est_usd      override the estimated cost; default is the MARKETING.md
                 per-unit estimate * units.
    path         override the output file (tests point this at a tmp dir).
    notify_dry_run  pass dry_run=True to notify() (tests / safe verification).

    Fires notify("warn", ...) when remaining budget drops below X_CREDIT_WARN.
    """
    if kind not in _EST_USD:
        raise ValueError(f"unknown kind {kind!r}; expected one of {sorted(_EST_USD)}")

    out_path = Path(path) if path else _cost_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    raw_headers = _extract_headers(resp_headers, response)
    if est_usd is None:
        est_usd = round(_EST_USD[kind] * units, 4)
    else:
        est_usd = round(float(est_usd), 4)

    # running total = everything already on disk + this line's cost
    prior = _running_total(out_path)
    running_total = round(prior + est_usd, 4)

    rec = {
        "ts": dt.datetime.now().isoformat(),
        "kind": kind,
        "units": units,
        "est_usd": est_usd,
        "running_total_usd": running_total,
        "note": note,
    }
    if raw_headers:
        rec["raw_headers"] = raw_headers

    with out_path.open("a") as f:
        f.write(json.dumps(rec) + "\n")

    remaining = round(X_CREDIT_BUDGET - running_total, 4)
    if remaining < X_CREDIT_WARN:
        notify(
            "warn",
            f"X credit low: ${remaining:.2f} of ${X_CREDIT_BUDGET:.2f} remaining "
            f"(spent ${running_total:.2f})",
            dry_run=notify_dry_run,
        )

    return rec


def summary(path: Path | None = None) -> dict:
    total = _running_total(path)
    remaining = round(X_CREDIT_BUDGET - total, 4)
    return {
        "budget_usd": X_CREDIT_BUDGET,
        "warn_floor_usd": X_CREDIT_WARN,
        "spent_usd": total,
        "remaining_usd": remaining,
        "below_warn": remaining < X_CREDIT_WARN,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="X API cost ledger")
    ap.add_argument("--summary", action="store_true",
                    help="print total spent + remaining budget")
    args = ap.parse_args(argv)

    if args.summary:
        s = summary()
        print(f"X API credit: ${s['budget_usd']:.2f} budget")
        print(f"  spent:     ${s['spent_usd']:.2f}")
        print(f"  remaining: ${s['remaining_usd']:.2f}"
              + ("  [BELOW WARN FLOOR]" if s["below_warn"] else ""))
        print(json.dumps(s))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
