define(['app'], function(app) {
  'use strict';

  app.controller('projectBuildCreateCtrl', [
      '$scope', '$rootScope', '$http', '$location', 'initialProject', 'flash',
      function($scope, $rootScope, $http, $location, initialProject, flash) {

      $scope.createBuild = function() {
        var data = angular.copy($scope.build);

        data.project = $scope.project.slug;

        $http.post('/api/0/builds/', data)
          .success(function(data){
            var builds = data.builds;

            if (builds.length === 0) {
              flash('error', 'Unable to create a new build.');
            } else if (builds.length > 1) {
              flash('success', builds.length + ' new builds created.');
              return $location.path('/projects/' + $scope.project.slug + '/');
            } else {
              return $location.path('/builds/' + builds[0].id + '/');
            }
          })
          .error(function(){
            flash('error', 'Unable to create a new build.');
          });
      };

      $rootScope.activeProject = initialProject.data;
      $scope.project = initialProject.data;
      $scope.build = {};
  }]);
});
