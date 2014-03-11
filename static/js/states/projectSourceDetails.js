define([
  'app',
  'utils/sortBuildList'
], function(app, sortBuildList) {
  'use strict';

  return {
    parent: 'project_details',
    url: 'sources/:source_id/',
    templateUrl: 'partials/project-source-details.html',
    controller: function($scope, $http, sourceData, buildList) {
      $scope.getBuildStatus = function(build) {
        if (build.status.id == 'finished') {
          return build.result.name;
        } else {
          return build.status.name;
        }
      };

      $scope.source = sourceData.data;
      $scope.builds = sortBuildList(buildList.data);
    },
    resolve: {
      sourceData: function($http, $stateParams, projectData) {
        return $http.get('/api/0/projects/' + projectData.data.id + '/sources/' + $stateParams.source_id + '/');
      },
      buildList: function($http, $stateParams, projectData) {
        return $http.get('/api/0/projects/' + projectData.data.id + '/sources/' + $stateParams.source_id + '/builds/');
      }
    }
  };
});
