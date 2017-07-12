.DEFAULT_GOAL := all

.PHONY: install
install:
	pip install -U pip
	pip install .[build]
	pip install -r tests/requirements.txt

.PHONY: isort
isort:
	isort -rc -w 120 grablib
	isort -rc -w 120 tests

.PHONY: lint
lint:
	python setup.py check -rms
	flake8 grablib/ tests/
	pytest grablib -p no:sugar -q --cache-clear

.PHONY: test
test:
	py.test --cov=grablib

.PHONY: testcov
testcov:
	py.test --cov=grablib && (echo "building coverage html"; coverage html)

.PHONY: all
all: testcov lint
