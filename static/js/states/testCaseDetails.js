define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'job_details',
    url: 'tests/:test_id/',
    templateUrl: 'partials/test-details.html',
    controller: function($scope, buildData, testData) {
      $scope.testCase = testData;
      $scope.testCase.build = buildData;
    },
    resolve: {
      testData: function($http, $stateParams) {
        return $http.get('/api/0/tests/' + $stateParams.test_id + '/').then(function(response){
          return response.data;
        });
      }
    }
  };
});
