.PHONY: install install_dev test test_coverage test_cov_missing lint lint_fix format build clean docs docs_clean docs_serve upload_pypi test_cov_combined test_cov_py312 test_cov_py38

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

test_cov_missing:
	@echo "Running tests with missing report coverage..."
	pytest --cov=ctxinject --cov-report=term-missing


# Run coverage for Python 3.8
test_cov_py38:
	@echo "Running coverage for Python 3.8..."
	@.venv38\Scripts\activate && coverage run --data-file=.coverage.py38 -m pytest --no-cov

# Run coverage for Python 3.12
test_cov_py312:
	@echo "Running coverage for Python 3.12..."
	@.venv\Scripts\activate && coverage run --data-file=.coverage.py312 -m pytest --no-cov

# Combine coverage from both Python versions
test_cov_combined:
	@echo "Running tests with coverage for Python 3.8..."
	@.venv38\Scripts\python -m coverage run --data-file=.coverage.py38 -m pytest --no-cov
	@echo ""
	@echo "Running tests with coverage for Python 3.12..."
	@.venv\Scripts\python -m coverage run --data-file=.coverage.py312 -m pytest --no-cov
	@echo ""
	@echo "Combining coverage data..."
	@coverage combine .coverage.py38 .coverage.py312
	@echo ""
	@echo "Combined coverage report:"
	@coverage report --show-missing
	@coverage html
	@echo ""
	@echo "HTML report generated in htmlcov/index.html"


lint:
	@echo "Running linter (ruff)..."
	ruff check .

lint_fix:
	@echo "Running linter --fix (ruff)..."
	ruff check --fix .

format:
	@echo "Formatting code (black e isort)..."
	black ctxinject
	isort ctxinject

clean:
	@echo "Cleaning cache and build/dist related files..."
	@python -c "import shutil, glob, os; [shutil.rmtree(d, ignore_errors=True) for d in ['dist', 'build', '.mypy_cache', '.pytest_cache', '.ruff_cache'] + glob.glob('*.egg-info')]; [shutil.rmtree(os.path.join(r, d), ignore_errors=True) for r, ds, _ in os.walk('.') for d in ds if d == '__pycache__']"

build: clean
	@echo "Building package ..."
	python -m build

upload_pypi: build
	@echo "Uploading package to pypi ..."
	twine upload dist/*
docs:
	@echo "Building documentation..."
	sphinx-build -b html docs/source docs/build/html

docs_clean:
	@echo "Cleaning documentation..."
	sphinx-build -M clean docs/source docs/build

docs_serve:
	@echo "Serving documentation locally at http://localhost:8000"
	@python -m http.server 8000 -d docs/build/html