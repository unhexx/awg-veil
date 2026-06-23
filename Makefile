.PHONY: install dev lint typecheck test coverage clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

lint:
	ruff check src tests

typecheck:
	mypy src

test:
	pytest

coverage:
	pytest --cov=awg_veil --cov-report=term-missing --cov-fail-under=85

check: lint typecheck coverage

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
