define(['app', 'utils/escapeHtml'], function (app, escapeHtml) {
  'use strict';
  app.filter('escape', function(){
    return function(input) {
      return escapeHtml(input);
    };
  });
});
