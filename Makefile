.PHONY: help setup install dev lint test golden build run format analyze

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

setup: ## Install the pre-commit hook
	pre-commit install

install: ## Install the package
	pip install .

dev: ## Editable install with dev deps (pytest, ruff, build)
	pip install -e ".[dev]"

lint: ## Run the whole gate — every hook, every file
	pre-commit run --all-files

test: ## Run tests
	pytest -q

golden: ## Regenerate the golden fixtures (needs hadolint on PATH)
	python3 tests/golden/regenerate.py
	HADOFIX_UPDATE_GOLDEN=1 pytest -q

build: ## Build sdist and wheel
	python -m build

run: ## Run hadofix
	hadofix --help

format: ## Rewrite the sources to canonical form
	ruff format .

analyze: ## Type-check the package
	basedpyright
