(function(){
  'use strict';

  define(['app', 'utils/sortBuildList'], function(app, sortBuildList) {
    app.controller('projectSourceDetailsCtrl', [
        '$scope', '$rootScope', '$http', 'initialProject', 'initialSource', 'initialBuildList',
        function($scope, $rootScope, $http, initialProject, initialSource, initialBuildList) {

      $scope.getBuildStatus = function(build) {
        if (build.status.id == 'finished') {
          return build.result.name;
        } else {
          return build.status.name;
        }
      };

      $scope.project = initialProject.data;
      $scope.source = initialSource.data;
      $scope.builds = sortBuildList(initialBuildList.data);
      $rootScope.activeProject = $scope.project;
    }]);
  });
})();
