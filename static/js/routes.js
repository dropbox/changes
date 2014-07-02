define([
  'app',

  'states/adminHome',
  'states/adminLayout',
  'states/adminPlanCreate',
  'states/adminPlanDetails',
  'states/adminPlanList',
  'states/adminProjectCreate',
  'states/adminProjectList',
  'states/adminRepositoryList',
  'states/authorBuildList',
  'states/buildDetails',
  'states/buildTestList',
  'states/clusterDetails',
  'states/clusterList',
  'states/jobDetails',
  'states/jobPhaseList',
  'states/layout',
  'states/logDetails',
  'states/nodeDetails',
  'states/nodeList',
  'states/projectBuildList',
  'states/projectCommitDetails',
  'states/projectCommitList',
  'states/projectCoverageList',
  'states/projectCreateBuild',
  'states/projectDetails',
  'states/projectList',
  'states/projectSettings',
  'states/projectSourceDetails',
  'states/projectTestDetails',
  'states/projectTestList',
  'states/projectTestSearch',
  'states/taskDetails',
  'states/taskList',
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

  AdminHomeState,
  AdminLayoutState,
  AdminPlanCreateState,
  AdminPlanDetailsState,
  AdminPlanListState,
  AdminProjectCreateState,
  AdminProjectListState,
  AdminRepositoryListState,
  AuthorBuildListState,
  BuildDetailsState,
  BuildTestListState,
  ClusterDetailsState,
  ClusterListState,
  JobDetailsState,
  JobPhaseListState,
  LayoutState,
  LogDetailsState,
  NodeDetailsState,
  NodeListState,
  ProjectBuildListState,
  ProjectCommitDetailsState,
  ProjectCommitListState,
  ProjectCoverageListState,
  ProjectCreateBuildState,
  ProjectDetailsState,
  ProjectListState,
  ProjectSettingsState,
  ProjectSourceDetailsState,
  ProjectTestDetailsState,
  ProjectTestListState,
  ProjectTestSearchState,
  TaskDetailsState,
  TaskListState,
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

    // Base routes
    $stateProvider
      .state('layout', LayoutState)
      .state('build_details', BuildDetailsState)
      .state('build_test_list', BuildTestListState)
      .state('cluster_details', ClusterDetailsState)
      .state('clusters', ClusterListState)
      .state('job_details', JobDetailsState)
      .state('job_phase_list', JobPhaseListState)
      .state('log_details', LogDetailsState)
      .state('my_builds', AuthorBuildListState)
      .state('nodes', NodeListState)
      .state('node_details', NodeDetailsState)
      .state('projects', ProjectListState)
      .state('project_builds', ProjectBuildListState)
      .state('project_details', ProjectDetailsState)
      .state('project_new_build', ProjectCreateBuildState)
      .state('project_commits', ProjectCommitListState)
      .state('project_commit_details', ProjectCommitDetailsState)
      .state('project_coverage', ProjectCoverageListState)
      .state('project_settings', ProjectSettingsState)
      .state('project_tests', ProjectTestListState)
      .state('project_test_details', ProjectTestDetailsState)
      .state('project_test_search', ProjectTestSearchState)
      .state('project_source_details', ProjectSourceDetailsState)
      .state('test_details', TestCaseDetailsState)
      .state('tasks', TaskListState)
      .state('task_details', TaskDetailsState);

    // Admin routes
    $stateProvider
      .state('admin_layout', AdminLayoutState)
      .state('admin_home', AdminHomeState)
      .state('admin_project_create', AdminProjectCreateState)
      .state('admin_project_list', AdminProjectListState)
      .state('admin_plan_list', AdminPlanListState)
      .state('admin_plan_create', AdminPlanCreateState)
      .state('admin_plan_details', AdminPlanDetailsState)
      .state('admin_repository_list', AdminRepositoryListState);
  });
});
