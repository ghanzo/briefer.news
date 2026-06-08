#!/bin/bash
# daily_memex.sh — daily project pulse -> Memex (NO claude calls).
# Part of the context-graph loop. Each tracker writes its rolling Memex note(s)
# over the raw MCP protocol, so this never touches the Claude subscription quota.
# Wired via ~/Library/LaunchAgents/news.briefer.spend.plist.
cd /Users/maxgoshay/code/briefernewsapp || exit 1
/usr/bin/python3 scripts/spend_tracker.py
/usr/bin/python3 scripts/status_tracker.py
