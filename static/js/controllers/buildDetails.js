(function(){
  'use strict';

  define([
      'app',
      'utils/chartHelpers',
      'utils/duration',
      'utils/escapeHtml',
      'directives/radialProgressBar',
      'directives/timeSince',
      'directives/duration',
      'filters/escape',
      'filters/wordwrap',
      'modules/pagination'], function(app, chartHelpers, duration, escapeHtml) {
    app.controller('buildDetailsCtrl', [
        '$scope', '$rootScope', 'initialData', '$window', '$timeout', '$http', '$routeParams', '$filter', 'stream', 'pagination', 'flash',
        function($scope, $rootScope, initialData, $window, $timeout, $http, $routeParams, $filter, Stream, Pagination, flash) {

      var stream,
          entrypoint = '/api/0/builds/' + $routeParams.build_id + '/',
          chart_options = {
            tooltipFormatter: function(item) {
              var content = '';

              content += '<h5>';
              content += escapeHtml(item.name);
              content += '<br><small>';
              content += escapeHtml(item.target);
              if (item.author) {
                content += ' &mdash; ' + item.author.name;
              }
              content += '</small>';
              content += '</h5>';
              if (item.status.id == 'finished') {
                content += '<p>Build ' + item.result.name;
                if (item.duration) {
                  content += ' in ' + duration(item.duration);
                }
                content += '</p>';
              } else {
                content += '<p>' + item.status.name + '</p>';
              }

              return content;
            }
          };

      function getFormattedBuildMessage(build) {
        return $filter('linkify')($filter('escape')(build.message));
      }

      function updateBuild(data){
        $scope.$apply(function() {
          $scope.build = data;
        });
      }

      $scope.$watch("build.message", function() {
        $scope.formattedBuildMessage = getFormattedBuildMessage($scope.build);
      });

      $scope.project = initialData.data.project;
      $scope.build = initialData.data.build;
      $scope.previousRuns = initialData.data.previousRuns;
      $scope.chartData = chartHelpers.getChartData($scope.previousRuns, $scope.build, chart_options);

      $rootScope.activeProject = $scope.project;

      stream = new Stream($scope, entrypoint);
      stream.subscribe('job.update', updateBuild);
    }]);
  });
})();
