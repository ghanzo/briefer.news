#!/bin/bash
# briefer.news boot-time bring-up.
#
# Triggered by ~/Library/LaunchAgents/news.briefer.boot.plist with
# RunAtLoad=true. Runs on user login.
#
# Belt-and-suspenders on top of Docker's `restart: unless-stopped` on
# postgres + nginx + adminer — explicitly waits for the Docker daemon
# to be ready, then `docker compose up -d` to start the persistent
# services. The `pipeline` service is profile-tagged (profiles: [manual])
# so it won't auto-start here; only the LaunchAgents at 04:00 / 07:00 /
# 07:30 PDT invoke it via `docker compose run --rm pipeline ...`.

set +e

REPO=/Users/maxgoshay/code/briefernewsapp
cd "$REPO"

LOG_DIR="$REPO/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/boot-$(date +%Y%m%d).log"
exec >> "$LOG_FILE" 2>&1

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Boot sequence starting at $(date)"
echo "═══════════════════════════════════════════════════════════════"

DOCKER=/usr/local/bin/docker

# Wait for Docker Engine to be ready — Docker Desktop typically takes
# 10-30 seconds to start, longer on cold boot. Poll for up to 5 minutes.
echo "Waiting for Docker Engine..."
DEADLINE=$(($(date +%s) + 300))
until "$DOCKER" info >/dev/null 2>&1; do
  if [ "$(date +%s)" -ge "$DEADLINE" ]; then
    echo "ERROR: Docker Engine not ready after 5 min — bailing"
    exit 0
  fi
  sleep 5
done
echo "Docker Engine ready."

# Bring up persistent services. `restart: unless-stopped` should already
# have started them, but `compose up -d` is idempotent and reconciles
# any drift between docker-compose.yml and running containers.
echo ""
echo "Bringing up postgres + nginx (adminer is auto)..."
"$DOCKER" compose up -d postgres nginx adminer 2>&1

echo ""
echo "Current container state:"
"$DOCKER" compose ps --format "table {{.Service}}\t{{.State}}\t{{.Status}}"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Boot sequence complete at $(date)"
echo "═══════════════════════════════════════════════════════════════"
