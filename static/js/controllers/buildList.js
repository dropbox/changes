define(['app', 'directives/radialProgressBar', 'directives/timeSince', 'filters/orderByBuild'], function(app) {
  var buildListCtrl = function(initial, $scope, $http, $routeParams, $location, Stream) {
    var stream,
        entrypoint = initial.entrypoint,
        filter = $location.search()['filter'] || '';

    $scope.builds = initial.data.builds;
    $scope.buildNavFilter = filter;

    $scope.getBuildStatus = function(build) {
      if (build.status.id == 'finished') {
        return build.result.name;
      } else {
        return build.status.name;
      }
    }

    $scope.buildNavClass = function(path) {
        return $location.path() == path ? 'active' : '';
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
        }
      });
    }

    stream = Stream($scope, entrypoint);
    stream.subscribe('build.update', addBuild);

  };

  app.controller('buildListCtrl', ['initial', '$scope', '$http', '$routeParams', '$location', 'stream', buildListCtrl]);

  return buildListCtrl;
});
