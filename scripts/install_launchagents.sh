#!/bin/bash
# install_launchagents.sh — keep the briefer.news LaunchAgent schedule
# reproducible from git. The repo's launchd/ dir is the source of truth; the
# live schedule lives in ~/Library/LaunchAgents. This script syncs between them.
#
#   scripts/install_launchagents.sh export    # repo  <- live : copy installed plists INTO launchd/
#   scripts/install_launchagents.sh install   # repo  -> live : copy launchd/ plists out + (re)load them
#   scripts/install_launchagents.sh status     # show which plists are live-only / repo-only (default)
#
# Typical use:
#   - After adding/changing a LaunchAgent by hand: run `export`, then commit launchd/.
#   - On a fresh machine / after a disk loss: clone the repo, then run `install`.
#
# Why this exists: 9 of the 16 production agents previously lived ONLY in
# ~/Library/LaunchAgents with no repo copy, so the running product could not be
# rebuilt from git. `export` closes that gap; `install` reconstructs it.

set -euo pipefail

REPO="/Users/maxgoshay/code/briefernewsapp"
LAUNCH_REPO="$REPO/launchd"
LAUNCH_LIVE="$HOME/Library/LaunchAgents"
PREFIX="news.briefer."
UID_NUM="$(id -u)"

mkdir -p "$LAUNCH_REPO"

# List basenames of briefer plists in a dir (empty, not error, if none).
list_plists() {
  find "$1" -maxdepth 1 -type f -name "${PREFIX}*.plist" -exec basename {} \; 2>/dev/null | sort
}

mode="${1:-status}"

case "$mode" in
  export)
    echo "Exporting live LaunchAgents  ->  $LAUNCH_REPO"
    n=0
    for src in "$LAUNCH_LIVE/${PREFIX}"*.plist; do
      [ -e "$src" ] || continue
      cp -p "$src" "$LAUNCH_REPO/"
      echo "  exported $(basename "$src")"
      n=$((n + 1))
    done
    echo "Exported $n plist(s). Review + commit:  git -C \"$REPO\" status launchd/"
    ;;

  install)
    echo "Installing repo LaunchAgents  ->  $LAUNCH_LIVE  (and (re)loading each)"
    n=0
    for src in "$LAUNCH_REPO/${PREFIX}"*.plist; do
      [ -e "$src" ] || continue
      base="$(basename "$src")"
      label="${base%.plist}"
      dst="$LAUNCH_LIVE/$base"
      cp -p "$src" "$dst"
      # Reload cleanly: bootout the old instance (ignore if absent), then bootstrap.
      launchctl bootout "gui/$UID_NUM/$label" 2>/dev/null || true
      launchctl bootstrap "gui/$UID_NUM" "$dst" 2>/dev/null \
        || launchctl load "$dst" 2>/dev/null \
        || echo "  WARN: could not load $label (load it manually)"
      echo "  installed + loaded $label"
      n=$((n + 1))
    done
    echo "Installed $n plist(s). Verify:  launchctl list | grep briefer"
    ;;

  status)
    repo_list="$(list_plists "$LAUNCH_REPO")"
    live_list="$(list_plists "$LAUNCH_LIVE")"
    echo "repo  launchd/        : $(printf '%s\n' "$repo_list" | grep -c . || true) plist(s)"
    echo "live  LaunchAgents/   : $(printf '%s\n' "$live_list" | grep -c . || true) plist(s)"
    echo ""
    echo "LIVE but NOT in repo (run 'export' to capture):"
    comm -23 <(printf '%s\n' "$live_list") <(printf '%s\n' "$repo_list") | sed 's/^/  /'
    echo "REPO but NOT live (run 'install' to deploy):"
    comm -13 <(printf '%s\n' "$live_list") <(printf '%s\n' "$repo_list") | sed 's/^/  /'
    ;;

  *)
    echo "usage: $0 {export|install|status}" >&2
    exit 1
    ;;
esac
