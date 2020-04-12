.DEFAULT_GOAL := all
isort = isort -rc grablib tests
black = black -S -l 120 --target-version py37 grablib tests

.PHONY: install
install:
	pip install -U pip
	pip install .[build]
	pip install -r tests/requirements.txt

.PHONY: format
format:
	$(isort)
	$(black)

.PHONY: lint
lint:
	python setup.py check -rms
	flake8 grablib/ tests/
	$(isort) --check-only -df
	$(black) --check

.PHONY: test
test:
	pytest --cov=grablib

.PHONY: testcov
testcov:
	pytest --cov=grablib
	@echo "building coverage html"
	@coverage html

.PHONY: all
all: lint testcov
