#!/bin/bash -ex

source ~/env/bin/activate
make test-full

ci/mypy-run
