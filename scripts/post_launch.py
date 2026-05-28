#!/usr/bin/env python3
"""
post_launch.py — one-time founder/launch tweet for briefer.news.

Composes the launch tweet (fixed opener + that morning's top U.S. events +
the site link) and posts it to X. Scheduled to run once at 07:45, after the
07:00 synth produces the day's brief.

Idempotent: a sentinel (logs/.launch_posted) guarantees it posts only once;
on success it also removes its own LaunchAgent so it never fires again.

    python3 scripts/post_launch.py            # compose + post (once)
    python3 scripts/post_launch.py --dry-run  # compose + print, do not post
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x_post

REPO = Path(__file__).resolve().parent.parent
LOGS = REPO / "logs"
RUN = REPO / ".run"
SENTINEL = LOGS / ".launch_posted"
CLAUDE = "/Users/maxgoshay/.local/bin/claude"
LABEL = "news.briefer.launch"

OPENER = ("I'm a builder, and I've spent a few years on this. Briefer News "
          "turns the day's government publications into one plain, fully cited "
          "brief, like a daily intelligence report. Today: ")
URL = "https://briefer.news/usa/?utm_source=x"
MAX_TEXT = 255  # leaves room for newline + 23-char t.co URL inside 280


def extract_events() -> list[str]:
    html = subprocess.run(["curl", "-s", "https://briefer.news/usa/"],
                          capture_output=True, text=True).stdout
    events = []
    i = html.find("Today's events")
    if i != -1:
        m = re.search(r'<ul class="items">([\s\S]+?)</ul>', html[i:])
        if m:
            for li in re.findall(r'<li[^>]*>([\s\S]+?)</li>', m.group(1))[:3]:
                sm = re.search(r'<summary[^>]*>([\s\S]+?)</summary>', li)
                lead = re.sub(r'<[^>]+>', '', sm.group(1)).strip() if sm else ''
                rest = li.split('</summary>', 1)[1] if '</summary>' in li else li
                desc = re.sub(r'<[^>]+>', '', re.split(r'<sup|<span', rest)[0]).strip()
                events.append((lead + ' ' + desc).strip())
    return events


def compose_fragment(events: list[str]) -> str:
    budget = MAX_TEXT - len(OPENER)
    prompt = f"""You are writing only the END of a tweet that already begins with:
"{OPENER}"

Append the 2-3 most important U.S. government events below as ultra-short,
plain-English phrases separated by commas, ending with a single colon.

Hard rules:
- Your output must be {budget} characters or fewer (it has to fit after the opener).
- Use 2 events if 3 will not fit. Shortest clear phrasing wins.
- Expand every acronym (e.g. "Quad" becomes "four nations"). Refer to officials
  who are not globally famous by country or institution.
- Do NOT use any dashes (no em-dash, en-dash, or hyphen as punctuation).
- Output ONLY the fragment (the events ending with a colon). No opener, no URL,
  no quotes, no preamble, no explanation.

Events:
{chr(10).join('- ' + e for e in events)}"""
    res = subprocess.run([CLAUDE, "-p", prompt, "--max-turns", "2"],
                         cwd=str(REPO), capture_output=True, text=True, timeout=180)
    frag = res.stdout.strip().strip('"').strip()
    return frag


def self_remove():
    plist = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"],
                   capture_output=True, text=True)
    try:
        plist.unlink()
    except FileNotFoundError:
        pass


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if SENTINEL.exists() and not args.dry_run:
        print(f"Launch tweet already posted ({SENTINEL.read_text().strip()}); skipping.")
        return 0

    events = extract_events()
    if not events:
        print("ERROR: no events extracted from /usa/ (brief not live yet?). Not posting.")
        return 1

    fragment = compose_fragment(events)
    text = OPENER + fragment

    # Validate before we ever post: must fit and contain no dashes.
    if not fragment or len(text) > MAX_TEXT or any(d in text for d in ("—", "–")) or " - " in text:
        print(f"ERROR: composed text failed validation (len={len(text)}). Not posting.")
        print(f"  fragment: {fragment!r}")
        return 1

    eff = len(text) + 1 + 23
    print(f"Composed launch tweet ({eff}/280):")
    print(f"  {text}")
    print(f"  {URL}")

    if args.dry_run:
        print("[dry-run] not posting.")
        return 0

    result = x_post.post(text, url=URL)
    x_post.log_post("x", text, URL, result)
    print(f"Posted: {result.get('url')}")
    SENTINEL.write_text(dt.datetime.now().isoformat())
    self_remove()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
