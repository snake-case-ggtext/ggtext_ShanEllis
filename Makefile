.PHONY: install test tox lint pre-commit

install: ## Install the package with the dev tools (uv sync) and the git hooks
	uv sync
	uv run prek install

test: ## Tests in random order (pytest-randomly) with coverage
	uv run pytest --cov=ggtext --cov-report=term-missing

tox: ## Tests on each matplotlib: 3.10, 3.11 and the newest pre-release (tox-uv)
	uv run tox -p auto

lint: ## ruff (lint + format check) and pyrefly (strict, baselined)
	uv run ruff check .
	uv run ruff format --check .
	uv run pyrefly check

pre-commit: ## Install the git hooks and run them on every file
	uv run prek install
	uv run prek run --all-files
