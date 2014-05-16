define([
  'app',

  'states/authorBuildList',
  'states/buildDetails',
  'states/buildTestList',
  'states/jobDetails',
  'states/jobPhaseList',
  'states/layout',
  'states/logDetails',
  'states/nodeDetails',
  'states/nodeList',
  'states/planCreate',
  'states/planDetails',
  'states/planList',
  'states/projectBuildList',
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
  'states/projectTestSearch',
  'states/taskDetails',
  'states/testCaseDetails',

  'directives/bindOnce',
  'directives/duration',
  'directives/renderBuildRow',
  'directives/timeSince',
  'filters/escape',
  'filters/buildEstimatedProgress',
  'filters/truncate',
  'filters/wordwrap'
], function(
  app,

  AuthorBuildListState,
  BuildDetailsState,
  BuildTestListState,
  JobDetailsState,
  JobPhaseListState,
  LayoutState,
  LogDetailsState,
  NodeDetailsState,
  NodeListState,
  PlanCreateState,
  PlanDetailsState,
  PlanListState,
  ProjectBuildListState,
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
  ProjectTestSearchState,
  TaskDetailsState,
  TestCaseDetailsState
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
      .state('build_test_list', BuildTestListState)
      .state('job_details', JobDetailsState)
      .state('job_phase_list', JobPhaseListState)
      .state('log_details', LogDetailsState)
      .state('my_builds', AuthorBuildListState)
      .state('nodes', NodeListState)
      .state('node_details', NodeDetailsState)
      .state('new_plan', PlanCreateState)
      .state('new_project', ProjectCreateState)
      .state('plans', PlanListState)
      .state('plan_details', PlanDetailsState)
      .state('projects', ProjectListState)
      .state('project_builds', ProjectBuildListState)
      .state('project_details', ProjectDetailsState)
      .state('project_new_build', ProjectCreateBuildState)
      .state('project_commits', ProjectCommitListState)
      .state('project_commit_details', ProjectCommitDetailsState)
      .state('project_settings', ProjectSettingsState)
      .state('project_tests', ProjectTestListState)
      .state('project_test_details', ProjectTestDetailsState)
      .state('project_test_search', ProjectTestSearchState)
      .state('project_source_details', ProjectSourceDetailsState)
      .state('test_details', TestCaseDetailsState)
      .state('task_details', TaskDetailsState);
  });
});
