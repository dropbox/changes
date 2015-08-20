/* some RequireJS config before we start */

requirejs.config({
  // NOTE: if you add something here, update the Gruntfile 'compile2' task
  paths: {
    // all of our code is written in jsx/es6 syntax and converted using babel
    babel: "vendor/requirejs-babel/babel-4.6.6.min",
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
  }
});

/*
 * essentially main(). Routes the user to the right page
 */

require([
  "react",
  "underscore",
  "uriJS/URI",
  "es6!server/api",
  // requiring every page. It doesn't matter that much in prod since we bundle,
  // and we want to avoid dynamic module loading
  "es6!pages/home_page",
  "es6!pages/project/project_page",
  "es6!pages/my_builds_page",
  "es6!pages/builds/builds_pages",
  "es6!pages/test_history_page",
  "es6!pages/all_projects_page",
  "es6!pages/node_page",
  "es6!pages/error_page",
  "es6!pages/test_page",
  "es6!pages/ui_test_page",
], function(
  React,
  _,
  URI,
  data_fetching,

  HomePage,
  ProjectPage,
  MyBuildsPage,
  buildsPages,
  TestHistoryPage,
  AllProjectsPage,
  NodePage,
  ErrorPage,
  TestPage,
  UITestPage
) {
  'use strict';

  // for some reason, import statements aren't working for the URI library
  // TODO: figure out why
  window.URI = URI;

  var CommitPage = buildsPages.CommitPage;
  var DiffPage = buildsPages.DiffPage;

  // routing
  // TODO: all of this is terrible and temporary just to get something working.
  // replace with a routing library. Probably not react-router, though... its
  // too template-y. Or at least don't use nesting with react-router

  var url = window.location.href;
  var path = _.last(url.split('/v2/', 2)).trim();
  // ignore # and ?
  var path = path.split(/[\?#]/, 1)[0];
  var path_parts = _.compact(path.split('/'));

  var url_contains = {
    'projects': [AllProjectsPage],
    'project': [ProjectPage, 'projectSlug'],
    'builds': [MyBuildsPage],
    'commit': [CommitPage, 'sourceUUID'],
    'diff': [DiffPage, 'diff_id'],
    'project_test': [TestHistoryPage, 'projectUUID', 'testHash'],
    // TODO: don't just use the homepage for this
    'author': [HomePage, 'author'],
    'node': [NodePage, 'node_id'],
    'test': [TestPage],
    'ui_examples': [UITestPage]
  };

  var page = ErrorPage;

  var params = {};
  for (var str in url_contains) {
    if (path_parts[0] === str) {
      var page_data = url_contains[str];
      page = page_data[0];
      if (page_data.length > 1) {
        if (path_parts.length < page_data.length) {
          // path doesn't have enough parts...
          page = ErrorPage;
          break;
        }
        for (var i = 1; i < page_data.length; i++) {
          params[page_data[i]] = path_parts[i];
        }
      }
      break;
    }
  }

  if (path === "") { page = HomePage; }

  // TODO: pages should set window.document.title

  data_fetching.make_api_ajax_get('/api/0/auth', function(response) {
    // TODO: use context?
    window.changesAuthData = JSON.parse(response.responseText);

    React.render(
      React.createElement(page, params),
      document.getElementById('reactRoot')
    );
  });
});

