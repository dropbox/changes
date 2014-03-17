define([
  'app',
  'utils/duration',
  'utils/escapeHtml'
], function(app, duration, escapeHtml) {
  'use strict';

  return {
    parent: 'job_details',
    url: 'tests/:testgroup_id/',
    templateUrl: 'partials/testgroup-details.html',
    controller: function($scope, $rootScope, buildData, testGroupData) {
      var stream,
          entrypoint = '/api/0/testgroups/' + testGroupData.id + '/';

      $scope.testGroup = testGroupData;
      $scope.testGroup.build = buildData;
      $scope.testFailures = testGroupData.testFailures;
      $scope.childTestGroups = testGroupData.childTestGroups;
      $scope.testCase = testGroupData.testCase;
      $scope.context = testGroupData.context;
    },
    resolve: {
      testGroupData: function($http, $stateParams) {
        return $http.get('/api/0/testgroups/' + $stateParams.testgroup_id + '/').then(function(response){
          return response.data;
        });
      }
    }
  };
});
