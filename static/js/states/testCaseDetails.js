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

      var filterArtifactsType = function(typeId) {
        return testData.artifacts.filter(function(a) {
          return a.type.id == typeId;
        });
      };

      $scope.testCase.textArtifacts = filterArtifactsType('text');
      $scope.testCase.htmlArtifacts = filterArtifactsType('html');
      $scope.testCase.imageArtifacts = filterArtifactsType('image');
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
