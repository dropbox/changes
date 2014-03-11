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
          entrypoint = '/api/0/testgroups/' + testGroupData.data.id + '/';

      $scope.testGroup = testGroupData.data;
      $scope.testGroup.build = buildData.data;
      $scope.testFailures = testGroupData.data.testFailures;
      $scope.childTestGroups = testGroupData.data.childTestGroups;
      $scope.testCase = testGroupData.data.testCase;
      $scope.context = testGroupData.data.context;
    },
    resolve: {
      testGroupData: function($http, $stateParams) {
        return $http.get('/api/0/testgroups/' + $stateParams.testgroup_id + '/');
      }
    }
  };
});
