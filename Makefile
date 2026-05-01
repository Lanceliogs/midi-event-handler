.DEFAULT_GOAL := build

.PHONY: build installer test lint lint-fix format format-check check

build:
	snackbox build

installer:
	snackbox installer

test:
	poetry run pytest

lint:
	poetry run ruff check src/ tests/

lint-fix:
	poetry run ruff check --fix src/ tests/

format:
	poetry run ruff format src/ tests/

format-check:
	poetry run ruff format --check src/ tests/

check: lint format-check test
