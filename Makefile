PYTHON ?= ./.venv/bin/python
PIP ?= $(PYTHON) -m pip
PYTEST ?= $(PYTHON) -m pytest
RUFF ?= $(PYTHON) -m ruff

.PHONY: help install-dev lint test test-web test-visual test-scoring ci web

help:
	@printf "%s\n" "Brand3 development commands"
	@printf "%s\n" ""
	@printf "%s\n" "  make install-dev   Install local dev dependencies"
	@printf "%s\n" "  make lint          Run Ruff gate"
	@printf "%s\n" "  make test          Run full pytest suite"
	@printf "%s\n" "  make test-web      Run web route/UI tests"
	@printf "%s\n" "  make test-visual   Run Visual Signature tests"
	@printf "%s\n" "  make test-scoring  Run scoring/report core tests"
	@printf "%s\n" "  make ci            Run local CI gate"
	@printf "%s\n" "  make web           Start local FastAPI/Jinja app"

install-dev:
	$(PIP) install -e ".[dev]"

lint:
	$(RUFF) check .

test:
	$(PYTEST) -q

test-web:
	$(PYTEST) tests/test_web_app.py tests/test_web_listings.py tests/test_web_visual_signature_routes.py -q

test-visual:
	$(PYTEST) tests/test_visual_signature*.py -q

test-scoring:
	$(PYTEST) tests/test_scoring_engine.py tests/test_reports_derivation.py tests/test_reports_renderer.py -q

ci: lint test

web:
	scripts/run_web_dev_macos.sh
