define([
  'app',
  'utils/createBuild'
], function(app, createBuild) {
  'use strict';

  return {
    parent: 'project_details',
    url: "new/build/",
    templateUrl: 'partials/project-build-create.html',
    controller: function($scope, $rootScope, $http, $state, flash, projectData) {
      $scope.startBuild = function() {
        var buildData = angular.copy($scope.build);
        buildData.project = projectData.slug;

        createBuild($http, $state, flash, buildData);
      };

      $scope.build = {};
    }
  };
});
