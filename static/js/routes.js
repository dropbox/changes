define([
  'app',

  'states/authorBuildList',
  'states/buildDetails',
  'states/jobDetails',
  'states/layout',
  'states/logDetails',
  'states/nodeDetails',
  'states/planDetails',
  'states/planList',
  'states/projectBuildList',
  'states/projectBuildSearch',
  'states/projectCommitDetails',
  'states/projectCommitList',
  'states/projectCreate',
  'states/projectCreateBuild',
  'states/projectDetails',
  'states/projectList',
  'states/projectSettings',
  'states/projectSourceDetails',
  'states/projectTestDetails',
  'states/projectTestList',
  'states/testGroupDetails',

  'directives/duration',
  'directives/radialProgressBar',
  'directives/timeSince',
  'filters/escape',
  'filters/truncate',
  'filters/wordwrap'
], function(
  app,

  AuthorBuildListState,
  BuildDetailsState,
  JobDetailsState,
  LayoutState,
  LogDetailsState,
  NodeDetailsState,
  PlanDetailsState,
  PlanListState,
  ProjectBuildListState,
  ProjectBuildSearchState,
  ProjectCommitDetailsState,
  ProjectCommitListState,
  ProjectCreateState,
  ProjectCreateBuildState,
  ProjectDetailsState,
  ProjectListState,
  ProjectSettingsState,
  ProjectSourceDetailsState,
  ProjectTestDetailsState,
  ProjectTestListState,
  TestGroupDetailsState
) {

  'use strict';

  app.config(function($urlRouterProvider, $httpProvider, $locationProvider, $stateProvider, $uiViewScrollProvider) {
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
      .state('layout', LayoutState)
      .state('build_details', BuildDetailsState)
      .state('job_details', JobDetailsState)
      .state('log_details', LogDetailsState)
      .state('test_details', TestGroupDetailsState)
      .state('my_builds', AuthorBuildListState)
      .state('node', NodeDetailsState)
      .state('new_project', ProjectCreateState)
      .state('plans', PlanListState)
      .state('plan_details', PlanDetailsState)
      .state('projects', ProjectListState)
      .state('project_builds', ProjectBuildListState)
      .state('project_details', ProjectDetailsState)
      .state('project_new_build', ProjectCreateBuildState)
      .state('project_search', ProjectBuildSearchState)
      .state('project_commits', ProjectCommitListState)
      .state('project_commit_details', ProjectCommitDetailsState)
      .state('project_settings', ProjectSettingsState)
      .state('project_tests', ProjectTestListState)
      .state('project_tests_details', ProjectTestDetailsState)
      .state('project_source', ProjectSourceDetailsState);
  });
});
