#!/usr/bin/env python3
"""notify.py — thin Python entrypoint over scripts/alert.sh, so .py callers
(healthcheck.py, email_send.py, …) have one off-box notifier to import instead
of each re-implementing SES. Shell callers use alert.sh directly.

    from notify import notify
    notify("crit", "synth produced an empty US brief — kept yesterday's live")
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ALERT = Path(__file__).resolve().parent / "alert.sh"


def notify(severity: str, message: str, dry_run: bool = False) -> bool:
    """Send an operational alert. Returns True if a channel delivered it.
    Never raises — a failing notifier must not crash the caller's error path."""
    args = ["bash", str(_ALERT)]
    if dry_run:
        args.append("--dry-run")
    args += [severity, message]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            sys.stderr.write(r.stderr or r.stdout)
        return r.returncode == 0
    except Exception as e:  # notifier must be best-effort
        sys.stderr.write(f"notify() failed: {e}\n")
        return False


if __name__ == "__main__":
    sev = sys.argv[1] if len(sys.argv) > 1 else "info"
    msg = " ".join(sys.argv[2:]) or "notify.py self-test"
    sys.exit(0 if notify(sev, msg) else 1)
