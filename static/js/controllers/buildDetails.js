define(['app', 'factories/stream', 'directives/radialProgressBar'], function(app) {
  app.controller('buildDetailsCtrl', ['$scope', '$http', '$routeParams', 'stream', function($scope, $http, $routeParams, stream) {
    'use strict';

    $scope.build = null;
    $scope.phases = [];
    $scope.tests = [];

    $http.get('/api/0/changes/' + $routeParams.change_id + '/builds/' + $routeParams.build_id + '/').success(function(data) {
      $scope.build = data.build;
      $scope.tests = data.tests;
      $scope.phases = data.phases;
    });

    $scope.timeSince = function timeSince(date) {
      return moment.utc(date).fromNow();
    };

    function updateBuild(data){
      $scope.$apply(function() {
        $scope.build = data;
      });
    }

    stream($scope, '/api/0/changes/' + $routeParams.change_id + '/builds/' + $routeParams.build_id + '/', updateBuild);

  }]);
});
