Jenkins Integration
===================

Changes integrates extremely with Jenkins as a build manager, however it will require you to have a very specialized job for running a build.

Creating the Job
----------------

This changes rapidly and documentation is not maintained for the internals of the generic job.

.. literalinclude:: /examples/jenkins-generic-job.xml
   :language: xml
   :emphasize-lines: 96-99

Example scripts based on git are included for reference. Note that REPO_PATH is a global variable that is assumed to exist.
The reset-generic job here is an optional, sample downstream job that can be run to execute cleanup tasks passed through the RESET_SCRIPT parameter.
Running cleanup tasks outside the generic job has the advantage of not delaying build results from the generic job being posted back to Changes.


Master Build Step
~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/generic-build-step
   :language: bash


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
