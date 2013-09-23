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


Webserver
---------

Run the webserver:

::

	buildbox-web
