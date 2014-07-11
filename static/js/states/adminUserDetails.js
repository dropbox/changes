/*jshint -W024 */

define(['app'], function(app) {
  'use strict';

  function getFormData(userData) {
    return {
      isAdmin: userData.isAdmin
    };
  }

  return {
    parent: 'admin_layout',
    url: 'users/:user_id/',
    templateUrl: 'partials/admin/user-details.html',
    controller: function($http, $scope, userData, flash) {
      $scope.user = userData;
      $scope.formData = getFormData(userData);

      $scope.saveForm = function() {
        $http.post('/api/0/users/' + userData.id + '/', $scope.formData)
          .success(function(data){
            $scope.user = data;
            $scope.formData = getFormData(data);
            $scope.userDetailsForm.$setPristine();
            flash('success', 'User saved successfully.');
          })
          .error(function(){
            flash('error', 'An error ocurred, and we have yet to implement a way to tell you about it.');
          });
      };
    },
    resolve: {
      userData: function($http, $stateParams) {
        return $http.get('/api/0/users/' + $stateParams.user_id + '/')
          .then(function(response){
            return response.data;
          });
      }
    }
  };
});
