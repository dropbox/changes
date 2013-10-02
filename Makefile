.PHONY: static

develop: update-submodules
	npm install
	bower install
	pip install -q -e . --use-mirrors
	make install-test-requirements

install-test-requirements:
	pip install -q "file://`pwd`#egg=changes[tests]" --use-mirrors

update-submodules:
	git submodule init
	git submodule update

test: develop lint
	@echo "Running Python tests"
	python setup.py -q test || exit 1
	@echo ""

lint:
	@echo "Linting Python files"
	PYFLAKES_NODOCTEST=1 flake8 changes tests
	@echo ""

test-full: develop lint
	py.test --junitxml=results.xml --cov-report=xml --cov=.

resetdb:
	dropdb --if-exists changes
	createdb -E utf-8 changes
	alembic upgrade head

static:
	r.js -o build.js
