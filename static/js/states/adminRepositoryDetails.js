/*jshint -W024 */

define(['app'], function(app) {
  'use strict';

  function getFormData(repositoryData) {
    return {
      url: repositoryData.url,
      backend: repositoryData.backend.id
    };
  }

  return {
    parent: 'admin_layout',
    url: 'repositories/:repository_id/',
    templateUrl: 'partials/admin/repository-details.html',
    controller: function($http, $scope, repositoryData, flash) {
      $scope.repository = repositoryData;
      $scope.formData = getFormData(repositoryData);

      $scope.saveForm = function() {
        $http.post('/api/0/repositories/' + repositoryData.id + '/', $scope.formData)
          .success(function(data){
            $scope.repository = data;
            $scope.formData = getFormData(data);
            $scope.repositoryDetailsForm.$setPristine();
          });
      };
    },
    resolve: {
      repositoryData: function($http, $stateParams) {
        return $http.get('/api/0/repositories/' + $stateParams.repository_id + '/')
          .then(function(response){
            return response.data;
          });
      }
    }
  };
});
