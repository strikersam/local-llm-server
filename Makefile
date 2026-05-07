# Makefile — local-llm-server developer commands
#
# Usage: make <target>
# Requires: make, python3, .venv (run: python3 -m venv .venv && pip install -r requirements.txt)

PYTHON  ?= .venv/bin/python
PYTEST  ?= .venv/bin/pytest
UVICORN ?= .venv/bin/uvicorn

.PHONY: help install dev test test-fast test-verbose lint hooks-install
.PHONY: changelog-check ai-start ai-status ai-resume ai-stop ai-logs
.PHONY: manifest summary audit ui-docs

# ── Help ──────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "local-llm-server — developer targets"
	@echo ""
	@echo "  make install         Install dependencies into .venv"
	@echo "  make dev             Start proxy in hot-reload mode"
	@echo "  make test            Run full test suite"
	@echo "  make test-fast       Run tests with -x (fail fast)"
	@echo "  make test-verbose    Run tests with -v"
	@echo "  make lint            Python syntax check on all .py files"
	@echo "  make hooks-install   Activate .claude/hooks (blocking guardrails)"
	@echo "  make changelog-check Check docs/changelog.md has [Unreleased] content"
	@echo ""
	@echo "  make ai-start        Start AI runner session"
	@echo "  make ai-status       Show current AI session state"
	@echo "  make ai-resume       Resume interrupted AI session"
	@echo "  make ai-stop         Stop current AI session"
	@echo "  make ai-logs         Tail AI session logs"
	@echo ""
	@echo "  make manifest        List all available skills and commands"
	@echo "  make summary         Summarize last AI session"
	@echo "  make audit           Run dependency and security audit"
	@echo "  make ui-docs         Refresh UI screenshots + README gallery"
	@echo ""

# ── Setup ─────────────────────────────────────────────────────────────────────

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

dev:
	$(UVICORN) proxy:app --reload --port 8000

# ── Tests ─────────────────────────────────────────────────────────────────────

test:
	$(PYTEST) -v

test-fast:
	$(PYTEST) -x

test-verbose:
	$(PYTEST) -v --tb=long

# ── Lint ──────────────────────────────────────────────────────────────────────

lint:
	@echo "Checking Python syntax..."
	@find . -name "*.py" -not -path "./.venv/*" -not -path "./.git/*" \
		-exec $(PYTHON) -m py_compile {} + && echo "✓ All files OK" || echo "✗ Syntax errors found"

# ── Hooks ─────────────────────────────────────────────────────────────────────

hooks-install:
	git config core.hooksPath .claude/hooks
	@echo "✓ Blocking hooks activated (.claude/hooks)"
	@echo "  Hooks: pre-commit, commit-msg, pre-push"

# ── Changelog ─────────────────────────────────────────────────────────────────

changelog-check:
	@$(PYTHON) scripts/ai_runner.py changelog-check 2>/dev/null || \
		python3 -c "\
import re, sys; \
content = open('docs/changelog.md').read(); \
m = re.search(r'## \[Unreleased\](.*?)## \[', content, re.DOTALL); \
body = m.group(1).strip() if m else ''; \
placeholder = body in ('', '_(nothing pending)_'); \
print('✓ Changelog has content' if not placeholder else '✗ No [Unreleased] entries found'); \
sys.exit(1 if placeholder else 0) \
"

# ── AI Runner ─────────────────────────────────────────────────────────────────

ai-start:
	$(PYTHON) scripts/ai_runner.py start

ai-status:
	$(PYTHON) scripts/ai_runner.py status

ai-resume:
	$(PYTHON) scripts/ai_runner.py resume

ai-stop:
	$(PYTHON) scripts/ai_runner.py stop

ai-logs:
	$(PYTHON) scripts/ai_runner.py logs

# ── Introspection ─────────────────────────────────────────────────────────────

manifest:
	$(PYTHON) scripts/ai_runner.py manifest

summary:
	$(PYTHON) scripts/ai_runner.py summary

audit:
	$(PYTHON) scripts/ai_runner.py audit

ui-docs:
	python3 scripts/gen_webui_screenshots.py
