define([
    'app',
    'utils/duration',
    'directives/timeSince'], function(app, duration) {
  app.controller('projectTestListCtrl', [
      '$scope', '$rootScope', 'initialProject', 'initialTests',
      function($scope, $rootScope, initialProject, initialTests) {
    'use strict';

    $scope.project = initialProject.data.project;
    $scope.tests = initialTests.data.tests;
    $rootScope.activeProject = $scope.project;
  }]);
});
