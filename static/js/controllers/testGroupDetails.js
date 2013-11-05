define(['app', 'directives/timeSince', 'directives/duration'], function(app) {
  app.controller('testGroupDetailsCtrl', ['$scope', 'initialData', '$routeParams', function($scope, initialData, $routeParams) {
    'use strict';

    var stream,
        entrypoint = '/api/0/testgroups/' + $routeParams.testgroup_id + '/';

    function getChartData(testgroups) {
      // this should return two series, one with passes, and one with failures
      var ok = [],
          failures = [],
          testgroup, point, i;

      for (i = 0; (testgroup = testgroups[i]); i++) {
        point = [i, testgroup.duration];
        if (testgroup.result.id == 'passed' || testgroup.result.id == 'skipped') {
          ok.push(point);
        } else {
          failures.push(point)
        }
      }

      return {
        values: [
          {data: ok, color: '#c7c0de', label: 'Ok'},
          {data: failures, color: '#d9322d', label: 'Failed'}
        ],
        options: {}
      }
    }

    $scope.build = initialData.data.build;
    $scope.testFailures = initialData.data.testFailures;
    $scope.testGroup = initialData.data.testGroup;
    $scope.childTestGroups = initialData.data.childTestGroups;
    $scope.childTests = initialData.data.childTests;
    $scope.previousRuns = initialData.data.previousRuns
    $scope.chartData = getChartData($scope.previousRuns);
  }]);
});
