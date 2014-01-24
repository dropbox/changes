define(['app',
        'controllers/layout',
        'controllers/authorBuildList',
        'controllers/changeList',
        'controllers/changeDetails',
        'controllers/buildList',
        'controllers/buildDetails',
        'controllers/jobDetails',
        'controllers/jobLogDetails',
        'controllers/jobPhaseList',
        'controllers/nodeDetails',
        'controllers/testGroupDetails',
        'controllers/projectCommitDetails',
        'controllers/projectCommitList',
        'controllers/projectDetails',
        'controllers/projectLeaderboard',
        'controllers/projectList',
        'controllers/projectSettings',
        'controllers/projectTestDetails',
        'controllers/projectTestList',
        'controllers/projectSourceDetails'
       ], function(app) {

  'use strict';

  // TODO(dcramer): We need to load initial data as part of routes
  return app.config([
      '$routeProvider', '$httpProvider', '$locationProvider',
      function($routeProvider, $httpProvider, $locationProvider) {

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
                  filter = $location.search().filter || '',
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
                .success(function(data, status, headers){
                  deferred.resolve({
                    'data': data,
                    'status': status,
                    'headers': headers,
                    'entrypoint': entrypoint
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
        .when('/jobs/:job_id/', {
          templateUrl: 'partials/job-details.html',
          controller: 'jobDetailsCtrl',
          resolve: {
            initialData: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/jobs/' + $route.current.params.job_id + '/');
            }]
          }
        })
        .when('/jobs/:job_id/phases/', {
          templateUrl: 'partials/job-phase-list.html',
          controller: 'jobPhaseListCtrl',
          resolve: {
            initialJob: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/jobs/' + $route.current.params.job_id + '/');
            }],
            initialPhaseList: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/jobs/' + $route.current.params.job_id + '/phases/');
            }]
          }
        })
        .when('/jobs/:job_id/logs/:source_id/', {
          templateUrl: 'partials/job-log-details.html',
          controller: 'jobLogDetailsCtrl',
          resolve: {
            initialJob: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/jobs/' + $route.current.params.job_id + '/');
            }],
            initialBuildLog: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/jobs/' + $route.current.params.job_id + '/logs/' + $route.current.params.source_id + '?limit=0');
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
        .when('/nodes/:node_id/', {
          templateUrl: 'partials/node-details.html',
          controller: 'nodeDetailsCtrl',
          resolve: {
            initialNode: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/nodes/' + $route.current.params.node_id + '/');
            }],
            initialJobList: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/nodes/' + $route.current.params.node_id + '/jobs/');
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
        .when('/projects/:project_id/commits/:commit_id/', {
          templateUrl: 'partials/project-commit-details.html',
          controller: 'projectCommitDetailsCtrl',
          resolve: {
            initialProject: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/projects/' + $route.current.params.project_id + '/');
            }],
            initialCommit: ['$http', '$route', '$window', function($http, $route, $window) {
              return $http.get('/api/0/projects/' + $route.current.params.project_id + '/commits/' + $route.current.params.commit_id + '/' + $window.location.search);
            }]
          }
        })
        .when('/projects/:project_id/settings/', {
          templateUrl: 'partials/project-settings.html',
          controller: 'projectSettingsCtrl',
          resolve: {
            initialProject: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/projects/' + $route.current.params.project_id + '/');
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
        .when('/projects/:project_id/tests/', {
          templateUrl: 'partials/project-test-list.html',
          controller: 'projectTestListCtrl',
          resolve: {
            initialProject: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/projects/' + $route.current.params.project_id + '/');
            }],
            initialTests: ['$http', '$route', '$window', function($http, $route, $window) {
              return $http.get('/api/0/projects/' + $route.current.params.project_id + '/tests/' + $window.location.search);
            }]
          }
        })
        .when('/projects/:project_id/tests/:test_id/', {
          templateUrl: 'partials/project-test-details.html',
          controller: 'projectTestDetailsCtrl',
          resolve: {
            initialProject: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/projects/' + $route.current.params.project_id + '/');
            }],
            initialTest: ['$http', '$route', '$window', function($http, $route, $window) {
              return $http.get('/api/0/projects/' + $route.current.params.project_id + '/tests/' + $route.current.params.test_id + '/' + $window.location.search);
            }]
          }
        })
        .when('/projects/:project_id/sources/:source_id/', {
          templateUrl: 'partials/project-source-details.html',
          controller: 'projectSourceDetailsCtrl',
          resolve: {
            initialProject: ['$http', '$route', function($http, $route) {
              return $http.get('/api/0/projects/' + $route.current.params.project_id + '/');
            }],
            initialSource: ['$http', '$route', '$window', function($http, $route, $window) {
              return $http.get('/api/0/projects/' + $route.current.params.project_id + '/sources/' + $route.current.params.source_id + '/');
            }],
            initialBuildList: ['$http', '$route', '$window', function($http, $route, $window) {
              return $http.get('/api/0/projects/' + $route.current.params.project_id + '/sources/' + $route.current.params.source_id + '/builds/');
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
