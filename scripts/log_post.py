#!/usr/bin/env python3
"""
log_post.py — record a manual post (HN, Reddit, LinkedIn, Threads) so the
growth loop's Researcher and Analyzer see manual channels too.

The autonomous channels (X, Bluesky) log themselves. Manual channels don't,
so run this one-liner right after you post by hand:

    python3 scripts/log_post.py --channel hn --url "https://news.ycombinator.com/item?id=XXX"
    python3 scripts/log_post.py --channel reddit --url "https://reddit.com/r/geopolitics/..." --text "title used"

Writes one line to logs/posts-YYYY-MM-DD.jsonl in the same schema the
autonomous posters use, with result={"manual": true}.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x_post  # reuse log_post()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True,
                    help="hn, reddit, linkedin, threads, ...")
    ap.add_argument("--url", required=True, help="permalink to the post you made")
    ap.add_argument("--text", default="", help="optional: the title/body you used")
    ap.add_argument("--id", default=None,
                    help="optional: platform post id (e.g. HN item id)")
    args = ap.parse_args(argv)

    result = {"manual": True}
    if args.id:
        result["id"] = args.id

    x_post.log_post(args.channel.lower(), args.text, args.url, result)
    print(f"Logged manual {args.channel} post to logs/posts-{date.today().isoformat()}.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
