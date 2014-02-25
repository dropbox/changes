(function(){
  'use strict';

  define([
      'app',
      'utils/chartHelpers',
      'utils/duration',
      'utils/escapeHtml'], function(app, chartHelpers, duration, escapeHtml) {
    app.controller('testGroupDetailsCtrl', [
          '$scope', '$rootScope', 'initialData', '$stateParams',
          function($scope, $rootScope, initialData, $stateParams) {
      var stream,
          entrypoint = '/api/0/testgroups/' + $stateParams.testgroup_id + '/',
          chart_options = {
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

      $scope.project = initialData.data.project;
      $scope.build = initialData.data.build;
      $scope.job = initialData.data.job;
      $scope.testFailures = initialData.data.testFailures;
      $scope.testGroup = initialData.data.testGroup;
      $scope.testGroup.build = $scope.build;
      $scope.childTestGroups = initialData.data.childTestGroups;
      $scope.testCase = initialData.data.testCase;
      $scope.previousRuns = initialData.data.previousRuns;
      $scope.context = initialData.data.context;
      $scope.chartData = chartHelpers.getChartData($scope.previousRuns, $scope.testGroup, chart_options);

      $rootScope.activeProject = $scope.project;
    }]);
  });
})();
