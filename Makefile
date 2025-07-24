.PHONY: install install_dev test test_coverage lint lint_fix format build clean update_dependency

install:
	@echo "Instaling dependencies..."
	pip install .

install_dev:
	@echo "Instaling dev dependencies..."
	pip install .[dev]


test:
	@echo "Running tests..."
	pytest -p no:warnings -s

test_coverage:
	@echo "Running tests with coverage..."
	pytest -p no:warnings --cov=ctxinject ./tests


lint:
	@echo "Running linter (ruff)..."
	ruff check . --exclude tests/lib

lint_fix:
	@echo "Running linter --fix (ruff)..."
	ruff check --fix . --exclude tests/lib

format:
	@echo "Formatting code (black e isort)..."
	black .
	isort .

build:
	@echo "Building package ..."
	python -m build

clean:
	@echo "Cleaning cache and build/dist related files..."
	@python -c "import shutil, glob, os; [shutil.rmtree(d, ignore_errors=True) for d in ['dist', 'build', '.mypy_cache', '.pytest_cache', '.ruff_cache'] + glob.glob('*.egg-info')]; [shutil.rmtree(os.path.join(r, d), ignore_errors=True) for r, ds, _ in os.walk('.') for d in ds if d == '__pycache__']"

update_dependency:
	@if not defined REPO (echo Erro: Forneça o nome do repositório. Exemplo: make update_dependency REPO=ctxinject && exit /b 1)
	@echo "Updating github dependency $(REPO)..."
	@pip install --upgrade --force-reinstall "git+https://github.com/bellirodrigo2/$(REPO).git@main"