define(['app'], function(app) {
  'use strict';

  return {
    parent: 'plans',
    url: ':plan_id/',
    templateUrl: 'partials/plan-details.html',
    controller: function($scope, planData, Collection) {
      $scope.plan = planData.data;
      $scope.projectList = new Collection($scope, planData.data.projects);
      $scope.stepList = new Collection($scope, planData.data.steps);
    },
    resolve: {
      planData: function($http, $stateParams) {
        return $http.get('/api/0/plans/' + $stateParams.plan_id + '/');
      }
    }
  };
});
