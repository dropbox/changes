(function(){
  'use strict';

  define([
      'app',
      'utils/escapeHtml'], function(app, escapeHtml) {
    app.controller('projectSettingsCtrl', [
        '$scope', '$rootScope', 'initialProject', '$http', '$routeParams',
        function($scope, $rootScope, initialProject, $http, $routeParams) {

      var booleans = {"mail.notify-authors": 1, "build.allow-patches": 1};
      var options = {};
      for (var k in initialProject.data.options) {
        var bits = k.split('.');
        var group = bits[0];
        var key = bits[1];
        var value = initialProject.data.options[k];
        if (booleans[k]) {
          value = parseInt(value, 10) == 1;
        }

        if (!options[group]) {
          options[group] = {};
        }
        options[group][key.replace(/-/g, '_')] = value;
      }

      $scope.project = initialProject.data;
      $scope.repo = initialProject.data.repository;
      $scope.plans = initialProject.data.plans;
      $scope.options = options;
      $rootScope.activeProject = $scope.project;
    }]);
  });
})();
