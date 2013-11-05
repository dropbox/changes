define([
    'app',
    'utils/chartHelpers',
    'directives/timeSince',
    'directives/duration'], function(app, chartHelpers) {
  app.controller('testDetailsCtrl', ['$scope', 'initialData', '$http', '$routeParams', 'stream', function($scope, initialData, $http, $routeParams, Stream) {
    'use strict';

    var stream,
        entrypoint = '/api/0/tests/' + $routeParams.test_id + '/';

    function updateTest(data){
      $scope.$apply(function() {
        $scope.test = data;
      });
    }

    $scope.test = initialData.data.test;
    $scope.build = initialData.data.build;
    $scope.previousRuns = initialData.data.previousRuns;
    $scope.firstRun = initialData.data.firstRun;
    $scope.chartData = chartHelpers.getChartData($scope.previousRuns, $scope.test);

    stream = Stream($scope, entrypoint);
    stream.subscribe('test.update', updateTest);
  }]);
});
