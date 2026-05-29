# briefer.news — operator Makefile. Run from the repo root.
# `make` (or `make help`) lists targets; `make status` is the daily orientation
# screen so any session — human or AI — can see what's running, what shipped,
# and what's dirty in one shot instead of cross-checking launchctl + logs + curl.
SHELL := /bin/bash
REPO  := $(CURDIR)
PY    := /usr/bin/python3

.PHONY: help status preflight test check-brief preview healthcheck \
        synth synth-china clean-logs alert-test x-costs \
        agents-status agents-export agents-install

help:
	@echo "briefer.news — make targets:"
	@echo "  status        one-screen orientation: git, launchd jobs, live stamps, recent logs/alerts"
	@echo "  preflight     lint + syntax-check all scripts (scripts/preflight.sh)"
	@echo "  test          run the test suite (tests/)"
	@echo "  check-brief   parse live /usa/ + /china/ and print structure counts"
	@echo "  preview       run validate_brief against the live briefs (read-only)"
	@echo "  healthcheck   run the stale-brief healthcheck"
	@echo "  synth         run the US synth + deploy (synthesize.sh)  ** DEPLOYS **"
	@echo "  synth-china   run the China synth + deploy                ** DEPLOYS **"
	@echo "  clean-logs    rotate logs + DB cleanup (scripts/cleanup.sh)"
	@echo "  alert-test    send a DRY-RUN alert (no email leaves the box)"
	@echo "  x-costs       show X API credit spend / remaining"
	@echo "  agents-status | agents-export | agents-install   launchd schedule sync"

status:
	@echo "════════════ briefer.news status — $$(date '+%Y-%m-%d %H:%M %Z') ════════════"
	@echo "── git ($$(git -C "$(REPO)" branch --show-current)) ──"
	@git -C "$(REPO)" status -sb | head -1
	@git -C "$(REPO)" status -s | head -15 | sed 's/^/  /' || true
	@echo "── launchd jobs (PID  lastexit  label) ──"
	@launchctl list | grep briefer | sort -k3 | sed 's/^/  /' || echo "  (none loaded)"
	@echo "── live brief (stamp | events | headline words) ──"
	@$(PY) -c "import sys; sys.path.insert(0,'$(REPO)/scripts'); from brief_parser import parse_url; [print('  %-5s: %s | %d+%d events | headline %dw'%(e,d['date'],d['events_visible_count'],d['events_more_count'],d['headline_words'])) for e in ('usa','china') for d in [parse_url('https://briefer.news/%s/'%e)]]" 2>/dev/null || echo "  (could not fetch live briefs)"
	@echo "── recent logs (newest 6) ──"
	@ls -t "$(REPO)/logs" 2>/dev/null | head -6 | sed 's/^/  /'
	@echo "── alerts (last 3) ──"
	@tail -3 "$(REPO)/logs/alerts.log" 2>/dev/null | sed 's/^/  /' || echo "  (none)"

preflight:
	@bash "$(REPO)/scripts/preflight.sh"

test:
	@cd "$(REPO)" && $(PY) -m unittest discover -s tests -v

check-brief:
	@$(PY) "$(REPO)/scripts/brief_parser.py" https://briefer.news/usa/
	@echo ""
	@$(PY) "$(REPO)/scripts/brief_parser.py" https://briefer.news/china/

preview:
	@$(PY) "$(REPO)/scripts/validate_brief.py" https://briefer.news/usa/ --edition us || true
	@echo ""
	@$(PY) "$(REPO)/scripts/validate_brief.py" https://briefer.news/china/ --edition china || true

healthcheck:
	@$(PY) "$(REPO)/scripts/healthcheck.py"

synth:
	@bash "$(REPO)/scripts/synthesize.sh"

synth-china:
	@bash "$(REPO)/scripts/synthesize_china.sh"

clean-logs:
	@bash "$(REPO)/scripts/cleanup.sh"

alert-test:
	@bash "$(REPO)/scripts/alert.sh" --dry-run info "make alert-test — dry run, no send"

x-costs:
	@$(PY) "$(REPO)/scripts/x_cost_log.py" --summary 2>/dev/null || echo "  (x_cost_log.py not available yet)"

agents-status:
	@bash "$(REPO)/scripts/install_launchagents.sh" status

agents-export:
	@bash "$(REPO)/scripts/install_launchagents.sh" export

agents-install:
	@bash "$(REPO)/scripts/install_launchagents.sh" install
