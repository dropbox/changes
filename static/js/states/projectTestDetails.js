define([
  'app',
  'utils',
  'utils/chartHelpers',
  'utils/escapeHtml'
], function(app, utils, chartHelpers, escapeHtml) {
  'use strict';

  var HISTORICAL_ITEMS = 100;

  return {
    parent: 'project_details',
    url: 'tests/:test_id/',
    templateUrl: 'partials/project-test-details.html',
    controller: function($scope, $state, testData, historicalData) {
      var chart_options = {
          linkFormatter: function(item) {
            return $state.href('build_details', {build_id: item.job.build.id});
          },
          tooltipFormatter: function(item) {
            var content = '';
            var build = item.job.build;

            content += '<h5>';
            content += escapeHtml(build.name);
            content += '<br><small>';
            content += escapeHtml(build.target);
            if (build.author) {
              content += ' &mdash; ' + build.author.name;
            }
            content += '</small>';
            content += '</h5>';
            content += '<p>Test ' + item.result.name;
            if (item.duration) {
              content += ' in ' + utils.time.duration(item.duration);
            }
            content += ' (Build ' + build.result.name + ')</p>';

            return content;
          },
          limit: HISTORICAL_ITEMS
        };

      $scope.test = testData;
      $scope.results = historicalData;
      $scope.chartData = chartHelpers.getChartData($scope.results, null, chart_options);
    },
    resolve: {
      testData: function($http, $stateParams, projectData) {
        return $http.get('/api/0/projects/' + projectData.id + '/tests/' + $stateParams.test_id + '/').then(function(response){
          return response.data;
        });
      },
      historicalData: function($http, $stateParams, projectData) {
        return $http.get('/api/0/projects/' + projectData.id + '/tests/' + $stateParams.test_id + '/history/?per_page=' + HISTORICAL_ITEMS).then(function(response){
          return response.data;
        });
      }
    }
  };
});
