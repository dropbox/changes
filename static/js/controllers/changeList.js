define(['app', 'factories/stream', 'directives/radialProgressBar'], function(app) {
  app.controller('changeListCtrl', ['$scope', '$http', 'stream', function($scope, $http, Stream) {
    'use strict';

    var stream;

    $scope.changes = [];

    $http.get('/api/0/changes/').success(function(data) {
      $scope.changes = data.changes;
    });

    // TODO: move to directive
    $scope.timeSince = function timeSince(date) {
      return moment.utc(date).fromNow();
    };

    function addChange(change) {
      $scope.$apply(function() {
        var updated = false,
            change_id = change.id,
            attr, result, item;

        if ($scope.changes.length > 0) {
          result = $.grep($scope.changes, function(e){ return e.id == change_id; });
          if (result.length > 0) {
            item = result[0];
            for (attr in change) {
              item[attr] = change[attr];
            }
            updated = true;
          }
        }
        if (!updated) {
          $scope.changes.unshift(change);
        }
      });
    }

    stream = Stream($scope, '/api/0/changes/');
    stream.subscribe('change.update', addChange);
  }]);
});
