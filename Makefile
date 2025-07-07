.PHONY: dev test

dev:
	uvicorn app.main:app --reload

test:
	pytest -q
