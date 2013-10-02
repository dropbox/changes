define(['app', 'controllers/changeList', 'controllers/changeDetails', 'controllers/buildList', 'controllers/buildDetails'], function(app) {
  'use strict';

  // TODO(dcramer): We need to load initial data as part of routes
  return app.config(['$routeProvider', function($routeProvider) {
    $routeProvider
        .when('/', {
          templateUrl: 'partials/change-list.html',
          // resolve: {
          //   apiResponse: function($http) {
          //     return $http.get('/api/0/changes/');
          //   }
          // },
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
        .otherwise({redirectTo: '/'});
  }]);
});
