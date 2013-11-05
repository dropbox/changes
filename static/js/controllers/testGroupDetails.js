define([
    'app',
    'utils/chartHelpers',
    'directives/timeSince',
    'directives/duration'], function(app, chartHelpers) {
  app.controller('testGroupDetailsCtrl', ['$scope', 'initialData', '$routeParams', function($scope, initialData, $routeParams) {
    'use strict';

    var stream,
        entrypoint = '/api/0/testgroups/' + $routeParams.testgroup_id + '/';

    $scope.build = initialData.data.build;
    $scope.testFailures = initialData.data.testFailures;
    $scope.testGroup = initialData.data.testGroup;
    $scope.childTestGroups = initialData.data.childTestGroups;
    $scope.childTests = initialData.data.childTests;
    $scope.previousRuns = initialData.data.previousRuns
    $scope.chartData = chartHelpers.getChartData($scope.previousRuns);
  }]);
});
