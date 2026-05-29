#!/usr/bin/env python3
"""
config.py — Python view of scripts/lib/env.sh.

Parses env.sh (pure KEY=value bash assignments) line-by-line so the two
Python deploy callers (inject_weekly_preview.py, traffic_report.py) read the
SAME source of truth as the shell scripts. No drift: edit env.sh, both shell
and Python follow.

env.sh is intentionally restricted to bare 'KEY=value' lines (plus comments
and blanks), so a trivial parser is correct — we do not need a shell to
evaluate it, which keeps Python free of a subprocess dependency on bash.

Exposes the constants both as module attributes (config.DIST_ID) and via the
ENV dict (config.ENV["DIST_ID"]).
"""

from __future__ import annotations

from pathlib import Path

_ENV_PATH = Path(__file__).resolve().parent / "env.sh"


def _parse_env(path: Path) -> dict:
    env: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        # env.sh holds bare unquoted values, but strip surrounding quotes
        # defensively in case one is ever added.
        val = val.strip().strip('"').strip("'")
        if key:
            env[key] = val
    return env


ENV = _parse_env(_ENV_PATH)

# Module-level constants for direct import. Mirror env.sh exactly.
DIST_ID = ENV["DIST_ID"]
S3_BUCKET = ENV["S3_BUCKET"]
CF_LOGS_BUCKET = ENV["CF_LOGS_BUCKET"]
AWS = ENV["AWS"]
DOCKER = ENV["DOCKER"]
REPO = ENV["REPO"]
REGION = ENV["REGION"]
CF_DOMAIN = ENV["CF_DOMAIN"]
