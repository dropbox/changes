(function(){
  'use strict';

  define(['app', 'directives/radialProgressBar', 'directives/timeSince'], function(app) {
    app.controller('changeListCtrl', ['$scope', 'initialData', '$http', 'stream', function($scope, initialData, $http, Stream) {
      var stream,
          entrypoint = '/api/0/changes/';

      $scope.changes = initialData.data.changes;

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

      stream = new Stream($scope, entrypoint);
      stream.subscribe('change.update', addChange);
    }]);
  });
})();
