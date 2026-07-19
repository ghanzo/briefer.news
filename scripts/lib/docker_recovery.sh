#!/bin/bash
# docker_recovery.sh — shared "get the Docker engine back" helper.
#
# Handles BOTH failure shapes that have caused outages:
#   1. Docker Desktop not running at all          → open -a Docker and wait.
#   2. Desktop app alive but engine dead/wedged   → hard-restart the app.
#      The 2026-07-17 VirtioFS wedge ("service fs failed: injecting event
#      blocked for 60s") presented exactly this way: engine stopped, an
#      always-on-top error dialog waiting for a click, and `open -a Docker`
#      a no-op because the app was already running. Containers stayed down
#      ~24h until a human quit the dialog and rebooted.
#
# Deliberately avoids osascript (AppleEvents from launchd would trigger TCC
# permission prompts); SIGTERM to the Desktop processes is handled gracefully
# by Docker and the engine was already dead on this path anyway.
#
# Usage:  . scripts/lib/docker_recovery.sh
#         docker_engine_recover [docker_path]   # default /usr/local/bin/docker
# Returns 0 when `docker info` succeeds, 1 if the engine is still dead.

docker_engine_recover() {
  local docker_bin="${1:-/usr/local/bin/docker}"

  "$docker_bin" info >/dev/null 2>&1 && return 0

  echo "  Docker engine down — launching Docker Desktop..."
  open -a Docker >/dev/null 2>&1 || true
  for _ in $(seq 1 45); do
    "$docker_bin" info >/dev/null 2>&1 && return 0
    sleep 4
  done

  echo "  Engine still dead after 3min — hard-restarting Docker Desktop..."
  pkill -TERM -f "Docker Desktop" 2>/dev/null || true
  pkill -TERM -f "com.docker.backend" 2>/dev/null || true
  sleep 15
  pkill -9 -f "Docker Desktop" 2>/dev/null || true
  pkill -9 -f "com.docker.backend" 2>/dev/null || true
  pkill -9 -f "com.docker.virtualization" 2>/dev/null || true
  sleep 10
  open -a Docker >/dev/null 2>&1 || true
  for _ in $(seq 1 60); do
    "$docker_bin" info >/dev/null 2>&1 && return 0
    sleep 5
  done

  echo "  Docker engine STILL dead after hard restart — host reboot likely required."
  return 1
}
