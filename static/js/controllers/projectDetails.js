define(['app', 'directives/radialProgressBar', 'directives/timeSince', 'filters/orderByBuild'], function(app) {
  app.controller('projectDetailsCtrl', ['$scope', 'initialProject', 'initialBuildList', '$http', '$routeParams', 'stream', function($scope, initialProject, initialBuildList, $http, $routeParams, Stream) {
    'use strict';

    var stream,
        entrypoint = '/api/0/projects/' + $routeParams.project_id + '/builds/';

    function addBuild(data) {
      $scope.$apply(function() {
        var updated = false,
            item_id = data.id,
            attr, result, item;

        if ($scope.builds.length > 0) {
          result = $.grep($scope.builds, function(e){ return e.id == item_id; });
          if (result.length > 0) {
            item = result[0];
            for (attr in data) {
              // ignore dateModified as we're updating this frequently and it causes
              // the dirty checking behavior in angular to respond poorly
              if (item[attr] != data[attr] && attr != 'dateModified') {
                updated = true;
                item[attr] = data[attr];
              }
              if (updated) {
                item.dateModified = data.dateModified;
              }
            }
          }
        }
        if (!updated) {
          $scope.builds.unshift(data);
          $scope.builds = $scope.builds.slice(0, 100);
        }
      });
    }

    function getChartData(builds) {
      // this should return two series, one with passes, and one with failures
      var ok = [],
          failures = [],
          build, point, i;

      for (i = 0; (build = builds[i]) && i < 50; i++) {
        point = [i, build.duration || 1];
        if (build.result.id == 'passed' || build.result.id == 'skipped') {
          ok.push(point);
        } else {
          failures.push(point)
        }
      }

      return {
        values: [
          {data: ok, color: '#c7c0de', label: 'Ok'},
          {data: failures, color: '#d9322d', label: 'Failed'}
        ],
        options: {}
      }
    }

    $scope.getBuildStatus = function(build) {
      if (build.status.id == 'finished') {
        return build.result.name;
      } else {
        return build.status.name;
      }
    }

    $scope.project = initialProject.data.project;
    $scope.builds = initialBuildList.data.builds;
    $scope.chartData = getChartData($scope.builds);

    $scope.$watch("builds", function() {
      $scope.chartData = getChartData($scope.builds);
    });

    stream = Stream($scope, entrypoint);
    stream.subscribe('build.update', addBuild);

  }]);
});
