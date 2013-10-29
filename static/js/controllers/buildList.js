define(['app', 'directives/radialProgressBar', 'directives/timeSince', 'filters/orderByBuild'], function(app) {
  app.controller('buildListCtrl', ['$scope', 'initialData', '$http', '$routeParams', 'stream', 'flash', function($scope, initialData, $http, $routeParams, Stream, flash) {
    'use strict';

    var stream, entrypoint;

    $scope.builds = initialData.data.builds;

    if ($routeParams.change_id) {
      entrypoint = '/api/0/changes/' + $routeParams.change_id + '/builds/';
    } else {
      entrypoint = '/api/0/builds/';
    }

    $scope.getBuildStatus = function(build) {
      if (build.status.id == 'finished') {
        return build.result.name;
      } else {
        return build.status.name;
      }
    }

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
        }
      });
    }

    stream = Stream($scope, entrypoint);
    stream.subscribe('build.update', addBuild);

  }]);
});
