define(['app', 'factories/stream', 'directives/radialProgressBar', 'directives/timeSince', 'directives/duration',
        'filters/escape', 'filters/wordwrap', 'modules/pagination'], function(app) {
  app.controller('buildDetailsCtrl', ['$scope', 'initialData', '$http', '$routeParams', 'stream', 'pagination', function($scope, initialData, $http, $routeParams, Stream, Pagination) {
    'use strict';

    var stream,
        entrypoint = '/api/0/builds/' + $routeParams.build_id + '/';

    $scope.build = initialData.data.build;
    $scope.phases = initialData.data.phase;
    $scope.tests = initialData.data.tests;

    $scope.testsPagination = Pagination.create($scope.tests);

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

    $scope.getTestStatus = function() {
      if ($scope.build.status.id == "finished") {
        if ($scope.tests.length === 0) {
          return "no-results";
        } else {
          return "has-results";
        }
      }
      return "pending";
    };

    stream = Stream($scope, entrypoint);
    stream.subscribe('build.update', updateBuild);
    stream.subscribe('test.update', addTest);
  }]);
});
