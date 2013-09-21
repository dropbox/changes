develop: update-submodules install-test-requirements
	pip install -q -e . --use-mirrors

install-test-requirements:
	pip install -q "file://`pwd`#egg=buildbox[tests]" --use-mirrors

update-submodules:
	git submodule init
	git submodule update

test: develop lint
	@echo "Running Python tests"
	python setup.py -q test || exit 1
	@echo ""

lint:
	@echo "Linting Python files"
	PYFLAKES_NODOCTEST=1 flake8 buildbox tests
	@echo ""

test-full: develop lint
	py.test --junitxml=results.xml --cov-report=xml --cov=.
