define(['app'], function(app) {
  'use strict';

  return {
    parent: 'layout',
    url: '/new/plan/',
    templateUrl: 'partials/plan-create.html',
    controller: function($scope, $http, $state) {
      $scope.createPlan = function() {
        $http.post('/api/0/plans/', $scope.plan)
          .success(function(data){
            return $state.go('plan_details', {plan_id: data.id});
          }).error(function(data){
            alert('An error ocurred, and we have yet to implement a way to tell you about it.');
          });
      };

      $scope.plan = {};
    }
  };
});
