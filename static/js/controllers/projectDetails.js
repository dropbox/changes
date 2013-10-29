define(['app', 'directives/radialProgressBar', 'directives/timeSince', 'filters/orderByBuild'], function(app) {
  app.controller('projectDetailsCtrl', ['$scope', 'initial', '$http', '$routeParams', 'stream', function($scope, initial, $http, $routeParams, Stream) {
    'use strict';

    var stream,
        entrypoint = '/api/0/projects/' + $routeParams.project_id + '/builds/';

    $scope.project = initial.data.project;
    $scope.builds = [];

    $http.get(entrypoint)
      .success(function(data){
        $scope.builds = data.builds;
      })

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
