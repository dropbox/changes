define(['app', 'directives/radialProgressBar', 'directives/timeSince'], function(app) {
  app.controller('changeDetailsCtrl', ['$scope', 'initialData', '$http', '$routeParams', 'stream', function($scope, initialData, $http, $routeParams, Stream) {
    'use strict';

    var stream,
        entrypoint = '/api/0/changes/' + $routeParams.change_id + '/';

    $scope.change = initialData.data.change;

    function updateChange(data){
      $scope.$apply(function() {
        $scope.change = data;
      });
    }

    stream = Stream($scope, entrypoint);
    stream.subscribe('change.update', updateChange);

  }]);
});
