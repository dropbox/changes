define(['app', 'factories/stream', 'directives/timeSince', 'directives/duration'], function(app) {
  app.controller('testDetailsCtrl', ['$scope', '$http', '$routeParams', 'stream', function($scope, $http, $routeParams, Stream) {
    'use strict';

    var stream,
        entrypoint = '/api/0/tests/' + $routeParams.test_id + '/';

    $scope.test = null;
    $scope.build = null;

    $http.get(entrypoint).success(function(data) {
      $scope.test = data.test;
      $scope.build = data.build;
    });

    function updateTest(data){
      $scope.$apply(function() {
        $scope.test = data;
      });
    }

    stream = Stream($scope, entrypoint);
    stream.subscribe('test.update', updateTest);
  }]);
});
