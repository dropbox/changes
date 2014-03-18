define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'project_details',
    url: "new/build/",
    templateUrl: 'partials/project-build-create.html',
    controller: function($scope, $rootScope, $http, $location, flash, projectData) {
      $scope.createBuild = function() {
        var buildData = angular.copy($scope.build);

        buildData.project = projectData.slug;

        $http.post('/api/0/builds/', buildData)
          .success(function(data){
            if (data.length === 0) {
              flash('error', 'Unable to create a new build.');
            } else if (data.length > 1) {
              flash('success', data.length + ' new builds created.');
              return $location.path('/projects/' + buildData.project + '/');
            } else {
              return $location.path('/builds/' + data[0].id + '/');
            }
          })
          .error(function(){
            flash('error', 'Unable to create a new build.');
          });
      };

      $scope.build = {};
    }
  };
});
