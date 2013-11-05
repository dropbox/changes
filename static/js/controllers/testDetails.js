define(['app', 'directives/timeSince', 'directives/duration'], function(app) {
  app.controller('testDetailsCtrl', ['$scope', 'initialData', '$http', '$routeParams', 'stream', function($scope, initialData, $http, $routeParams, Stream) {
    'use strict';

    var stream,
        entrypoint = '/api/0/tests/' + $routeParams.test_id + '/';

    function getChartData(tests) {
      // this should return two series, one with passes, and one with failures
      var ok = [],
          failures = [],
          test, point, i;

      for (i = 0; (test = tests[i]); i++) {
        point = [i, test.duration];
        if (test.result.id == 'passed' || test.result.id == 'skipped') {
          ok.push(point);
        } else {
          failures.push(point)
        }
      }

      return [
        {data: ok, color: '#c7c0de', label: 'Ok'},
        {data: failures, color: '#d9322d', label: 'Failed'}
      ]
    }

    function updateTest(data){
      $scope.$apply(function() {
        $scope.test = data;
      });
    }

    $scope.test = initialData.data.test;
    $scope.build = initialData.data.build;
    $scope.previousRuns = initialData.data.previousRuns;
    $scope.firstRun = initialData.data.firstRun;
    $scope.chartData = getChartData($scope.previousRuns);

    stream = Stream($scope, entrypoint);
    stream.subscribe('test.update', updateTest);
  }]);
});
