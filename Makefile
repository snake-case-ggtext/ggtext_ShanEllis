.PHONY: install test lint pre-commit

install: ## Install the package with the dev tools (uv sync) and the git hooks
	uv sync
	uv run prek install

test: ## Tests in random order (pytest-randomly) with coverage
	uv run pytest --cov=ggtext --cov-report=term-missing

lint: ## ruff (lint + format check) and pyrefly (strict, baselined)
	uv run ruff check .
	uv run ruff format --check .
	uv run pyrefly check

pre-commit: ## Install the git hooks and run them on every file
	uv run prek install
	uv run prek run --all-files
