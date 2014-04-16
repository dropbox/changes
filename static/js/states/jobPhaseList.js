define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'job_details',
    url: 'phases/',
    templateUrl: 'partials/job-phase-list.html',
    controller: function($scope, phaseList) {
      $scope.phaseList = phaseList;
    },
    resolve: {
      phaseList: function($http, $stateParams) {
        return $http.get('/api/0/jobs/' + $stateParams.job_id + '/phases/').then(function(response){
          return response.data;
        });
      }
    }
  };
});
