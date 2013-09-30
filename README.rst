Changes
-------

Setup
=====

Create an environment:

::

	mkvirtualenv buidlbox


Install dependencies:

::

	make

Setup Postgers:

::

	createdb -E utf-8

Apply migrations:

::

	alembic upgrade head

Fixture Data
============

You can generate sample data by running the following:

::

	python generate_data.py

.. note:: This will wipe all existing data!


Webserver
=========

Run the webserver:

::

	changes-web


API
===

List Changes
~~~~~~~~~~~

::

	GET /api/0/changes/


Change Details
~~~~~~~~~~~~~

::

	GET /api/0/changes/:change_id/


List Builds
~~~~~~~~~~~

::

	GET /api/0/changes/:change_id/builds/


Create Build
~~~~~~~~~~~~

::

	POST /api/0/changes/:change_id/builds/

**Params**

project:
	the project ID

sha:
	the base revision sha to build on

(optional) patch:
	git unified diff format

(optional) patch[label]:
	a human readable label for this patch
	**must be specified if patch is present**

(optional) patch[url]:
	a url which describes this patch

**Response**

::

	{
		"build": {
			"id": "a857d7dc0d9843cfa568cfbd0b0de91c"
		}
	}
