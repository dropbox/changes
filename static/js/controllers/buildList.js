define(['app', 'factories/stream', 'factories/flash', 'directives/radialProgressBar', 'directives/timeSince', 'filters/orderByBuild'], function(app) {
  app.controller('buildListCtrl', ['$scope', '$http', '$routeParams', 'stream', 'flash', function($scope, $http, $routeParams, Stream, flash) {
    'use strict';

    var stream;
    var entrypoint

    $scope.builds = [];

    if ($routeParams.change_id) {
      entrypoint = '/api/0/changes/' + $routeParams.change_id + '/builds/';
    } else {
      entrypoint = '/api/0/builds/';
    }

    $http.get(entrypoint).
      success(function(data) {
        $scope.builds = data.builds;
      }).
      error(function(){
        flash('error', 'Unable to load build list');
      });

    $scope.getBuildStatus = function(build) {
      if (build.status.id == 'finished') {
        return build.result.name;
      } else {
        return build.status.name;
      }
    }

    function addBuild(build) {
      $scope.$apply(function() {
        var updated = false,
            build_id = build.id,
            attr, result, item;

        if ($scope.builds.length > 0) {
          result = $.grep($scope.builds, function(e){ return e.id == build_id; });
          if (result.length > 0) {
            item = result[0];
            for (attr in build) {
              item[attr] = build[attr];
            }
            updated = true;
          }
        }
        if (!updated) {
          $scope.builds.unshift(build);
        }
      });
    }

    stream = Stream($scope, entrypoint);
    stream.subscribe('build.update', addBuild);

  }]);
});
