define([
  'app',
  'moment',
  'utils/duration'
], function(app, moment, duration) {
  'use strict';

  return {
    parent: 'project_details',
    url: 'coverage/?parent',
    templateUrl: 'partials/project-coverage-list.html',
    controller: function($http, $scope, $state, $stateParams, projectData, fileCoverageData) {
      $scope.fileCoverageList = fileCoverageData.groups;
      $.each($scope.fileCoverageList, function(_, file_coverage){
        var percent, total_lines;
        if (file_coverage.totalLinesCovered === 0) {
          percent = 0;
        } else {
          total_lines = file_coverage.totalLinesCovered + file_coverage.totalLinesUncovered;
          percent = parseInt(file_coverage.totalLinesCovered / total_lines * 100, 10);
        }

        file_coverage.percent = percent;
      });
      $scope.trail = fileCoverageData.trail;
      $scope.overThreshold = fileCoverageData.overThreshold;
    },
    resolve: {
      fileCoverageData: function($http, $stateParams, projectData) {
        var url = '/api/0/projects/' + projectData.id + '/coveragegroups/?parent=' + ($stateParams.parent || '');
        return $http.get(url).then(function(response){
          return response.data;
        });
      }
    }
  };
});
