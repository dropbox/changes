define(['app', 'factories/stream', 'directives/radialProgressBar'], function(app) {
  app.controller('changeDetailsCtrl', ['$scope', '$http', '$routeParams', 'stream', function($scope, $http, $routeParams, Stream) {
    'use strict';

    var stream;

    $scope.change = null;

    $http.get('/api/0/changes/' + $routeParams.change_id + '/').success(function(data) {
      $scope.change = data.change;
    });

    $scope.timeSince = function timeSince(date) {
      return moment.utc(date).fromNow();
    };

    function updateChange(data){
      $scope.$apply(function() {
        $scope.change = data;
      });
    }


    stream = Stream($scope, '/api/0/changes/' + $routeParams.change_id + '/');
    stream.subscribe('change.update', updateChange);

  }]);
});
