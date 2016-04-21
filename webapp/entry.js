/* WARNING:  This is NOT as ES6 file. So no =>, `str`, or other conveniences */

// some RequireJS config before we start.
requirejs.config({

  // IMPORTANT NOTE: if you add something here, update the Gruntfile
  // 'compile2' task

  paths: {
    // all of our code is written in jsx/es6 syntax and converted using babel
    babel: "vendor/requirejs-babel/babel-4.6.6.min",
    classnames: 'vendor/classnames/index',
    es6: "vendor/requirejs-babel/es6", // the requirejs babel loader
    // time library
    moment: "vendor/moment/min/moment.min",
    // some extra react components
    react_bootstrap: 'vendor/react-bootstrap/react-bootstrap',
    // core libraries we use
    react: 'vendor/react/react-with-addons',
    requirejs: 'vendor/requirejs/require',
    underscore: 'vendor/underscore/underscore',
    // library to deal with URIs. Per github repo, this version is published
    // under a pure MIT license (despite the gpl v3 reference.)
    uriJS: 'vendor/uri.js/src'
  },
  config: {
    'es6': {
      'optional': ['es7.objectRestSpread'],
    }
  },
  shim: {
    underscore: {
      exports: '_'
    },
  },

  // Increase the require.js load timeout threshold, since the ES6 compilation
  // step in development mode often exceeds the 7-second default threshold.
  waitSeconds: 15
});

/*
 * essentially main(). Routes the user to the right page
 */

require([
  "react",
  "underscore",
  "uriJS/URI",
  "es6!server/api",
  "es6!utils/custom_content",
  "es6!utils/utils",
  "es6!display/changes/links",
  // requiring every page. It doesn't matter that much in prod since we bundle,
  // and we want to avoid dynamic module loading
  "es6!pages/home_page",
  "es6!pages/admin_page",
  "es6!pages/admin_project_page",
  "es6!pages/admin_repository_page",
  "es6!pages/infra_fails_page",
  "es6!pages/task_tree_page",
  "es6!pages/jobstep_summary_page",
  "es6!pages/project_page/project_page",
  "es6!pages/author_builds_page",
  "es6!pages/builds_pages/builds_pages",
  "es6!pages/tests_for_build_page",
  "es6!pages/test_history_page",
  "es6!pages/log_page",
  "es6!pages/all_projects_page",
  "es6!pages/node_page",
  "es6!pages/snapshot_page",
  "es6!pages/code_page",
  "es6!pages/pusher_page",
  "es6!pages/examples_page",
  "es6!pages/fourohfour_page",
], function(
  React,
  _,
  URI,
  data_fetching,
  custom_content_hook,
  utils,
  ChangesLinks,

  HomePage,
  AdminPage,
  AdminProjectPage,
  AdminRepositoryPage,
  InfraFailsPage,
  TaskTreePage,
  JobstepSummaryPage,
  ProjectPage,
  AuthorBuildsPage,
  buildsPages,
  buildTestsPages,
  TestHistoryPage,
  LogPage,
  AllProjectsPage,
  NodePage,
  SnapshotPage,
  CodePage,
  PusherPage,
  DisplayExamplesPage,
  FourOhFourPage
) {
  'use strict';

  // for some reason, import statements aren't working for the URI library
  // TODO: figure out why
  window.URI = URI;

  var CommitPage = buildsPages.CommitPage;
  var DiffPage = buildsPages.DiffPage;
  var SingleBuildPage = buildsPages.SingleBuildPage;

  var BuildTestsPage = buildTestsPages.BuildTestsPage;
  var SingleBuildTestPage = buildTestsPages.SingleBuildTestPage;

  // routing
  // TODO: all of this is terrible and temporary just to get something working.
  // replace with a routing library. Probably not react-router, though... its
  // too template-y. Or at least don't use nesting with react-router

  var path = window.location.pathname;
  var path_parts = _.compact(path.split('/'));

  // Strip the leading /v2/ if it exists
  if (path_parts[0] == 'v2') {
    path_parts.shift();
  }

  // We want to ensure that certain changes classic style links still work.
  if (path_parts.length > 3 && path_parts[0] === 'projects' && path_parts[2] == 'builds') {
    var build_id = path_parts[3];
    if (path_parts.indexOf('tests') > 3)
      path_parts = ['build_tests', build_id];
    // for /projects/<slug>/builds/<build_id>/jobs/<job_id>/logs/<log_id>
    else if (path_parts.length == 8 && path_parts[4] == 'jobs' && path_parts[6] == 'logs')
      path_parts = ['job_log', build_id, path_parts[5], path_parts[7]];
    else
      path_parts = ['find_build', build_id];
  }

  if (path_parts[0] === 'find_build') {
    var redirect_func = function(response, was_success) {
      if (!was_success) {
        document.write('Redirect failed');
        return;
      }
      var build = JSON.parse(response.responseText);
      var new_href = URI(ChangesLinks.buildHref(build))
        .addSearch('optin', 1);
      window.location.href = new_href;
    }
    data_fetching.make_api_ajax_get('/api/0/builds/' + path_parts[1], null,
      redirect_func, redirect_func);

    return;
  }

  var url_contains = {
    'projects': [AllProjectsPage],
    'project': [ProjectPage, 'projectSlug'],
    'author_builds': [AuthorBuildsPage, 'author'],
    'commit_source': [CommitPage, 'sourceUUID'],
    'diff': [DiffPage, 'diff_id'],
    'single_build': [SingleBuildPage, 'buildID'],
    'build_test': [SingleBuildTestPage, 'buildID', 'testID'],
    'build_tests': [BuildTestsPage, 'buildID'],
    'project_test': [TestHistoryPage, 'projectUUID', 'testHash'],
    'job_log': [LogPage, 'buildID', 'jobID', 'logsourceID'],
    'author': [HomePage, 'author'],  // TODO: don't just use the homepage
    'node': [NodePage, 'nodeID'],
    'snapshot': [SnapshotPage, 'snapshotID'],
    'infra_fails': [InfraFailsPage],
    'task_tree': [TaskTreePage, 'objectID'],
    'jobstep_summary': [JobstepSummaryPage],
    'code': [CodePage, 'sourceID'],
    'pusher': [PusherPage],
    'display_examples': [DisplayExamplesPage],
    'admin': [AdminPage],
    'admin_project': [AdminProjectPage, 'projectSlug'],
    'admin_repository': [AdminRepositoryPage, 'repositoryID'],
  };

  var page = FourOhFourPage;

  // Redirect projects/foo -> project/foo because
  // v1 project pages used the plural form
  if (path_parts[0] === 'projects' && path_parts.length > 1) {
    path_parts[0] = 'project';
  }

  var params = {};
  for (var str in url_contains) {
    if (path_parts[0] === str) {
      var page_data = url_contains[str];
      page = page_data[0];
      if (page_data.length > 1) {
        if (path_parts.length < page_data.length) {
          // path doesn't have enough parts...
          page = FourOhFourPage;
          params['badUrl'] = true;
          break;
        }
        for (var i = 1; i < page_data.length; i++) {
          params[page_data[i]] = path_parts[i];
        }
      }
      break;
    }
  }

  if (path_parts.length === 0) { page = HomePage; }

  // we fetch some initial data used by pages (e.g. are we logged in?)
  data_fetching.make_api_ajax_get('/api/0/initial/', null, function(response) {
    var parsedResponse = JSON.parse(response.responseText);

    // TODO: use context?
    window.changesAuthData = parsedResponse['auth'];
    window.changesMessageData = parsedResponse['admin_message'];

    // require user to be logged in
    if (!window.changesAuthData || !window.changesAuthData.user) {
      // disabled on the project page for now so that people can create
      // dashboards
      var unauthOKPages = ['project', 'pusher'];
      var unauthOK = _.any(unauthOKPages, function(path) {
        return path_parts[0] === path
      });

      if (!unauthOK) {
         // if WEBAPP_USE_ANOTHER_HOST, we can't redirect to login. Tell the
         // user to do it themselves
         if (window.changesGlobals['USE_ANOTHER_HOST']) {
           document.getElementById('reactRoot').innerHTML = '<div>' +
             'We want to redirect you to login, but API calls are using ' +
             'a different server (WEBAPP_USE_ANOTHER_HOST). Go to that ' +
             'server and log in.' +
             '</div>';
           return;
         }

         var current_location = encodeURIComponent(window.location.href);
         var login_href = '/auth/login/?orig_url=' + current_location;

         console.log("User not identified - redirecting to login");
         window.location.href = login_href;
         return;
      }
    }

    // add custom css class if present
    var custom_css = custom_content_hook('rootClass', '');
    var root_classes = (
      "reactRoot " +
      (document.getElementById('reactRoot').className || '') + " " +
      custom_css
    ).trim();
    document.getElementById('reactRoot').className = root_classes

    var pageElem = React.render(
      React.createElement(page, params),
      document.getElementById('reactRoot')
    );

    var initialTitle = pageElem.getInitialTitle && pageElem.getInitialTitle();

    if (initialTitle) {
      utils.setPageTitle(initialTitle);
    }
  });
});

