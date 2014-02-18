(function(){
  'use strict';

  define([
      'app',
      'utils/chartHelpers',
      'utils/duration',
      'utils/escapeHtml'], function(app, chartHelpers, duration, escapeHtml) {
    app.controller('projectTestDetailsCtrl', [
        '$scope', '$rootScope', 'initialProject', 'initialTest',
        function($scope, $rootScope, initialProject, initialTest) {
      var chart_options = {
            tooltipFormatter: function(item) {
              var content = '';
              var build = item.job.build;

              content += '<h5>';
              content += escapeHtml(build.name);
              content += '<br><small>';
              content += escapeHtml(build.target);
              if (build.author) {
                content += ' &mdash; ' + build.author.name;
              }
              content += '</small>';
              content += '</h5>';
              content += '<p>Test ' + item.result.name;
              if (item.duration) {
                content += ' in ' + duration(item.duration);
              }
              content += ' (Build ' + build.result.name + ')</p>';

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
