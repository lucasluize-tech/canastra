# Canastra dev Makefile. Boring and explicit: every target is one command.
# Run `make` with no args for a short help listing.

PYTHON ?= python3
# Local installs go through uv for speed. CI uses plain pip (no uv on runners).
PIP    ?= uv pip

.DEFAULT_GOAL := help
.PHONY: help install install-dev lint format typecheck test test-cov hooks ci clean web

help:
	@echo "Targets:"
	@echo "  install      Install runtime deps only"
	@echo "  install-dev  Install runtime + dev deps"
	@echo "  lint         ruff check ."
	@echo "  format       ruff format ."
	@echo "  typecheck    mypy on canastra package"
	@echo "  test         pytest (no coverage gate)"
	@echo "  test-cov     pytest with coverage report"
	@echo "  hooks        Install pre-commit git hook"
	@echo "  ci           Run the full CI pipeline locally"
	@echo "  web          Run the FastAPI/WebSocket dev server (uvicorn --reload)"
	@echo "  clean        Remove caches and coverage artifacts"

install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements.txt -r requirements-dev.txt

lint:
	ruff check .
	ruff format --check .

format:
	ruff check --fix .
	ruff format .

typecheck:
	mypy canastra

test:
	pytest --no-cov

test-cov:
	pytest

hooks:
	pre-commit install

ci: lint typecheck test-cov

web:
	CANASTRA_DEBUG=1 CANASTRA_SESSION_SECRET=$$($(PYTHON) -c "import secrets; print(secrets.token_urlsafe(32))") \
		WEB_CONCURRENCY=1 uvicorn canastra.web:app --reload --host 127.0.0.1 --port 8000

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov build dist
	rm -f .coverage coverage.xml
	find . -type d -name __pycache__ -not -path "./venv/*" -not -path "./.venv/*" -exec rm -rf {} +
