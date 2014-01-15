(function(){
  'use strict';

  define([
      'app',
      'utils/chartHelpers',
      'utils/duration',
      'utils/escapeHtml',
      'directives/timeSince'], function(app, chartHelpers, duration, escapeHtml) {
    app.controller('projectTestDetailsCtrl', [
        '$scope', '$rootScope', 'initialProject', 'initialTest',
        function($scope, $rootScope, initialProject, initialTest) {
      var chart_options = {
            tooltipFormatter: function(item) {
              var content = '';

              content += '<h5>';
              content += escapeHtml(item.build.name);
              content += '<br><small>';
              content += escapeHtml(item.build.target);
              if (item.author) {
                content += ' &mdash; ' + item.author.name;
              }
              content += '</small>';
              content += '</h5>';
              content += '<p>Test ' + item.result.name;
              if (item.duration) {
                content += ' in ' + duration(item.duration);
              }
              content += ' (Build ' + item.build.result.name + ')</p>';

              return content;
            }
          };

      $scope.project = initialProject.data;
      $scope.test = initialTest.data.test;
      $scope.childTests = initialTest.data.childTests;
      $scope.context = initialTest.data.context;
      $scope.previousRuns = initialTest.data.previousRuns;
      $rootScope.activeProject = $scope.project;
      $scope.chartData = chartHelpers.getChartData($scope.previousRuns, null, chart_options);

    }]);
  });
})();
