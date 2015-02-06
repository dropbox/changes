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
	@echo "  docker                     build and run in a Docker container"
	@echo "    docker-container           build Docker container named '$(DOCKER_CONTAINER_NAME)'"
	@echo "    docker-image               build Docker image named '$(DOCKER_IMAGE_NAME)'"
	@echo "  docker-browse              connect via HTTP"
	@echo "    docker-browse-info         display information about how to connect via HTTP"
	@echo "  docker-ssh                 connect via ssh"
	@echo "    docker-ssh-info            display information about how to connect via ssh"
	@echo "  docker-destroy             remove Docker container named '$(DOCKER_CONTAINER_NAME)'"
	@echo "  docker-destroy-image       remove the Docker container, and image named '$(DOCKER_IMAGE_NAME)"
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
	npm cache clean
	npm install
	pip install pip==1.5.6
	pip install -e . --use-mirrors --allow-external=argparse

install-test-requirements: install-requirements
	pip install "file://`pwd`#egg=changes[tests]" --use-mirrors

test: lint test-python test-js

test-python:
	@echo "Running Python tests"
	py.test tests
	@echo ""

test-js:
	@echo "Running JavaScript tests"
	@npm run test
	@echo ""

lint: lint-js lint-python

lint-python:
	@echo "Linting Python files"
	@PYFLAKES_NODOCTEST=1 flake8 changes tests
	@echo ""

lint-js:
	@echo "Linting JavaScript files"
	@npm run lint
	@echo ""

test-full: install-test-requirements
	$(MAKE) lint
	$(MAKE) coverage
	@npm run test-ci

coverage:
	coverage run -m py.test --junitxml=python.junit.xml tests
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
	npm run compile-static

# Debian/Ubuntu name collision on /usr/bin/docker
# - https://bugs.debian.org/740863
# - https://bugs.debian.org/748526
DOCKER ?= $(shell which docker.io || which docker)

# These should not be identical, or random commands will fail with
# "Error: Conflict between containers and images"
DOCKER_IMAGE_NAME ?= local/changes
DOCKER_CONTAINER_NAME ?= changes-dev

DOCKER_ENV_FILE ?= $(HOME)/.changes/changes.docker-env.conf
DOCKER_ENV_EXAMPLE_FILE ?= docs/examples/changes.docker-env.conf

$(DOCKER_ENV_FILE):
	@echo "******************************************************************"
	@echo "You need to configure $(DOCKER_ENV_FILE)"
	@echo ""
	@echo "Start here:"
	@echo "  cp -f docs/examples/changes.docker-env.conf $(DOCKER_ENV_FILE)"
	@echo "  $(or $(VISUAL),$(EDITOR),nano) $(DOCKER_ENV_FILE)"
	@echo ""
	@echo "Then run this command again"
	@echo "******************************************************************"
	@exit 1

docker-quickstart: $(DOCKER_ENV_FILE)
	$(MAKE) docker
	$(MAKE) docker-browse
	$(MAKE) docker-ssh

docker: docker-container
	$(MAKE) docker-info

docker-browse:
	xdg-open $(shell $(MAKE) -s docker-browse-info) || open $(shell $(MAKE) -s docker-browse-info)

docker-browse-info:
	@$(DOCKER) inspect --format='http://localhost:{{(index (index .NetworkSettings.Ports "5000/tcp") 0).HostPort}}/' $(DOCKER_CONTAINER_NAME)

docker-ssh:
	$(shell $(MAKE) -s docker-ssh-info)

docker-ssh-info:
	@# See http://docs.docker.io/reference/commandline/cli/ for examples of how to use --format
	@$(DOCKER) inspect --format='ssh -p {{(index (index .NetworkSettings.Ports "22/tcp") 0).HostPort}} root@{{(index (index .NetworkSettings.Ports "22/tcp") 0).HostIp}}' $(DOCKER_CONTAINER_NAME)

docker-info:
	@$(MAKE) -s docker-ssh-info
	@$(MAKE) -s docker-browse-info

docker-container: docker-image $(DOCKER_ENV_FILE)
	$(DOCKER) run --detach --env-file $(DOCKER_ENV_FILE) \
		-p 127.0.0.1:5000:5000 -p 127.0.0.1::22 \
		--name $(DOCKER_CONTAINER_NAME) \
		$(DOCKER_IMAGE_NAME)

docker-image:
	$(DOCKER) build -t $(DOCKER_IMAGE_NAME) .

docker-destroy: docker-destroy-container
	@echo "Now run $(MAKE) docker-destroy-image if you also want to destroy the image"

docker-destroy-container:
	-$(DOCKER) rm -f $(DOCKER_CONTAINER_NAME)

docker-destroy-image: docker-destroy-container
	-$(DOCKER) rmi $(DOCKER_IMAGE_NAME)

# XXX(dlitz): We should have some real build products, too.
.PHONY: help develop upgrade setup-git \
	install-requirements install-test-requirements \
	test lint lint-python lint-js test-full coverage \
	dropdb createdb migratedb resetdb static \
	docker docker-container docker-image
