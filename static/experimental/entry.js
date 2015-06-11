requirejs.config({
  // TODO: use minified versions in prod
  paths: {
    // code is written in jsx/es6 syntax and converted using babel
    es6: "../vendor/requirejs-babel/es6",
    babel: "../vendor/requirejs-babel/babel-4.6.6.min",
    // mostly just for jquery.ajax
    jquery: "../vendor/jquery/jquery",
    // time library
    moment: "../vendor/moment/min/moment.min",
    // core libraries we use
    react: '../vendor/react/react-with-addons',
    requirejs: '../vendor/requirejs/require',
    underscore: '../vendor/underscore/underscore'
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

require(["react", "es6", "babel"], function(React, Route) {
  'use strict';

  // TODO: all of this is terrible and temporary just to get something working.
  // replace with a routing library. Probably not react-router, though... its 
  // too template-y. Or at least don't use nesting with react-router
  require([
    // TODO: don't include everything... it might not matter with bundling,
    // though
    "es6!pages/home_page",
    "es6!pages/project_page",
    "es6!pages/commit_page",
    "es6!pages/error_page",
    "es6!pages/test_page",
    "es6!pages/ui_test_page"
  ], function(
    HomePage,
    ProjectPage,
    CommitPage,
    ErrorPage,
    TestPage,
    UITestPage
  ) {

    var url = window.location.href;
    var path_start = url.indexOf('experimental/') + 'experimental/'.length;
    var path = url.substr(path_start);
    var path_parts = _.compact(path.split('/'));

    var url_contains = {
      'project': [ProjectPage, 'project'],
      'project_commit': [CommitPage, 'project', 'sourceUUID'],
      // TODO: don't just use the homepage for this
      'author': [HomePage, 'author'],
      'test': [TestPage],
      'ui_examples': [UITestPage]
    };

    var page = HomePage;
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

    // TODO: pages should set window.document.title

    // HACK: always send an auth/ api call
    require(['es6!utils/data_fetching'], function(data_fetching) {
      data_fetching.make_api_ajax_call('/auth');
    });

    React.render(
      React.createElement(page, params),
      document.getElementById('reactRoot')
    );
  });
});

