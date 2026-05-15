#!/bin/bash
# preflight.sh — pre-synthesis health check for the briefer.news pipeline.
#
# Catches the bug classes that have broken the daily synth and burned a
# full Claude turn budget for nothing:
#
#   1. Backticks in the synth/weekly scripts. Those prompts are built with
#      an unquoted `cat > "$P" <<EOF` heredoc; a backtick in the body is
#      command substitution, which mangles the prompt Claude receives.
#   2. Bash / Python syntax errors in any pipeline script.
#   3. A single source flooding the candidate pool (first-run archive
#      dumps). The per-source SQL cap absorbs it, but it is worth seeing.
#   4. Missing spec / prototype files the synth @-references.
#   5. Docker services (postgres, nginx) down.
#   6. Stale corpus — the overnight scrape produced too little to synth.
#   7. The headless `claude` CLI not being present.
#
# Cheap by design: NO Claude calls, runs in a couple of seconds. Run it
# by hand any time, or wire it ahead of the synth — exit 0 means green,
# exit 1 means at least one hard failure that should block the synth.

set -u

REPO=/Users/maxgoshay/code/briefernewsapp
cd "$REPO"

DOCKER=/usr/local/bin/docker
CLAUDE=/Users/maxgoshay/.local/bin/claude

FAIL=0
ok()   { echo "  ok    $*"; }
warn() { echo "  warn  $*"; }
fail() { echo "  FAIL  $*"; FAIL=1; }

echo "═══════════════════════════════════════════════════════════════"
echo "briefer.news preflight — $(date)"
echo "═══════════════════════════════════════════════════════════════"

# ── 1. Backtick lint ────────────────────────────────────────────────────────
# The synth/weekly scripts build prompts in unquoted heredocs and use $(...)
# — never backticks — for real command substitution. Any backtick is a bug.
echo ""
echo "[1] heredoc backtick lint"
for f in synthesize.sh synthesize_china.sh weekly.sh; do
  if [ ! -f "scripts/$f" ]; then
    fail "scripts/$f missing"
    continue
  fi
  n=$(grep -c '`' "scripts/$f" 2>/dev/null || true)
  n=${n:-0}
  if [ "$n" -gt 0 ]; then
    fail "scripts/$f has $n backtick(s) — will mangle the synth prompt"
    grep -n '`' "scripts/$f" | sed 's/^/          /'
  else
    ok "scripts/$f — clean"
  fi
done

# ── 2. Bash syntax ──────────────────────────────────────────────────────────
echo ""
echo "[2] bash -n syntax check"
for f in scripts/*.sh; do
  if bash -n "$f" 2>/dev/null; then
    ok "$f"
  else
    fail "$f — bash syntax error:"
    bash -n "$f" 2>&1 | sed 's/^/          /'
  fi
done

# ── 3. Python compile ───────────────────────────────────────────────────────
echo ""
echo "[3] python compile check"
for f in scripts/*.py; do
  if python3 -m py_compile "$f" 2>/dev/null; then
    ok "$f"
  else
    fail "$f — python syntax error:"
    python3 -m py_compile "$f" 2>&1 | sed 's/^/          /'
  fi
done

# ── 4. Required spec + prototype files ──────────────────────────────────────
echo ""
echo "[4] required spec / prototype files"
for f in DEK.md WEEKLY.md BRIEF_STYLE.md lens.md \
         research/prototype_us_2026-05-12.html \
         research/prototype_china_2026-05-12.html; do
  if [ -s "$f" ]; then
    ok "$f"
  else
    fail "missing or empty: $f"
  fi
done

# ── 5. Headless Claude CLI ──────────────────────────────────────────────────
echo ""
echo "[5] headless claude CLI"
if [ -x "$CLAUDE" ] || command -v claude >/dev/null 2>&1; then
  ok "claude CLI present"
else
  fail "claude CLI not found at $CLAUDE — Stage 2/4 cannot run"
fi

# ── 6. Docker services ──────────────────────────────────────────────────────
echo ""
echo "[6] docker services"
PG_UP=0
for c in briefer_postgres briefer_nginx; do
  if "$DOCKER" ps --format '{{.Names}}' 2>/dev/null | grep -q "^${c}$"; then
    ok "$c up"
    [ "$c" = "briefer_postgres" ] && PG_UP=1
  else
    fail "$c not running"
  fi
done

# ── 7. Corpus freshness + single-source flood ───────────────────────────────
echo ""
echo "[7] candidate corpus health"
if [ "$PG_UP" -eq 1 ]; then
  psql() { "$DOCKER" exec briefer_postgres psql -U briefer -d briefer -tA -c "$1" 2>/dev/null; }

  fresh=$(psql "SELECT COUNT(*) FROM articles WHERE scraped_at >= NOW() - INTERVAL '36 hours';")
  fresh=${fresh:-0}
  if [ "$fresh" -lt 20 ]; then
    fail "only $fresh article(s) scraped in the last 36h — overnight scrape likely failed"
  else
    ok "$fresh articles scraped in the last 36h"
  fi

  # Per-source SQL cap is 12; a source contributing >40 fresh rows is a
  # back-catalogue dump (e.g. a first-run allied-gov archive). The cap
  # absorbs it, so this is a warning, not a failure — but worth seeing.
  flood=$(psql "SELECT s.name || ' (' || COUNT(*) || ')'
                FROM articles a JOIN sources s ON a.source_id = s.id
                WHERE a.scraped_at >= NOW() - INTERVAL '36 hours'
                GROUP BY s.name HAVING COUNT(*) > 40
                ORDER BY COUNT(*) DESC;")
  if [ -n "$flood" ]; then
    warn "source(s) with a large fresh backlog (per-source cap=12 absorbs it):"
    echo "$flood" | sed 's/^/          /'
  else
    ok "no single-source flood"
  fi
else
  fail "postgres down — cannot check corpus"
fi

# ── Verdict ─────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
if [ "$FAIL" -eq 0 ]; then
  echo "PREFLIGHT: PASS — pipeline is clear to synthesize"
  echo "═══════════════════════════════════════════════════════════════"
  exit 0
else
  echo "PREFLIGHT: FAIL — resolve the FAIL line(s) above before synth"
  echo "═══════════════════════════════════════════════════════════════"
  exit 1
fi
