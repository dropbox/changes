define(['app'], function(app) {
  'use strict';

  return {
    parent: 'admin_layout',
    url: 'new/project/',
    templateUrl: 'partials/admin/project-create.html',
    controller: function($scope, $http, $state) {
      $scope.createProject = function() {
        $http.post('/api/0/projects/', $scope.project)
          .success(function(data){
            return $state.go('project_settings', {project_id: data.slug});
          });
      };

      $scope.project = {};
    }
  };
});
