(function(){
  'use strict';

  define(['app'], function(app) {
    app.directive('commitInfo', function() {
      return {
        restrict: 'E',
        templateUrl: 'partials/directives/commit-info.html',
        scope: {
          commit: '=',
          title: '=',
          showProject: '=',
        },
        replace: true,
      };
    });
  });
})();
