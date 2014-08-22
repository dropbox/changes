define([
  'app'
], function(app) {
  'use strict';

  return {
    abstract: true,
    parent: 'admin_layout',
    url: 'projects/:project_id/',
    templateUrl: 'partials/admin/project-details.html',
    controller: function($scope, projectData) {
      $scope.project = projectData;
      $scope.repo = projectData.repository;
    },
    resolve: {
      projectData: function($http, $stateParams) {
        return $http.get('/api/0/projects/' + $stateParams.project_id + '/')
          .then(function(response){
            return response.data;
          });
      }
    }
  };
});
