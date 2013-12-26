(function(){
  'use strict';

  define([
      'app',
      'utils/sortBuildList',
      'directives/radialProgressBar',
      'directives/timeSince'], function(app, sortBuildList) {
    var authorBuildListCtrl = function(initialBuildList, $scope, $http, Stream) {

      var stream,
          entrypoint = '/api/0/authors/me/builds/';

      $scope.builds = sortBuildList(initialBuildList.data.builds);

      $scope.getBuildStatus = function(build) {
        if (build.status.id == 'finished') {
          return build.result.name;
        } else {
          return build.status.name;
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
            sortBuildList($scope.builds);
            $scope.builds = $scope.builds.slice(0, 100);
          }
        });
      }

      stream = new Stream($scope, entrypoint);
      stream.subscribe('build.update', addBuild);

    };

    app.controller('authorBuildListCtrl', ['initialBuildList', '$scope', '$http', 'stream', authorBuildListCtrl]);

    return authorBuildListCtrl;
  });
})();
