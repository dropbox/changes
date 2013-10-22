define(['app', 'factories/stream', 'directives/radialProgressBar', 'directives/timeSince', 'directives/duration',
        'filters/escape', 'filters/wordwrap', 'modules/pagination', 'ngInfiniteScroll'], function(app) {
  app.controller('buildDetailsCtrl', ['$scope', 'initialData', '$http', '$routeParams', 'stream', 'pagination', function($scope, initialData, $http, $routeParams, Stream, Pagination) {
    'use strict';

    var stream,
        entrypoint = '/api/0/builds/' + $routeParams.build_id + '/';

    function sortTests(arr) {
      var resultScore = {
        'errored': 1100,
        'failed': 1000,
        'skipped': 200,
        'passed': 100
      }

      function getScore(object) {
        return [resultScore[object.result.id] || 500, object.duration];
      }

      arr.sort(function(a, b){
        var a_score = getScore(a),
            b_score = getScore(b);
        if (a_score[0] < b_score[0]) {
          return 1
        }
        if (a_score[0] > b_score[0]) {
          return -1
        }
        if (a_score[1] < b_score[1]) {
          return 1
        }
        if (a_score[1] > b_score[1]) {
          return -1
        }
        if (a_score[2] < b_score[2]) {
          return 1
        }
        if (a_score[2] > b_score[2]) {
          return -1
        }
        return 0;
      });

      return arr;
    }

    $scope.build = initialData.data.build;
    $scope.phases = initialData.data.phase;
    $scope.tests = sortTests(initialData.data.tests);
    $scope.testsPaginator = Pagination.create($scope.tests);

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
