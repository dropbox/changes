define(['app',
        'controllers/layout',
        'controllers/authorBuildList',
        'controllers/changeList',
        'controllers/changeDetails',
        'controllers/buildList',
        'controllers/buildLogDetails',
        'controllers/buildDetails',
        'controllers/testGroupDetails',
        'controllers/projectCommitList',
        'controllers/projectLeaderboard',
        'controllers/projectList',
        'controllers/projectDetails'
       ], function(app) {

  'use strict';

  // TODO(dcramer): We need to load initial data as part of routes
  return app.config(['$routeProvider', '$httpProvider', '$locationProvider', function($routeProvider, $httpProvider, $locationProvider) {

    $locationProvider.html5Mode(true);

    $routeProvider
        .when('/', {
          templateUrl: 'partials/project-list.html',
          controller: 'projectListCtrl',
          resolve: {
            initial: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/projects/');
            }]
          }
        })
        .when('/changes/', {
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
            initial: ['$q', '$route', '$location', '$http', function($q, $route, $location, $http){
              var deferred = $q.defer(),
                  filter = $location.search()['filter'] || '',
                  entrypoint;

              if ($route.current.params.change_id) {
                // TODO: handle me filter
                entrypoint = '/api/0/changes/' + $route.current.params.change_id + '/builds/';
              } else {
                if (filter === 'me') {
                  entrypoint = '/api/0/authors/me/builds/';
                } else {
                  entrypoint = '/api/0/builds/';
                }
              }

              $http.get(entrypoint)
                .success(function(data){
                  deferred.resolve({
                    'data': data,
                    'entrypoint': entrypoint,
                  });
                })
                .error(function(){
                  deferred.reject();
                });

              return deferred.promise;
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
        .when('/builds/:build_id/logs/:source_id/', {
          templateUrl: 'partials/build-log-details.html',
          controller: 'buildLogDetailsCtrl',
          resolve: {
            initialBuild: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/builds/' + $route.current.params.build_id + '/');
            }],
            initialBuildLog: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/builds/' + $route.current.params.build_id + '/logs/' + $route.current.params.source_id + '?limit=0');
            }]
          }
        })
        .when('/my/builds/', {
          templateUrl: 'partials/author-build-list.html',
          controller: 'authorBuildListCtrl',
          resolve: {
            initialBuildList: ['$http', function($http) {
              return $http.get('/api/0/authors/me/builds/');
            }]
          }
        })
        .when('/projects/:project_id/', {
          templateUrl: 'partials/project-details.html',
          controller: 'projectDetailsCtrl',
          resolve: {
            initialProject: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/projects/' + $route.current.params.project_id + '/');
            }],
            initialBuildList: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/projects/' + $route.current.params.project_id + '/builds/?include_patches=0');
            }]
          }
        })
        .when('/projects/:project_id/commits/', {
          templateUrl: 'partials/project-commit-list.html',
          controller: 'projectCommitListCtrl',
          resolve: {
            initialProject: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/projects/' + $route.current.params.project_id + '/');
            }],
            initialCommitList: ['$http', '$route', '$window', function($http, $route, $window) {
              return $http.get('/api/0/projects/' + $route.current.params.project_id + '/commits/' + $window.location.search);
            }]
          }
        })
        .when('/projects/:project_id/stats/', {
          templateUrl: 'partials/project-stats.html',
          controller: 'projectLeaderboardCtrl',
          resolve: {
            initialProject: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/projects/' + $route.current.params.project_id + '/');
            }],
            initialStats: ['$http', '$route', '$window', function($http, $route, $window) {
              return $http.get('/api/0/projects/' + $route.current.params.project_id + '/stats/' + $window.location.search);
            }]
          }
        })
        .when('/testgroups/:testgroup_id/', {
          templateUrl: 'partials/testgroup-details.html',
          controller: 'testGroupDetailsCtrl',
          resolve: {
            initialData: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/testgroups/' + $route.current.params.testgroup_id + '/');
            }]
          }
        })
        .otherwise({redirectTo: '/'});
  }]);
});
