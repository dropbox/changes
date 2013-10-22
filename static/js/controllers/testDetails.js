define(['app', 'factories/stream', 'directives/timeSince', 'directives/duration'], function(app) {
  app.controller('testDetailsCtrl', ['$scope', 'initialData', '$http', '$routeParams', 'stream', function($scope, initialData, $http, $routeParams, Stream) {
    'use strict';

    var stream,
        entrypoint = '/api/0/tests/' + $routeParams.test_id + '/';

    $scope.test = initialData.data.test;
    $scope.build = initialData.data.build;
    $scope.previousRuns = initialData.data.previousRuns

    function updateTest(data){
      $scope.$apply(function() {
        $scope.test = data;
      });
    }

    stream = Stream($scope, entrypoint);
    stream.subscribe('test.update', updateTest);
  }]);
});
