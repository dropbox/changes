define(['app', 'factories/stream', 'directives/radialProgressBar', 'directives/timeSince', 'directives/duration'], function(app) {
  app.controller('buildDetailsCtrl', ['$scope', '$http', '$routeParams', 'stream', function($scope, $http, $routeParams, Stream) {
    'use strict';

    var stream,
        entrypoint = '/api/0/builds/' + $routeParams.build_id + '/';

    $scope.build = null;
    $scope.phases = [];
    $scope.tests = [];

    $http.get(entrypoint).success(function(data) {
      $scope.build = data.build;
      $scope.tests = data.tests;
      $scope.phases = data.phases;
    });

    function updateBuild(data){
      $scope.$apply(function() {
        $scope.build = data;
      });
    }

    function addTest(data) {
      $scope.$apply(function() {
        var updated = false,
            item_id = data.id,
            attr, result, item;

        if ($scope.tests.length > 0) {
          result = $.grep($scope.tests, function(e){ return e.id == item_id; });
          if (result.length > 0) {
            item = result[0];
            for (attr in data) {
              item[attr] = data[attr];
            }
            updated = true;
          }
        }
        if (!updated) {
          $scope.tests.unshift(data);
        }
      });
    }

    stream = Stream($scope, entrypoint);
    stream.subscribe('build.update', updateBuild);
    stream.subscribe('test.update', addTest);
  }]);
});
