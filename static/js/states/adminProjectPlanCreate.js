define(['app'], function(app) {
  'use strict';

  return {
    parent: 'admin_project_details',
    url: 'new/plan/',
    templateUrl: 'partials/admin/project-plan-create.html',
    controller: function($scope, $http, $state, $stateParams, projectData) {
      $scope.createPlan = function() {
        $http.post('/api/0/projects/' + $stateParams.project_id + '/plans/', $scope.plan)
          .success(function(data){
            return $state.go('admin_project_plan_details', {plan_id: data.id});
          }).error(function(data){
            alert('An error ocurred, and we have yet to implement a way to tell you about it.');
          });
      };

      $scope.plan = {};
      $scope.project = projectData;
    }
  };
});
