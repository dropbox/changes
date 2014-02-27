(function(){
  'use strict';

  define([
      'app',
      'utils/duration',
      'utils/escapeHtml'], function(app, duration, escapeHtml) {
    app.controller('testGroupDetailsCtrl', [
          '$scope', '$rootScope', 'initialData', '$stateParams',
          function($scope, $rootScope, initialData, $stateParams) {
      var stream,
          entrypoint = '/api/0/testgroups/' + $stateParams.testgroup_id + '/';

      $scope.project = initialData.data.project;
      $scope.build = initialData.data.build;
      $scope.job = initialData.data.job;
      $scope.testFailures = initialData.data.testFailures;
      $scope.testGroup = initialData.data.testGroup;
      $scope.testGroup.build = $scope.build;
      $scope.childTestGroups = initialData.data.childTestGroups;
      $scope.testCase = initialData.data.testCase;
      $scope.context = initialData.data.context;

      $rootScope.activeProject = $scope.project;
    }]);
  });
})();
