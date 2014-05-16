(function(){
  'use strict';

  define(['app'], function(app) {
    app.directive('buildrow', function($timeout) {
      var tickRate = 3000;

      function getCoveragePercent(build) {
        var total_lines = build.stats.diff_lines_covered + build.stats.diff_lines_uncovered;
        if (!total_lines) {
          return 0;
        }
        return parseInt(build.stats.diff_lines_covered / total_lines * 100, 10);
      }

      function getEstimatedProgress(build)
      {
        if (build.status.id == 'finished') {
          return 100;
        }

        var ts_start = new Date(build.dateStarted).getTime();
        if (!ts_start) {
          return 0;
        }

        var ts_now = Math.max(new Date().getTime(), ts_start);
        return parseInt(Math.min((ts_now - ts_start) / build.estimatedDuration * 100, 95), 10);
      }

      return {
        templateUrl: 'partials/includes/build-row.html',
        restrict: 'E',
        link: function (scope, element, attrs) {
          var timeout_id;

          scope.estimatedProgress = 0;

          function updateBuildProgress(build) {
            scope.estimatedProgress = getEstimatedProgress(build);

            if (build.status.id != 'finished') {
              timeout_id = $timeout(function(){
                updateBuildProgress(build);
              }, tickRate);
            }
          }

          scope.$watch(attrs.ngModel, function(build) {
            scope.build = build;
            scope.buildTitle = attrs.title || build.name;
            scope.hasCoverage = (build.stats.diff_lines_covered + build.stats.diff_lines_uncovered) > 0;
            scope.coveragePercent = getCoveragePercent(build);
            scope.isFinished = (build.status.id == 'finished');

            updateBuildProgress(build);
          });

          element.bind('$destroy', function() {
            if (timeout_id) {
              $timeout.cancel(timeout_id);
            }
          });

        }
      };
    });
  });
})();
