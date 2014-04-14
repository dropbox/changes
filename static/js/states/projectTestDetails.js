define([
  'app',
  'utils/chartHelpers',
  'utils/duration',
  'utils/escapeHtml'
], function(app, chartHelpers, duration, escapeHtml) {
  'use strict';

  return {
    parent: 'project_details',
    url: 'tests/:test_id/',
    templateUrl: 'partials/project-test-details.html',
    controller: function($scope, testData) {
      var chart_options = {
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
              content += ' in ' + duration(item.duration);
            }
            content += ' (Build ' + build.result.name + ')</p>';

            return content;
          }
        };

      $scope.test = testData;
      $scope.results = testData.results;
      $scope.chartData = chartHelpers.getChartData($scope.results, null, chart_options);
    },
    resolve: {
      testData: function($http, $stateParams, projectData) {
        return $http.get('/api/0/projects/' + projectData.id + '/tests/' + $stateParams.test_id + '/').then(function(response){
          return response.data;
        });
      }
    }
  };
});
