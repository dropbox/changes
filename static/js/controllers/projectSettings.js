(function(){
  'use strict';

  define([
      'app',
      'utils/escapeHtml'], function(app, escapeHtml) {
    app.controller('projectSettingsCtrl', [
        '$scope', '$rootScope', 'initialProject', '$http', '$routeParams',
        function($scope, $rootScope, initialProject, $http, $routeParams) {

      $scope.project = initialProject.data;
      $scope.repo = initialProject.data.repository;
      $scope.plans = initialProject.data.plans;
      $rootScope.activeProject = $scope.project;
    }]);
  });
})();
