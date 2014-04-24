Contributing to Changes
=======================

To get started, either get a job at Dropbox, or sign our CLA:

https://opensource.dropbox.com/cla/

Getting the Source Code
-----------------------

Use the git, Luke!

.. code-block:: bash

    $ git clone https://github.com/dropbox/changes.git


Setting up an Environment
-------------------------

You'll need to ensure you have a few dependencies:

- Node.js

  - Bower (npm install -g bower)

- Postgresql

- Redis

- Python 2.7

  - virtualenv

  - pip


Bootstrapping
~~~~~~~~~~~~~

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

    $ mkvirtualenv changes

Bootstrap your environment:

.. code-block:: bash

    # install basic dependencies (npm, bower, python)
    $ make develop

    # perform any data migrations
    $ make upgrade


Take a glance at the `Makefile <https://github.com/dropbox/changes/blob/master/Makefile>`_ for
more details on what commands are available, and what actually gets executed.


Webserver
~~~~~~~~~

Run the webserver:

.. code-block:: bash

    $ bin/web

.. note:: The server doesn't automatically reload when you make changes to the Python code.


Background Workers
~~~~~~~~~~~~~~~~~~

While it's likely you won't need to actually run the workers, they're managed via `Celery <http://www.celeryproject.org/>`_.

.. code-block:: bash

    # Start a generic worker process
    # the -B flag indicates to also start "celerybeat" which
    # is utilized for periodic tasks.
    $ bin/worker -B

.. note:: In development you can set ``CELERY_ALWAYS_EAGER=True`` to run the queue tasks synchronously in-process. Generally we prefer to test throughs through automated integration tests, but this is useful if you want to QA and don't want to run several processes.


Directory Layout
----------------

While there are a significant and growing number of paths, this is an attempt to outline some of the more common and important code paths.

.. code-block:: bash

    # command line scripts
    ├── bin

    # python code
    ├── changes

    # the core of url registration and app configuration
    │   ├── config.py

    # api controllers and serializers
    │   ├── api

    # various integration code (primarily for communicating with Jenkins)
    │   ├── backends

    # database utilities
    │   ├── db

    # tasks executed asynchronously via Celery workers
    │   ├── jobs

    # our sqlalchemy model definitions
    │   ├── models

    # integration code for mercurial/git
    │   └── vcs


    # python test bootstrap code
    ├── conftest.py

    # docs, like what you're reading right now
    ├── docs

    # database migrations (via Alembic)
    ├── migrations

    # client-side templates
    ├── partials

    # static media (such as the frontend code, as well as vendored code within)
    ├── static
    │   ├── css
    │   ├── js
    │   └── vendor

    # server-side templates
    ├── templates

    # all tests (only python currently)
    └── tests


Understanding the Frontend
--------------------------

Everything is bundled into a "state". A state is a combination of a router and a controller, and it contains nearly all of the logic for rendering an individual page.

States are registered into `routes.js <https://github.com/dropbox/changes/blob/master/static/js/routes.js>`_ (they get required and then registered to a unique name).

As an example, let's take a look at `planList.js <https://github.com/dropbox/changes/blob/master/static/js/states/planList.js>`_,
a fairly simple state:

.. code-block:: javascript

    // static/js/states/planList.js
    define(['app'], function(app) {
      'use strict';

      return {
        // parent is used for template/scope inheritance
        parent: 'layout',

        // the url **relative** to the parent
        // in our case, layout is the parent which has no base url
        url: '/plans/',

        // all templates exist in partials/
        templateUrl: 'partials/plan-list.html',

        // $scope, planList, and Collection are all dependencies, implicitly
        // parsed by angular and included in the function's scope
        controller: function($scope, planList, Collection) {
          // binding to $scope adds it to the template context
          $scope.plans = new Collection($scope, planList);
        },

        // resolvers get executed **before** the controller is run and
        // are ideal for loading initial data
        resolve: {
          planList: function($http) {
            // this **must** return a future
            return $http.get('/api/0/plans/').then(function(response){
                return response.data;
            });
          }
        }
      };
    });


Then within `routes.js <https://github.com/dropbox/changes/blob/master/static/js/routes.js>`_,
we register this under the 'plan_list' namespace:

.. code-block:: javascript

    // static/js/routes.js
    define([
      'app',
      'states/layout',
      // ...
      'states/planList'
    ], function(
      // the order of dependencies must match above
      app,
      LayoutState,
      // ...
      PlanListState
    ) {
      // this has been simplified for illustration purposes
      app.config(function($stateProvider) {
      $stateProvider
        .state('layout', LayoutState)
        // ...
        .state('plan_list', PlanListState);
    });


Let's take a look at the template, `plan-list.html <https://github.com/dropbox/changes/blob/master/partials/plan-list.html>`_:

.. code-block:: html

    <!-- partials/plan-list.html -->
    <section ui-view>
        <div id="overview">
            <div class="page-header">
                <h2>Build Plans</h2>
            </div>

            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Plan</th>
                        <th style="width:150px;text-align:center">Created</th>
                        <th style="width:150px;text-align:center">Modified</th>
                    </tr>
                </thead>
                <tbody>
                    <tr ng-repeat="plan in plans">
                        <td><a ui-sref="plan_details({plan_id: plan.id})">{{plan.name}}</a></td>
                        <td style="text-align:center" time-since="plan.dateCreated"></td>
                        <td style="text-align:center" time-since="plan.dateModified"></td>
                    </tr>
                </tbody>
            </table>
        </div>
    </section>


There's a few key things to understand in this simple example:

.. code-block:: html

    <section ui-view>


The ui-view attribute here is what Angular calls a directive. In this case, it actually maps to the library we use (ui-router) and says "content within this can be replaced by the child template". That's not precisely the meaning, but for our examples it's close enough.

Jumping down to actual rendering:

.. code-block:: html

    <tr ng-repeat="plan in plans">


This is another built-in directive, and it says "expand 'plans', and assign the item at the current index to 'plan'".

We can then reference it:

.. code-block:: html

        <td><a ui-sref="plan_details({plan_id: plan.id})">{{plan.name}}</a></td>


Two things are happening here:

- We're specifying ui-sref, which is saying "find the named url with these parameters". Parameters are always inherited, so you only need to pass in the changed values.

  - In our specific example, we're referring to the ``plan_details`` state, which might be a child page of ``plan_list``. This is the same name you would define in the ``.state()`` registration.

  - We also need to pass the ``plan_id`` parameter, which is used by the state's url matcher, and then made available via ``$stateParams`` within it's controller.

- Render the ``name`` attribute of this plan.


There's also a couple uses of our `timeSince.js <https://github.com/dropbox/changes/blob/master/static/js/directives/timeSince.js>`_ directive:

.. code-block:: html

        <td style="text-align:center" time-since="plan.dateCreated"></td>


In most uses of directives, you'll notice that we don't surround the value with ``{{ }}``. This is because the
directive itself is choosing to evaluate the value as part of the scope.

Understanding the Backend
-------------------------

The backend is a fairly straightforward Flask app. It has two primary models: task execution and consumer API.

We're not going to explain the workers as they contain a very large amount of coordination logic, but instead let's focus on the API.

To start with, the entry point for URLs currently lives in ``config.py``, under ``configure_api_routes``. You'll see that each API controller lives in a separate module space and is registered into the routing here.

Let's take a look at the API controller for our ``plan_list`` state, contained in
`plan_index.py <https://github.com/dropbox/changes/blob/master/changes/api/plan_index.py>`_:

.. code-block:: python

    # changes/api/plan_index.py
    from __future__ import absolute_import, division, unicode_literals

    from changes.api.base import APIView
    from changes.models import Plan


    class PlanIndexAPIView(APIView):
        def get(self):
            results = Plan.query.order_by(Plan.label.asc())[:10]

            # while respond() can serialize for you, we use this for illustration
            # purposes
            data = self.serialize(results)

            return self.respond(data, serialize=False)


There's no real surprises here if you've ever written Python. We're using SQLAlchemy to query the ``Plan`` table, and we're returning a simple result of ten plans.

There are two things happening here:

- We're serializing the list of Plans using the default registered serializer (dig
  into the `serializer https://github.com/dropbox/changes/blob/master/changes/api/serializer/models/plan.py>`_ to see what this does.)

- ``respond()`` is then going to return an HTTP response object, with a 200 status code
  any required headers, as well as eventually encode our Python object into JSON.

And of course, we absolutely require integration tests for every endpoint, which live
in `test_plan_index.py <https://github.com/dropbox/changes/blob/master/tests/changes/api/test_plan_index.py>`_:

.. code-block:: python

    from changes.testutils import APITestCase


    class PlanIndexTest(APITestCase):
        path = '/api/0/plans/'

        def test_simple(self):
            plan1 = self.plan
            plan2 = self.create_plan(label='Bar')

            resp = self.client.get(self.path)
            assert resp.status_code == 200
            data = self.unserialize(resp)
            assert len(data) == 2
            assert data[0]['id'] == plan2.id.hex
            assert data[1]['id'] == plan1.id.hex


A ``client`` attribute exists on the test instance, as well as a number of helpers in `changes.testutils.fixtures <https://github.com/dropbox/changes/blob/master/changes/testutils/fixtures.py>`_ for creating mock data. This is a real database transaction so you can do just about everything, and we'll safely ensure things are cleaned up and fast.


Loading in Mock Data
--------------------

If you're changing the frontend, it's likely you're going to want some data to work with. We've provided a helper script which will create some sample data, as well as stream in continuous updates. It's not quite the same as production, but it should be enough to work with:

.. code-block:: bash

    $ python stream_data.py
