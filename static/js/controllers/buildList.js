define(['app', 'factories/stream', 'directives/radialProgressBar', 'filters/orderByBuild'], function(app) {
  app.controller('buildListCtrl', ['$scope', '$http', '$routeParams', 'stream', function($scope, $http, $routeParams, Stream) {
    'use strict';

    var stream;

    $scope.builds = [];

    $http.get('/api/0/changes/' + $routeParams.change_id + '/builds/').success(function(data) {
      $scope.builds = data.builds;
    });

    $scope.timeSince = function timeSince(date) {
      return moment.utc(date).fromNow();
    };

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

    stream = Stream($scope, '/api/0/changes/' + $routeParams.change_id + '/builds/');
    stream.subscribe('build.update', addBuild);

  }]);
});
