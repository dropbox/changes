define(['app', 'controllers/layout', 'controllers/changeList', 'controllers/changeDetails',
        'controllers/buildList', 'controllers/buildDetails', 'controllers/testDetails'], function(app) {
  'use strict';

  // TODO(dcramer): We need to load initial data as part of routes
  return app.config(['$routeProvider', '$httpProvider', '$locationProvider', function($routeProvider, $httpProvider, $locationProvider) {

    $locationProvider.html5Mode(true);

    $routeProvider
        .when('/', {
          templateUrl: 'partials/change-list.html',
          controller: 'changeListCtrl',
          resolve: {
            initialData: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/changes/');
            }]
          }
        })
        .when('/changes/:change_id/', {
          templateUrl: 'partials/change-details.html',
          controller: 'changeDetailsCtrl',
          resolve: {
            initialData: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/changes/' + $route.current.params.change_id + '/');
            }]
          }
        })
        .when('/builds/', {
          templateUrl: 'partials/build-list.html',
          controller: 'buildListCtrl',
          resolve: {
            initialData: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/builds/');
            }]
          }
        })
        .when('/builds/:build_id/', {
          templateUrl: 'partials/build-details.html',
          controller: 'buildDetailsCtrl',
          resolve: {
            initialData: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/builds/' + $route.current.params.build_id + '/');
            }]
          }
        })
        .when('/tests/:test_id/', {
          templateUrl: 'partials/test-details.html',
          controller: 'testDetailsCtrl',
          resolve: {
            initialData: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/tests/' + $route.current.params.test_id + '/');
            }]
          }
        })
        .otherwise({redirectTo: '/'});
  }]);
});
