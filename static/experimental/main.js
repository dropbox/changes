requirejs.config({
  paths: {
    es6: "../vendor/requirejs-babel/es6",
    babel: "../vendor/requirejs-babel/babel-4.6.6.min",
    react: '../vendor/react/react.min',
    requirejs: '../vendor/requirejs/require',
  },
});

require([
    "react", 
    "es6!pages/test_page", 
  ], function(React, TestPage) {
  'use strict';

  React.render(
    React.createElement(TestPage, {}),
    document.getElementById('reactRoot')
  );
});

