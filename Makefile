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

.PHONY: check_tag_version
check_tag_version:
	python3 -c "import sys, os; \
		from grablib.version import VERSION; \
		os.getenv('TRAVIS_TAG') not in (None, '', str(VERSION)) and sys.exit(1)"
