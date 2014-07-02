define(['app'], function(app) {
  'use strict';

  return {
    parent: 'admin_layout',
    url: 'new/repository/',
    templateUrl: 'partials/admin/repository-create.html',
    controller: function($http, $scope, $state, flash) {
      $scope.formData = {};

      $scope.saveForm = function() {
        $http.post('/api/0/repositories/', $scope.formData)
          .success(function(data){
            flash('success', 'Repository saved successfully.');
            return $state.go('admin_repository_details', {repository_id: data.id});
          }).error(function(data){
            flash('error', 'An error ocurred, and we have yet to implement a way to tell you about it.');
          });
      };
    }
  };
});
