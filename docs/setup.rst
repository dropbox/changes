Setup Guide
===========


Getting the Source Code
-----------------------

Use the git, Luke!

.. code-block:: bash

    $ git clone https://github.com/dropbox/changes.git


Installing Dependencies
-----------------------

We're going to assume you're running OS X, otherwise you're on your own.

.. code-block:: bash

    $ brew install node libev libxml2 libxslt python

Install Postgres (ensure you follow whatever instructions are given post-install):

.. code-block:: bash

    $ brew install postgresql

Install Redis (ensure you follow whatever instructions are given post-install):

.. code-block:: bash

    $ brew install redis

Next up, we need Bower for JavaScript dependencies:

.. code-block:: bash

    $ npm install -g bower

And finally let's make sure we have virtualenv for our Python environment:

.. code-block:: bash

    $ pip install --upgrade virtualenv


Configure the Environment
-------------------------

Create the database in Postgres:

.. code-block:: bash

    $ createdb -E utf-8 changes

Setup the default configuration:

.. code-block:: python

    .. literalinclude:: examples/changes.conf.py

Create a Python environment:

.. code-block:: bash

    # set cwd to repo root
    $ cd /path/to/changes

    # create a base environment
    $ virtualenv env

    # "active" the environment, so python becomes localized
    $ source env/bin/activate

Bootstrap your environment:

.. code-block:: bash

    # fix for Xcode 5.1
    $ export ARCHFLAGS=-Wno-error=unused-command-line-argument-hard-error-in-future

    # install basic dependencies (npm, bower, python)
    $ make develop

    # perform any data migrations
    $ make upgrade


Take a glance at the `Makefile <https://github.com/dropbox/changes/blob/master/Makefile>`_ for
more details on what commands are available, and what actually gets executed.


Installing Services
-------------------

You're going to need to run several services in the background. Specifically, you'll need both the webserver and the workers running. To do this we recommend using `supervisord <http://supervisord.org/>`_.

Below is a sample configuration for both the web and worker processes:

    .. literalinclude:: examples/supervisord.conf

For more details you'll want to refer to the `supervisord documentation <http://supervisord.org/configuration.html#program-x-section-settings>`_.
