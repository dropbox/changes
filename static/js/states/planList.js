define(['app'], function(app) {
  'use strict';

  return {
    parent: 'layout',
    url: '/plans/',
    templateUrl: 'partials/plan-list.html',
    controller: function($scope, planList, Collection) {
      $scope.plans = new Collection($scope, planList.data);
    },
    resolve: {
      planList: function($http) {
        return $http.get('/api/0/plans/');
      }
    }
  };
});
