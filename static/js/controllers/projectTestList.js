(function(){
  'use strict';

  define([
      'app',
      'utils/duration',
      'directives/timeSince'], function(app, duration) {
    app.controller('projectTestListCtrl', [
        '$scope', '$rootScope', 'initialProject', 'initialTests',
        function($scope, $rootScope, initialProject, initialTests) {
      $scope.project = initialProject.data;
      $scope.tests = initialTests.data.tests;
      $rootScope.activeProject = $scope.project;
    }]);
  });
})();
