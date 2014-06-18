define([
  'app'
], function(app) {
  'use strict';

  return {
    abstract: true,
    parent: 'layout',
    url: '/projects/:project_id/',
    templateUrl: 'partials/project-details.html',
    controller: function($document, $scope, $rootScope, features, projectData, PageTitle) {
      PageTitle.set(projectData.name);

      $scope.features = features;
      $scope.project = projectData;

      var stats = projectData.stats;
      if (stats.greenPercent && stats.previousGreenPercent !== null) {
        stats.greenPercentChange = stats.greenPercent - stats.previousGreenPercent;
      } else if (stats.previousGreenPercent !== null) {
        stats.greenPercentChange = -stats.previousGreenPercent;
      } else {
        stats.greenPercentChange = null;
      }

      if (stats.avgDuration && stats.previousAvgDuration) {
        stats.avgDurationChange = stats.avgDuration - stats.previousAvgDuration;
      } else {
        stats.avgDurationChange = null;
      }

      $rootScope.activeProject = $scope.project;
      $rootScope.activeProjectFeatures = $scope.features;
    },
    resolve: {
      projectData: function($http, $location, $stateParams) {
        return $http.get('/api/0/projects/' + $stateParams.project_id + '/').error(function(){
          $location.path('/');
        }).then(function(response){
          return response.data;
        });
      },
      features: function($q, projectData) {
        var deferred = $q.defer();
        deferred.resolve({
          coverage: (projectData.options['ui.show-coverage'] == '1'),
          tests: (projectData.options['ui.show-tests'] == '1')
        });
        return deferred.promise;
      }
    }
  };
});
