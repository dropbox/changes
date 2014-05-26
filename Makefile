help:
	@echo "Please use \`$(MAKE) <target>' where <target> is one of the following:"
	@echo "  setup-git                  optional git config & pre-commit hooks"
	@echo "  develop                    perform inital development setup"
	@echo "    install-requirements       install basic deps (npm, bower, python)"
	@echo "    install-test-requirements  install runtime + testing dependencies"
	@echo "  upgrade                    perform data migrations"
	@echo "    install-requirements       (see above)"
	@echo "    migratedb                  migrate the database schema"
	@echo "    static                     update static assets (generate css, js)"
	@echo "  test                       run the unit tests"
	@echo "    lint                       inspect code for errors"
	@echo "      lint-js                    run jshint"
	@echo "      lint-python                run flake8"
	@echo "  test-full                  run the full test suite and make a coverage report"
	@echo "    install-test-requirements  (see above)"
	@echo "    lint                       (see above)"
	@echo "    coverage                   produce a coverage report"
	@echo "  resetdb                    drop and re-create the database"
	@echo "    dropdb                     drop the database"
	@echo "    createdb                   create an empty database"
	@echo "    migratedb                  migrate the database schema"
	@echo ""
	@echo "For help building documentation, run:"
	@echo "  $(MAKE) -C docs help"

# Works like "python setup.py develop"
develop: install-requirements install-test-requirements

upgrade: install-requirements
	@# XXX: Can `migratedb' and `static' run in parallel?
	$(MAKE) migratedb
	$(MAKE) static

setup-git:
	git config branch.autosetuprebase always
	cd .git/hooks && ln -sf ../../hooks/* ./

install-requirements:
	@# XXX: Can any of these run in parallel?
	npm install
	bower install
	pip install -e . --use-mirrors --allow-external=argparse

install-test-requirements: install-requirements
	pip install "file://`pwd`#egg=changes[tests]" --use-mirrors

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

test-full: install-test-requirements
	$(MAKE) lint
	$(MAKE) coverage

coverage:
	coverage run -m py.test --junitxml=junit.xml tests
	coverage xml

dropdb:
	dropdb --if-exists changes

createdb:
	createdb -E utf-8 changes

migratedb:
	alembic upgrade head

resetdb:
	$(MAKE) dropdb
	$(MAKE) createdb
	$(MAKE) migratedb

static:
	node_modules/.bin/grunt requirejs

# XXX(dlitz): We should have some real build products, too.
.PHONY: help develop upgrade setup-git \
	install-requirements install-test-requirements \
	test lint lint-python lint-js test-full coverage \
	dropdb createdb migratedb resetdb static
