Contributing to Changes
=======================

To get started, either get a job at Dropbox, or sign our CLA:

https://opensource.dropbox.com/cla/

Getting the Source Code
-----------------------

Use the git, Luke!

::

    git clone https://github.com/dropbox/changes.git


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

Create the database:

::

    $ createdb -E utf-8 changes

Setup the default configuration:

::

    # this should live in ~/.changes/changes.conf.py
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
~~~~~~~~~

Run the webserver:

::

    bin/web

.. note:: The server doesn't automatically reload when you make changes to the Python code.


Background Workers
~~~~~~~~~~~~~~~~~~

While it's likely you won't need to actually run the workers, they're managed via Celery:

::

    bin/worker -B

.. note:: In development you can set ``CELERY_ALWAYS_EAGER`` to run the queue in-process. You likely don't want this if you're synchronizing builds as it can cause recursion errors.


Directory Layout
----------------

::

    # command line scripts
    ├── bin

    # python code
    ├── changes

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

States are registered into routes.js (they get required and then registered to a unique name).

A state in it's simplest form, looks something like this:

::

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

        // $scope, planList, and Collection are all dependencies, implicitly parsed
        // by angular and included in the function's scope
        controller: function($scope, planList, Collection) {
          // binding to $scope means its available via reference in the template
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

Then within routes.js, we register this under the 'plan_list' namespace:

::

    // static/js/routes.js
    .route('plan_list', PlanListState)

Digging into the template a little bit:

::

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

::

    <section ui-view>

The ui-view attribute here is what Angular calls a directive. In this case, it actually maps to the library we use (ui-router) and says "content within this can be replaced by the child template". That's not precisely the meaning, but for our examples its close enough.

Jumping down to actual rendering:

::

    <tr ng-repeat="plan in plans">

This is another built-in directive, and it says "expand 'plans', and assign the item at the current index to 'plan'".

We can then reference it:

::

        <td><a ui-sref="plan_details({plan_id: plan.id})">{{plan.name}}</a></td>

Two things are happening here:

- We're specifying ui-sref, which is saying "find the named url with these parameters". Parameters are always inherited, so you only need to pass in the changed values.

- Render the ``name`` attribute of this plan.


Understanding the Backend
-------------------------

The backend is a fairly straightforward Flask app. It has two primary models: task execution and consumer API.

We're not going to explain the workers as they contain a very large amount of coordination logic, but instead let's focus on the API.

To start with, the entry point for URLs currently lives in ``config.py``, under ``configure_api_routes``. You'll see that each API controller lives in a separate module space and is registered into the routing here.

Let's take a look at the API controller for our ``plan_list`` state:

::

    # changes/api/plan_index.py
    from __future__ import absolute_import, division, unicode_literals

    from changes.api.base import APIView
    from changes.models import Plan


    class PlanIndexAPIView(APIView):
        def get(self):
            queryset = Plan.query.order_by(Plan.label.asc())
            return self.paginate(queryset)


There's no real surprises here if you've ever written Python. We're using SQLAlchemy to query the ``Plan`` table, and we're returning a paginated response.

There are a couple of things happening under the hood here:

- ``paginate`` is actually aware that we're passing it a queryset and its returning a ``Link`` header with any applicable paging data. Of note, our plan list example above isn't actually handling pagination correctly.

- ``paginate`` actually calls out to ``respond`` eventually, which will then call out to our default serializers. Serializers exist to automatically transform certain types into native Python objects, which then eventually get coerced to JSON.

And of course, we absolutely require integration tests for every endpoint:

::

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


A ``client`` attribute exists on the test instance, as well as a number of helpers in ``changes.testutils.fixtures`` for creating mock data. This is a real database transaction so you can do just about everything, and we'll safely ensure things are cleaned up and fast.


Loading in Mock Data
--------------------

If you're changing the frontend, it's likely you're going to want some data to work with. We've provided a helper script which will create some sample data, as well as stream in continuous updates. It's not quite the same as production, but it should be enough to work with:

::

    python stream_data.py
