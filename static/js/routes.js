define(['app', 'controllers/layout', 'controllers/changeList', 'controllers/changeDetails',
        'controllers/buildList', 'controllers/buildDetails', 'controllers/testDetails'], function(app) {
  'use strict';

  // TODO(dcramer): We need to load initial data as part of routes
  return app.config(['$routeProvider', '$locationProvider', function($routeProvider, $locationProvider) {

    $locationProvider.html5Mode(true);

    $routeProvider
        .when('/', {
          templateUrl: 'partials/change-list.html',
          controller: 'changeListCtrl'
        })
        .when('/changes/:change_id/', {
          templateUrl: 'partials/change-details.html',
          controller: 'changeDetailsCtrl'
        })
        .when('/builds/', {
          templateUrl: 'partials/build-list.html',
          controller: 'buildListCtrl'
        })
        .when('/builds/:build_id/', {
          templateUrl: 'partials/build-details.html',
          controller: 'buildDetailsCtrl'
        })
        .when('/tests/:test_id/', {
          templateUrl: 'partials/test-details.html',
          controller: 'testDetailsCtrl'
        })
        .otherwise({redirectTo: '/'});
  }]);
});
