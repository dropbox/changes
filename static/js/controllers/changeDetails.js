(function(){
  'use strict';

  define(['app'], function(app) {
    app.controller('changeDetailsCtrl', ['$scope', 'initialData', '$http', '$stateParams', 'stream', function($scope, initialData, $http, $stateParams, Stream) {
      var stream,
          entrypoint = '/api/0/changes/' + $stateParams.change_id + '/';

      $scope.change = initialData.data.change;

      function updateChange(data){
        $scope.$apply(function() {
          $scope.change = data;
        });
      }

      stream = new Stream($scope, entrypoint);
      stream.subscribe('change.update', updateChange);

    }]);
  });
})();
