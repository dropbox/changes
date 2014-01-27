Changes
-------

Changes is a dashboard to view information about your code. Specifically, it focuses on aggregating quality metrics and history, such as results from a build server.

Supported build platforms include:

- `Koality <http://koalitycode.com>`_
- `Jenkins <http://jenkins-ci.org>`_

Requirements
============

- Node.js
  - Bower (npm install -g bower)
- Postgresql
- Python 2.7
  - virtualenv
  - pip

Setup
=====

Create the database:

::

	$ createdb -E utf-8 changes

Setup the default configuration:

::

	# ~/.changes/changes.conf.py
	BASE_URI = 'http://localhost:5000'
	SERVER_NAME = 'localhost:5000'

	REPO_ROOT = '/tmp'

	# Changes only supports Google Auth, so you'll need to obtain tokens
    GOOGLE_CLIENT_ID = None
    GOOGLE_CLIENT_SECRET = None



Create a Python environment:

::

	$ mkvirtualenv changes

Bootstrap your environment:

::

	$ make upgrade


.. note:: You can run ``make resetdb`` to drop and re-create a clean database.


Webserver
=========

Run the webserver:

::

	bin/web


Background Workers
==================

Workers are managed via Celery:

::

	bin/worker -B

.. note:: In development you can set ``CELERY_ALWAYS_EAGER`` to run the queue in-process. You likely don't want this if you're synchronizing builds as it can cause recursion errors.


NGINX Configuration
===================

::

	    location / {
	        proxy_pass              http://changes_server;
	        proxy_set_header        Host $host;
	        proxy_set_header        X-Real-IP $remote_addr;
	        proxy_set_header        X-Forwarded-For $proxy_add_x_forwarded_for;
	        proxy_set_header        X-Forwarded-Proto $scheme;
	        proxy_connect_timeout   150;
	        proxy_send_timeout      100;
	        proxy_read_timeout      100;
	        proxy_buffers           4 32k;
	        proxy_buffering	        off;
	        client_max_body_size    8m;
	        client_body_buffer_size 128k;
	    }


Architecture
============

Top level, we have a few key concepts:

Repository:
  Exactly what it sounds like. git or hg
Project:
  A project belongs to a single repository, and may only describe a subsection of the repository.
Plan:
  A build plan. Plans belong to many projects.
Step:
  An individual step in a plan.

Within each project, we have a few things relevant to builds:

Source:
  Generally either a commit or a patch (for diff testing).
Change:
  A change is discrete changeset throughout its lifecycle. It may consist of several sources, such as an initial patch, a commit, a revert, a followup patch, and a followup commit.
Build:
  A build is a collection of jobs bound to a single source. Think of the build as the collective matrix of jobs for an individual change. e.g. you may want to test "Windows" and "Linux", which would both be contained within the same grouping.
Job:
  An individual job within a build. e.g. "Linux"
Job Plan:
  A snapshot of the plan at the time a job is created.

Inside of each job, a few items exist for collecting and reporting results:

Job Step:
  An individual step run as part of a job. For example, this could be the provision step.
Job Phase:
  A grouping of steps at the same tier. If you're using job factories, you may have several steps that execute similar tasks. These steps are grouped together as a phase.
Tests:
  Several types of models exist for reporting tests. These exist both on the per-build level, as well as per-project for aggregate results.
