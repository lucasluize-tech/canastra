# Canastra dev Makefile. Boring and explicit: every target is one command.
# Run `make` with no args for a short help listing.

PYTHON ?= python3
# Local installs go through uv for speed. CI uses plain pip (no uv on runners).
PIP    ?= uv pip

.DEFAULT_GOAL := help
.PHONY: help install install-dev lint format typecheck test test-cov hooks ci clean

help:
	@echo "Targets:"
	@echo "  install      Install runtime deps only"
	@echo "  install-dev  Install runtime + dev deps"
	@echo "  lint         ruff check ."
	@echo "  format       ruff format ."
	@echo "  typecheck    mypy on flat modules"
	@echo "  test         pytest (no coverage gate)"
	@echo "  test-cov     pytest with coverage report"
	@echo "  hooks        Install pre-commit git hook"
	@echo "  ci           Run the full CI pipeline locally"
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
	mypy deck.py player.py table.py helpers.py

test:
	pytest --no-cov

test-cov:
	pytest

hooks:
	pre-commit install

ci: lint typecheck test-cov

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov build dist
	rm -f .coverage coverage.xml
	find . -type d -name __pycache__ -not -path "./venv/*" -not -path "./.venv/*" -exec rm -rf {} +
