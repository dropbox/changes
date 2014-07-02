define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'admin_layout',
    url: 'projects/',
    templateUrl: 'partials/admin/project-list.html',
    controller: function($scope, Collection, projectList) {
      $scope.projects = new Collection(projectList);
    },
    resolve: {
      projectList: function($http) {
        return $http.get('/api/0/projects/')
          .then(function(response){
            return response.data;
          });
      }
    }
  };
});
