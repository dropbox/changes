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

    # ~/.changes/changes.conf.py
    BASE_URI = 'http://localhost:5000'
    SERVER_NAME = 'localhost:5000'

    REPO_ROOT = '/tmp'

    # You can obtain these values via the Google Developers Console:
    # https://console.developers.google.com/
    GOOGLE_CLIENT_ID = None
    GOOGLE_CLIENT_SECRET = None


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

::

    [program:changes-web]
    command=/srv/changes/env/bin/uwsgi --http 127.0.0.1:50%(process_num)02d --processes 1 --threads 10 --log-x-forwarded-for --buffer-size 32768 --post-buffering 65536 --need-app --disable-logging -w changes.app:app
    user=ubuntu
    environment=CHANGES_CONF="/srv/changes/config.py",PATH="/srv/changes/env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:"
    process_name=%(program_name)s_%(process_num)02d
    numprocs=4
    autorestart=true
    killasgroup=true
    stopasgroup=true
    directory=/srv/changes
    redirect_stderr=true
    stdout_logfile=/tmp/%(program_name)s_%(process_num)02d.log

    [program:changes-worker]
    command=/srv/changes/env/bin/celery -A changes.app:celery worker -c 96 --without-mingle
    user=ubuntu
    environment=CHANGES_CONF="/srv/changes/config.py",PATH="/srv/changes/env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:"
    directory=/srv/changes
    autorestart=true
    killasgroup=true
    stopasgroup=true
    redirect_stderr=true
    stdout_logfile=/tmp/%(program_name)s_%(process_num)02d.log

For more details you'll want to refer to the `supervisord documentation <http://supervisord.org/configuration.html#program-x-section-settings>`_.
