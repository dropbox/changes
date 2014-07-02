define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'admin_layout',
    url: 'repositories/',
    templateUrl: 'partials/admin/repository-list.html',
    controller: function($scope, Collection, repositoryList) {
      $scope.repositoryList = new Collection(repositoryList);
    },
    resolve: {
      repositoryList: function($http) {
        return $http.get('/api/0/repositories/')
          .then(function(response){
            return response.data;
          });
      }
    }
  };
});
