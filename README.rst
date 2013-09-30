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

Setup Postgres:

::

	createdb -E utf-8 changes

Apply migrations:

::

	alembic upgrade head

.. note:: You can simply run ``make resetdb`` to drop and re-create a clean database.


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


Create Change
~~~~~~~~~~~~~

::

	POST /api/0/changes/

**Params**

project:
	the project ID

label:
	a label for this change

(optional) key:
	a unique identifier for this change (e.g. D1234)

(optional) sha:
	the committed revision's sha

(optional) author:
	the author of this change (e.g. "David Cramer <dcramer@example.com>")


**Response**

::

	{
		"build": {
			"id": "a857d7dc0d9843cfa568cfbd0b0de91c"
		}
	}


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

(optional) author:
	the author of this build (e.g. "David Cramer <dcramer@example.com>")

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
