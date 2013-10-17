define(['app', 'controllers/layout', 'controllers/changeList', 'controllers/changeDetails', 'controllers/buildList', 'controllers/buildDetails'], function(app) {
  'use strict';

  // TODO(dcramer): We need to load initial data as part of routes
  return app.config(['$routeProvider', '$locationProvider', function($routeProvider, $locationProvider) {

    $locationProvider.html5Mode(true);

    $routeProvider
        .when('/', {
          templateUrl: 'partials/change-list.html',
          controller: 'changeListCtrl'
        })
        .when('/projects/:project_id/changes/:change_id/', {
          templateUrl: 'partials/change-details.html',
          controller: 'changeDetailsCtrl'
        })
        .when('/projects/:project_id/changes/:change_id/builds/:build_id/', {
          templateUrl: 'partials/build-details.html',
          controller: 'buildDetailsCtrl'
        })
        .when('/builds/', {
          templateUrl: 'partials/build-list.html',
          controller: 'buildListCtrl'
        })
        .otherwise({redirectTo: '/'});
  }]);
});
