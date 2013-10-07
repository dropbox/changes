define(['app', 'factories/stream', 'directives/radialProgressBar', 'directives/timeSince', 'directives/duration'], function(app) {
  app.controller('buildDetailsCtrl', ['$scope', '$http', '$routeParams', 'stream', function($scope, $http, $routeParams, Stream) {
    'use strict';

    var stream;

    $scope.build = null;
    $scope.phases = [];
    $scope.tests = [];

    $http.get('/api/0/changes/' + $routeParams.change_id + '/builds/' + $routeParams.build_id + '/').success(function(data) {
      $scope.build = data.build;
      $scope.tests = data.tests;
      $scope.phases = data.phases;
    });

    function updateBuild(data){
      $scope.$apply(function() {
        $scope.build = data;
      });
    }

    stream = Stream($scope, '/api/0/changes/' + $routeParams.change_id + '/builds/' + $routeParams.build_id + '/');
    stream.subscribe('build.update', updateBuild);
  }]);
});
