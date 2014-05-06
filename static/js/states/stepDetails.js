define(['app'], function(app) {
  'use strict';

  return {
    parent: 'plan_details',
    url: 'steps/:step_id/',
    templateUrl: 'partials/step-details.html',
    controller: function($scope, stepData) {
      $scope.step = stepData;
    },
    resolve: {
      stepData: function($http, $stateParams) {
        return $http.get('/api/0/steps/' + $stateParams.step_id + '/').then(function(response){
          return response.data;
        });
      }
    }
  };
});
