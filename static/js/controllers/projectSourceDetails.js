(function(){
  'use strict';

  define(['app'], function(app) {
    app.controller('projectSourceDetailsCtrl', [
        '$scope', '$rootScope', '$http', 'initialProject', 'initialSource',
        function($scope, $rootScope, $http, initialProject, initialSource) {

      $scope.project = initialProject.data;
      $scope.source = initialSource.data;
      $rootScope.activeProject = $scope.project;
    }]);
  });
})();
