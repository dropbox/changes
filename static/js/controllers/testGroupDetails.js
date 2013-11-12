define([
    'app',
    'utils/chartHelpers',
    'utils/duration',
    'utils/escapeHtml',
    'directives/timeSince',
    'directives/duration'], function(app, chartHelpers, duration, escapeHtml) {
  app.controller('testGroupDetailsCtrl', ['$scope', 'initialData', '$routeParams', function($scope, initialData, $routeParams) {
    'use strict';

    var stream,
        entrypoint = '/api/0/testgroups/' + $routeParams.testgroup_id + '/',
        chart_options = {
          tooltipFormatter: function(item) {
            var content = ''

            content += '<h5>';
            content += escapeHtml(item.build.name);
            content += '<br><small>';
            content += escapeHtml(item.build.target);
            if (item.author) {
              content += ' &mdash; ' + item.author.name;
            }
            content += '</small>'
            content += '</h5>';
            content += '<p>Test ' + item.result.name;
            if (item.duration) {
              content += ' in ' + duration(item.duration);
            }
            content += ' (Build ' + item.build.result.name + ')</p>';

            return content;
          }
        };

    $scope.build = initialData.data.build;
    $scope.testFailures = initialData.data.testFailures;
    $scope.testGroup = initialData.data.testGroup;
    $scope.testGroup.build = $scope.build;
    $scope.childTestGroups = initialData.data.childTestGroups;
    $scope.testCase = initialData.data.testCase;
    $scope.previousRuns = initialData.data.previousRuns;
    $scope.context = initialData.data.context;
    $scope.chartData = chartHelpers.getChartData($scope.previousRuns, $scope.testGroup, chart_options);
  }]);
});
