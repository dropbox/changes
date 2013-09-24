Setup
-----

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
------------

You can generate sample data by running the following:

::

	python generate_data.py

.. note:: This will wipe all existing data!


Webserver
---------

Run the webserver:

::

	buildbox-web
