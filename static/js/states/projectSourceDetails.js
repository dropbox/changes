define([
  'app',
  'utils/sortBuildList'
], function(app, sortBuildList) {
  'use strict';

  return {
    parent: 'project_details',
    url: 'sources/:source_id/',
    templateUrl: 'partials/project-source-details.html',
    controller: function($scope, $http, sourceData, buildList, Collection) {
      $scope.source = sourceData.data;
      $scope.builds = new Collection($scope, buildList.data, {
        sortFunc: sortBuildList,
        limit: 100
      });

      var diff = sourceData.data.diff;
      if (diff) {
        // If we have diff information, render coverage after the DOM loads.
        var coverage_list = sourceData.data.coverageForAddedLines;

        // The use of setTimeout here is a bit hacky, but it's pretty localized.
        setTimeout(function() {
          $("pre code .addition").each(function(index) {
            var coverage_type = null;

            if (coverage_list[index] == 'U') {
              coverage_type = 'negative-coverage';
            } else if (coverage_list[index] == 'C') {
              coverage_type = 'positive-coverage';
            } else if (coverage_list[index] == 'N') {
              coverage_type = 'unknown-coverage';
            } else {
              throw new Error("Unknown coverage type: " + coverage_type[index]);
            }

            $(this).addClass(coverage_type).prepend("<span class='coverage-info'> </span>");
          });
        });
      }
    },
    resolve: {
      sourceData: function($http, $stateParams, projectData) {
        return $http.get('/api/0/projects/' + projectData.id + '/sources/' + $stateParams.source_id + '/');
      },
      buildList: function($http, $stateParams, projectData) {
        return $http.get('/api/0/projects/' + projectData.id + '/sources/' + $stateParams.source_id + '/builds/');
      }
    }
  };
});
