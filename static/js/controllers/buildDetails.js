define(['app', 'factories/stream', 'directives/radialProgressBar', 'directives/timeSince', 'directives/duration',
        'filters/escape', 'filters/wordwrap', 'modules/pagination', 'factories/flash'], function(app) {
  app.controller('buildDetailsCtrl', ['$scope', 'initialData', '$window', '$http', '$routeParams', 'stream', 'pagination', 'flash', function($scope, initialData, $window, $http, $routeParams, Stream, Pagination, flash) {
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
    function getTestStatus() {
      if ($scope.build.status.id == "finished") {
        if ($scope.tests.length === 0) {
          return "no-results";
        } else {
          return "has-results";
        }
      }
      return "pending";
    }

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

    $scope.build = initialData.data.build;
    $scope.phases = initialData.data.phase;
    $scope.tests = sortTests(initialData.data.tests);
    $scope.testsPaginator = Pagination.create($scope.tests);
    $scope.testStatus = getTestStatus();

    $scope.$watch("build.status", function(status) {
      $scope.testStatus = getTestStatus();
    });
    $scope.$watch("build.tests", function(status) {
      $scope.testStatus = getTestStatus();
    });

    $scope.retryBuild = function() {
      $http.post('/api/0/builds/' + $scope.build.id + '/retry/')
        .success(function(data){
          $window.location.href = data.build.link;
        })
        .error(function(){
          flash('error', 'There was an error while retrying this build.');
        });
    };

    stream = Stream($scope, entrypoint);
    stream.subscribe('build.update', updateBuild);
    stream.subscribe('test.update', addTest);
  }]);
});
