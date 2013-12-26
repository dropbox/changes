(function(){
  'use strict';

  define(['app', 'utils/escapeHtml'], function (app, escapeHtml) {
    app.filter('escape', function(){
      return function(input) {
        return escapeHtml(input);
      };
    });
  });
})();
