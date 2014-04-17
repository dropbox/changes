define([
  'app',
  'utils/escapeHtml'
], function(app, escapeHtml) {
  'use strict';

  return {
    parent: 'project_details',
    url: 'settings/',
    templateUrl: 'partials/project-settings.html',
    controller: function($scope, $http, $stateParams, projectData) {
      var booleans = {
        "build.allow-patches": 1,
        "build.expect-tests": 1,
        "green-build.notify": 1,
        "mail.notify-author": 1,
        "hipchat.notify": 1
      }, options = {};

      for (var key in projectData.options) {
        var value = projectData.options[key];
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

      $scope.project = projectData;
      $scope.repo = projectData.repository;
      $scope.plans = projectData.plans;
      $scope.options = options;
    },
    resolve: {
      projectData: function($http, $stateParams) {
        return $http.get('/api/0/projects/' + $stateParams.project_id + '/').then(function(response){
          return response.data;
        });
      }
    }
  };
});
