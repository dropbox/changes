(function(){
  'use strict';

  define([
      'app',
      'utils/escapeHtml'], function(app, escapeHtml) {
    app.controller('projectSettingsCtrl', [
        '$scope', '$rootScope', 'initialProject', '$http', '$stateParams',
        function($scope, $rootScope, initialProject, $http, $stateParams) {

      var booleans = {
        "build.allow-patches": 1,
        "green-build.notify": 1,
        "mail.notify-author": 1
      }, options = {};

      for (var key in initialProject.data.options) {
        var value = initialProject.data.options[key];
        if (booleans[key]) {
          value = parseInt(value, 10) == 1;
        }
        options[key] = value;
      }

      $scope.saveProjectSettings = function() {
        var options = angular.copy($scope.options);
        for (var key in options) {
          if (booleans[key]) {
            options[key] = options[key] ? '1' : '0';
          }
        }
        $http.post('/api/0/projects/' + $scope.project.slug + '/options/', options);
        $scope.projectSettingsForm.$setPristine();
      };

      $scope.project = initialProject.data;
      $scope.repo = initialProject.data.repository;
      $scope.plans = initialProject.data.plans;
      $scope.options = options;

      $rootScope.activeProject = $scope.project;
    }]);
  });
})();
