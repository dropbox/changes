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
        var data = angular.copy($scope.build);

        data.project = projectData.slug;

        $http.post('/api/0/builds/', data)
          .success(function(data){
            var builds = data.builds;

            if (builds.length === 0) {
              flash('error', 'Unable to create a new build.');
            } else if (builds.length > 1) {
              flash('success', builds.length + ' new builds created.');
              return $location.path('/projects/' + data.project + '/');
            } else {
              return $location.path('/builds/' + builds[0].id + '/');
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
