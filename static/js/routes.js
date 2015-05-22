define([
  'app',

  'states/adminHome',
  'states/adminLayout',
  'states/adminMessageDetails',
  'states/adminMessageList',
  'states/adminProjectCreate',
  'states/adminProjectDetails',
  'states/adminProjectList',
  'states/adminProjectPlanCreate',
  'states/adminProjectPlanDetails',
  'states/adminProjectPlanList',
  'states/adminProjectSettings',
  'states/adminProjectSnapshotList',
  'states/adminRepositoryCreate',
  'states/adminRepositoryDetails',
  'states/adminRepositoryList',
  'states/adminRepositoryProjectList',
  'states/adminUserDetails',
  'states/adminUserList',
  'states/authorBuildList',
  'states/buildDetails',
  'states/buildTestList',
  'states/clusterDetails',
  'states/clusterList',
  'states/fourohfour',
  'states/jobArtifactList',
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
  'states/projectSourceDetails',
  'states/projectTestDetails',
  'states/projectTestList',
  'states/projectTestSearch',
  'states/taskDetails',
  'states/taskList',
  'states/testCaseDetails',

  'directives/bindOnce',
  'directives/buildCommentList',
  'directives/commitInfo',
  'directives/duration',
  'directives/prettyJson',
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
  AdminMessageDetailsState,
  AdminMessageListState,
  AdminProjectCreateState,
  AdminProjectDetailsState,
  AdminProjectListState,
  AdminProjectPlanCreateState,
  AdminProjectPlanDetailsState,
  AdminProjectPlanListState,
  AdminProjectSettingsState,
  AdminProjectSnapshotListState,
  AdminRepositoryCreateState,
  AdminRepositoryDetailsState,
  AdminRepositoryListState,
  AdminRepositoryProjectListState,
  AdminUserDetailsState,
  AdminUserListState,
  AuthorBuildListState,
  BuildDetailsState,
  BuildTestListState,
  ClusterDetailsState,
  ClusterListState,
  FourOhFourState,
  JobArtifactListState,
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

    // homepage is projects/
    $urlRouterProvider.when("", "/projects/");
    $urlRouterProvider.when("/", "/projects/");

    // send 404s to /
    $urlRouterProvider.otherwise(function ($injector, $location) {
      var url = $location.url();
      // either angular or ui-router automagically unencodes standard 
      // url escaping :/. Use base64 instead, replacing /s
      var encoded_url = btoa(url).replace("/", "-");
      return "/404/" + encoded_url;
    });

    // urls without trailing slashes should go to the right place. newer 
    // versions of angular-ui-router have a strictMode parameter that does 
    // this, but at the time this comment was written said parameter didn't
    // work 100% (it broke for urls that included query parameters, like
    // projectBuildList.js.) It also would require us to rewrite all of our 
    // links to not end in a trailing slash.
    //
    // This code snippet is provided by the angular-ui-router documentation.
    // It doesn't handle urls with hashbangs or urls like www.site.com/page.html
    // https://github.com/angular-ui/ui-router/wiki/Frequently-Asked-Questions
    //   #how-to-make-a-trailing-slash-optional-for-all-routes
    $urlRouterProvider.rule(function ($injector, $location) {
      var url = $location.url();

      // check to see if the url already has a slash where it should be
      if (url[url.length - 1] === '/' || url.indexOf('/?') > -1) {
        return;
      }

      if (url.indexOf('?') > -1) {
        return url.replace('?', '/?');
      }

      return url + '/';
    });

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

    $httpProvider.interceptors.push(['$window', '$q', function($window, $q) {
      return {
        'request' : function(config) {
          if ($window.DEV_JS_SHOULD_HIT_HOST) {
            // for safety, default behavior is to only redirect non-post 
            // api calls
            var is_get = config.method.toLowerCase() === 'get';
            if (is_get && (config.url.indexOf("api/0/") !== -1)) {
              config.url = ($window.DEV_JS_SHOULD_HIT_HOST +
                (config.url.charAt(0) === '/' ? '' : '/') +
                config.url);
            }
          }
          return config;
        },
        'response' : function(response) {
          return response;
        }
      };
    }]);

    // Base routes
    $stateProvider
      .state('layout', LayoutState)
      .state('build_details', BuildDetailsState)
      .state('build_test_list', BuildTestListState)
      .state('cluster_details', ClusterDetailsState)
      .state('clusters', ClusterListState)
      .state('fourohfour', FourOhFourState)
      .state('job_details', JobDetailsState)
      .state('job_artifact_list', JobArtifactListState)
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
      .state('admin_message_details', AdminMessageDetailsState)
      .state('admin_message_list', AdminMessageListState)
      .state('admin_project_create', AdminProjectCreateState)
      .state('admin_project_details', AdminProjectDetailsState)
      .state('admin_project_settings', AdminProjectSettingsState)
      .state('admin_project_list', AdminProjectListState)
      .state('admin_project_plan_list', AdminProjectPlanListState)
      .state('admin_project_plan_details', AdminProjectPlanDetailsState)
      .state('admin_project_plan_create', AdminProjectPlanCreateState)
      .state('admin_project_snapshot_list', AdminProjectSnapshotListState)
      .state('admin_repository_list', AdminRepositoryListState)
      .state('admin_repository_create', AdminRepositoryCreateState)
      .state('admin_repository_details', AdminRepositoryDetailsState)
      .state('admin_repository_project_list', AdminRepositoryProjectListState)
      .state('admin_user_list', AdminUserListState)
      .state('admin_user_details', AdminUserDetailsState);
  });
});
