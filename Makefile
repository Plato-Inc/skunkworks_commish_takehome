.PHONY: dev test lint lint-fix install

install:
	poetry install

dev:
	poetry run uvicorn app.main:app --reload

test:
	poetry run pytest -q

lint:
	poetry run ruff check .

lint-fix:
	poetry run ruff check . --fix
