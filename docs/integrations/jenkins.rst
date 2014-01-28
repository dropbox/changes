Jenkins Integration
===================

Changes integrates extremely with Jenkins as a build manager, however it will require you to have a very specialized job for running a build.


Creating the Job
----------------

Your job will need to accept the following string parameters:

- REVISION
- CHANGES_BID
- PATCH_URL

The build itself should consist of steps:

1. Fetching the revision (and optionally fetching the repository if needed)
2. Applying the patch if present
3. Running tests
4. Archiving artifacts (via a post-build action)

Example scripts based on git are included for reference. Note that REPO_PATH is a global variables that is assumed to exist.

Fetching the Revision
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

	#!/bin/bash -eux

	if [ ! -d $REPO_PATH/.git ]; then
		git clone $REPO_URL $REPO_PATH
		pushd $REPO_PATH
	else
		pushd $REPO_PATH && git fetch --all
		git remote prune origin
	fi

	git clean -fdx

	if ! git reset --hard $REVISION ; then
		git reset --hard origin/master
		echo "Failed to update to $REVISION, falling back to master"
	fi


Applying the Patch
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

	#!/bin/bash -eux

	WORKSPACE_DIR=$(pwd)

	pushd $REPO_PATH
	if [ ! -z "${PATCH_URL:-}" ]; then
		curl -o ${WORKSPACE_DIR}/PATCH $PATCH_URL
		git apply ${WORKSPACE_DIR}/PATCH
	fi


Running Tests
~~~~~~~~~~~~~

This step is arbitrary based on your platform. In Python this might be something like:

.. code-block:: bash

	py.test --junit=junit.xml


Archiving Artifacts
~~~~~~~~~~~~~~~~~~~

You'll need to ensure artifacts are archived via a post-build step. Changes can aggregate these results in two ways:

1. If Jenkins is setup to output a test result, the artifacts do not need to be archived
2. If the artifact is named "junit.xml", it will automatically get picked up.
