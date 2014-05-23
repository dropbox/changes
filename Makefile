.PHONY: static

develop: install-requirements install-test-requirements setup-git

upgrade: develop
	alembic upgrade head
	make static

setup-git:
	git config branch.autosetuprebase always
	cd .git/hooks && ln -sf ../../hooks/* ./

install-requirements: update-submodules
	npm install
	bower install
	pip install -e . --use-mirrors --allow-external=argparse

install-test-requirements:
	pip install "file://`pwd`#egg=changes[tests]" --use-mirrors

update-submodules:
	git submodule init
	git submodule update

test: lint
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

test-full: install-requirements install-test-requirements lint
	coverage run -m py.test --junitxml=junit.xml tests
	coverage xml

resetdb:
	dropdb --if-exists changes
	createdb -E utf-8 changes
	alembic upgrade head

static:
	node_modules/.bin/grunt requirejs
