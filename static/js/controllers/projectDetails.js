define([
    'app',
    'utils/chartHelpers',
    'directives/radialProgressBar',
    'directives/timeSince',
    'filters/orderByBuild'], function(app, chartHelpers) {
  app.controller('projectDetailsCtrl', ['$scope', 'initialProject', 'initialBuildList', '$http', '$routeParams', 'stream', function($scope, initialProject, initialBuildList, $http, $routeParams, Stream) {
    'use strict';

    var stream,
        entrypoint = '/api/0/projects/' + $routeParams.project_id + '/builds/',
        chart_options = {
          labelFormatter: function(item) {
            return item.name;
          },
          linkFormatter: function(item) {
            return item.link;
          }
        };

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

    $scope.getBuildStatus = function(build) {
      if (build.status.id == 'finished') {
        return build.result.name;
      } else {
        return build.status.name;
      }
    }

    $scope.project = initialProject.data.project;
    $scope.builds = initialBuildList.data.builds;
    $scope.chartData = chartHelpers.getChartData($scope.builds, null, chart_options);

    $scope.$watch("builds", function() {
      $scope.chartData = chartHelpers.getChartData($scope.builds, null, chart_options);
    });

    stream = Stream($scope, entrypoint);
    stream.subscribe('build.update', addBuild);

  }]);
});
