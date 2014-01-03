.PHONY: static

develop: install-requirements
	alembic upgrade head

install-requirements: update-submodules
	npm install
	bower install
	pip install -e . --use-mirrors --no-use-wheel
	make install-test-requirements

install-test-requirements:
	pip install "file://`pwd`#egg=changes[tests]" --use-mirrors --no-use-wheel

update-submodules:
	git submodule init
	git submodule update

test: install-requirements lint
	@echo "Running Python tests"
	py.test tests
	@echo ""

lint: lint-js lint-python

lint-python:
	@echo "Linting Python files"
	@PYFLAKES_NODOCTEST=1 flake8 changes tests
	@echo ""

lint-js:
	@echo "Linting JavaScript files"
	@node_modules/.bin/jshint static/
	@echo ""

test-full: install-requirements lint
	py.test --junitxml=results.xml --cov-report=xml --cov=. tests

resetdb:
	dropdb --if-exists changes
	createdb -E utf-8 changes
	alembic upgrade head

static:
	r.js -o build.js
