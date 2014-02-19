(function(){
  'use strict';

  define(['app'], function(app) {
    app.controller('projectCreateCtrl', [
        '$scope', '$rootScope', '$http', '$location',
        function($scope, $rootScope, $http, $location) {

        $scope.createProject = function() {
          $http.post('/api/0/projects/', $scope.project)
            .success(function(data){
              return $location.path('/projects/' + data.slug + '/');
            });
        };

        $scope.project = {};

    }]);
  });
})();
