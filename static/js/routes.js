define([
  'app',
  'routes/buildDetails',
  'routes/jobDetails',
  'controllers/layout',
  'controllers/authorBuildList',
  'controllers/changeList',
  'controllers/changeDetails',
  'controllers/buildList',
  'controllers/jobLogDetails',
  'controllers/jobPhaseList',
  'controllers/nodeDetails',
  'controllers/testGroupDetails',
  'controllers/planDetails',
  'controllers/planList',
  'controllers/projectBuildCreate',
  'controllers/projectBuildSearch',
  'controllers/projectCommitDetails',
  'controllers/projectCommitList',
  'controllers/projectCreate',
  'controllers/projectDetails',
  'controllers/projectList',
  'controllers/projectSettings',
  'controllers/projectTestDetails',
  'controllers/projectTestList',
  'controllers/projectSourceDetails',
  'directives/duration',
  'directives/radialProgressBar',
  'directives/timeSince',
  'filters/escape',
  'filters/truncate',
  'filters/wordwrap'
], function(app, BuildDetailsRoute, JobDetailsRoute) {

  'use strict';

  app.config(['$urlRouterProvider', '$httpProvider', '$locationProvider', '$stateProvider', '$uiViewScrollProvider',
            function($urlRouterProvider, $httpProvider, $locationProvider, $stateProvider, $uiViewScrollProvider) {
    // use html5 location rather than hashes
    $locationProvider.html5Mode(true);

    // send 404s to /
    $urlRouterProvider.otherwise("/projects/");

    // revert to default scrolling behavior as autoscroll is broken
    $uiViewScrollProvider.useAnchorScroll();

    // on a 401 (from the API) redirect the user to the login view
    var logInUserOn401 = ['$window', '$q', function($window, $q) {
        function success(response) {
            return response;
        }

        function error(response) {
            if(response.status === 401) {
                $window.location.href = '/auth/login/';
                return $q.reject(response);
            }
            else {
                return $q.reject(response);
            }
        }

        return function(promise) {
            return promise.then(success, error);
        };
    }];
    $httpProvider.responseInterceptors.push(logInUserOn401);

    $stateProvider
      .state('projects', {
        url: "/projects/",
        templateUrl: 'partials/project-list.html',
        controller: 'projectListCtrl',
        resolve: {
          initial: ['$http', function($http) {
            return $http.get('/api/0/projects/');
          }]
        }
      })
      .state('builds', {
        url: "/builds/",
        templateUrl: 'partials/build-list.html',
        controller: 'buildListCtrl',
        resolve: {
          initial: ['$q', '$location', '$http', function($q, $location, $http){
            var deferred = $q.defer(),
                filter = $location.search().filter || '',
                entrypoint = '/api/0/builds/';

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
      .state('build_details', BuildDetailsRoute)
      .state('job_details', JobDetailsRoute)
      .state('log_details', {
        url: 'logs/:source_id/',
        templateUrl: 'partials/job-log-details.html',
        controller: 'jobLogDetailsCtrl',
        parent: 'job_details',
        resolve: {
          initialBuildLog: ['$http', '$stateParams', function($http, $stateParams) {
            return $http.get('/api/0/jobs/' + $stateParams.job_id + '/logs/' + $stateParams.source_id + '?limit=0');
          }]
        }
      })
      .state('test_details', {
        url: 'tests/:testgroup_id/',
        templateUrl: 'partials/testgroup-details.html',
        controller: 'testGroupDetailsCtrl',
        parent: 'job_details',
        resolve: {
          initialData: ['$http', '$stateParams', function($http, $stateParams) {
            return $http.get('/api/0/testgroups/' + $stateParams.testgroup_id + '/');
          }]
        }
      })
      .state('builds_details_job_phases', {
        url: '/jobs/:job_id/phases/',
        templateUrl: 'partials/job-phase-list.html',
        controller: 'jobPhaseListCtrl',
        resolve: {
          initialJob: ['$http', '$stateParams', function($http, $stateParams) {
            return $http.get('/api/0/jobs/' + $stateParams.job_id + '/');
          }],
          initialPhaseList: ['$http', '$stateParams', function($http, $stateParams) {
            return $http.get('/api/0/jobs/' + $stateParams.job_id + '/phases/');
          }]
        }
      })
      .state('my_builds', {
        url: '/my/builds/',
        templateUrl: 'partials/author-build-list.html',
        controller: 'authorBuildListCtrl',
        resolve: {
          initialBuildList: ['$http', function($http) {
            return $http.get('/api/0/authors/me/builds/');
          }]
        }
      })
      .state('node', {
        url: '/nodes/:node_id/',
        templateUrl: 'partials/node-details.html',
        controller: 'nodeDetailsCtrl',
        resolve: {
          initialNode: ['$http', '$stateParams', function($http, $stateParams) {
            return $http.get('/api/0/nodes/' + $stateParams.node_id + '/');
          }],
          initialJobList: ['$http', '$stateParams', function($http, $stateParams) {
            return $http.get('/api/0/nodes/' + $stateParams.node_id + '/jobs/');
          }]
        }
      })
      .state('new_project', {
        url: '/new/project/',
        templateUrl: 'partials/project-create.html',
        controller: 'projectCreateCtrl'
      })
      .state('plans', {
        url: '/plans/',
        templateUrl: 'partials/plan-list.html',
        controller: 'planListCtrl',
        resolve: {
          initial: ['$http', function($http) {
            return $http.get('/api/0/plans/');
          }]
        }
      })
      .state('plans_details', {
        url: '/plans/:plan_id/',
        templateUrl: 'partials/plan-details.html',
        controller: 'planDetailsCtrl',
        resolve: {
          initial: ['$http', '$stateParams', function($http, $stateParams) {
            return $http.get('/api/0/plans/' + $stateParams.plan_id + '/');
          }]
        }
      })
      .state('projects_details', {
        url: '/projects/:project_id/',
        templateUrl: 'partials/project-details.html',
        controller: 'projectDetailsCtrl',
        resolve: {
          initialProject: ['$http', '$stateParams', function($http, $stateParams) {
            return $http.get('/api/0/projects/' + $stateParams.project_id + '/');
          }],
          initialBuildList: ['$http', '$stateParams', function($http, $stateParams) {
            return $http.get('/api/0/projects/' + $stateParams.project_id + '/builds/?include_patches=0');
          }]
        }
      })
      .state('project_new_build', {
        url: '/projects/:project_id/new/build/',
        templateUrl: 'partials/project-build-create.html',
        controller: 'projectBuildCreateCtrl',
        resolve: {
          initialProject: ['$http', '$stateParams', function($http, $stateParams) {
            return $http.get('/api/0/projects/' + $stateParams.project_id + '/');
          }]
        }
      })
      .state('project_search', {
        url: '/projects/:project_id/search/',
        templateUrl: 'partials/project-build-list.html',
        controller: 'projectBuildSearchCtrl',
        resolve: {
          initialProject: ['$http', '$stateParams', function($http, $stateParams) {
            return $http.get('/api/0/projects/' + $stateParams.project_id + '/');
          }],
          initialBuildList: ['$http', '$stateParams', '$window', function($http, $stateParams, $window) {
            return $http.get('/api/0/projects/' + $stateParams.project_id + '/builds/search/' + $window.location.search);
          }]
        }
      })
      .state('project_commits', {
        url: '/projects/:project_id/commits/',
        templateUrl: 'partials/project-commit-list.html',
        controller: 'projectCommitListCtrl',
        resolve: {
          initialProject: ['$http', '$stateParams', function($http, $stateParams) {
            return $http.get('/api/0/projects/' + $stateParams.project_id + '/');
          }],
          initialCommitList: ['$http', '$stateParams', '$window', function($http, $stateParams, $window) {
            return $http.get('/api/0/projects/' + $stateParams.project_id + '/commits/' + $window.location.search);
          }]
        }
      })
      .state('project_commit_details', {
        url: '/projects/:project_id/commits/:commit_id/',
        templateUrl: 'partials/project-commit-details.html',
        controller: 'projectCommitDetailsCtrl',
        resolve: {
          initialProject: ['$http', '$stateParams', function($http, $stateParams) {
            return $http.get('/api/0/projects/' + $stateParams.project_id + '/');
          }],
          initialCommit: ['$http', '$stateParams', '$window', function($http, $stateParams, $window) {
            return $http.get('/api/0/projects/' + $stateParams.project_id + '/commits/' + $stateParams.commit_id + '/' + $window.location.search);
          }]
        }
      })
      .state('project_settings', {
        url: '/projects/:project_id/settings/',
        templateUrl: 'partials/project-settings.html',
        controller: 'projectSettingsCtrl',
        resolve: {
          initialProject: ['$http', '$stateParams', function($http, $stateParams) {
            return $http.get('/api/0/projects/' + $stateParams.project_id + '/');
          }]
        }
      })
      .state('project_tests', {
        url: '/projects/:project_id/tests/',
        templateUrl: 'partials/project-test-list.html',
        controller: 'projectTestListCtrl',
        resolve: {
          initialProject: ['$http', '$stateParams', function($http, $stateParams) {
            return $http.get('/api/0/projects/' + $stateParams.project_id + '/');
          }],
          initialTests: ['$http', '$stateParams', '$window', function($http, $stateParams, $window) {
            return $http.get('/api/0/projects/' + $stateParams.project_id + '/tests/' + $window.location.search);
          }]
        }
      })
      .state('project_tests_details', {
        urls: '/projects/:project_id/tests/:test_id/',
        templateUrl: 'partials/project-test-details.html',
        controller: 'projectTestDetailsCtrl',
        resolve: {
          initialProject: ['$http', '$stateParams', function($http, $stateParams) {
            return $http.get('/api/0/projects/' + $stateParams.project_id + '/');
          }],
          initialTest: ['$http', '$stateParams', '$window', function($http, $stateParams, $window) {
            return $http.get('/api/0/projects/' + $stateParams.project_id + '/tests/' + $stateParams.test_id + '/' + $window.location.search);
          }]
        }
      })
      .state('project_source', {
        url: '/projects/:project_id/sources/:source_id/',
        templateUrl: 'partials/project-source-details.html',
        controller: 'projectSourceDetailsCtrl',
        resolve: {
          initialProject: ['$http', '$stateParams', function($http, $stateParams) {
            return $http.get('/api/0/projects/' + $stateParams.project_id + '/');
          }],
          initialSource: ['$http', '$stateParams', '$window', function($http, $stateParams, $window) {
            return $http.get('/api/0/projects/' + $stateParams.project_id + '/sources/' + $stateParams.source_id + '/');
          }],
          initialBuildList: ['$http', '$stateParams', '$window', function($http, $stateParams, $window) {
            return $http.get('/api/0/projects/' + $stateParams.project_id + '/sources/' + $stateParams.source_id + '/builds/');
          }]
        }
      });
  }]);
});
