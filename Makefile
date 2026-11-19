.PHONY: test lint pre-commit

test: ## Tests in random order (pytest-randomly) with coverage
	uv run pytest --cov=ggtext --cov-report=term-missing

lint: ## ruff (lint + format check) and pyrefly (strict, baselined)
	uv run ruff check .
	uv run ruff format --check .
	uv run pyrefly check

pre-commit: ## Install the git hooks and run them on every file
	uv run prek install
	uv run prek run --all-files
