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
    url: 'tests/:test_id/?branch',
    templateUrl: 'partials/project-test-details.html',
    controller: function($scope, $state, $stateParams, flash, Collection, Paginator, projectData, testData) {
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

      $scope.branches = projectData.repository.branches.map(function(x){return x.name;});

      if ($stateParams.branch) $scope.branch = $stateParams.branch;
      else if ($scope.branches.indexOf("master") != -1) $scope.branch = "master";
      else if ($scope.branches.indexOf("default") != -1) $scope.branch = "default";
      else $scope.branch = $scope.branches[0];

      var historicalData = new Collection();
      var endpoint = '/api/0/projects/' + projectData.id + '/tests/' + $stateParams.test_id + '/history/?per_page=' + HISTORICAL_ITEMS + "&branch=" + $scope.branch;
        
      var paginator = new Paginator(endpoint, {
        collection: historicalData,
        onLoadSuccess: function(url, data) {
          $scope.chartData = chartHelpers.getChartData(historicalData, null, chart_options);
        },
        onLoadError: function(url, data) {
          if (data.error) {
            flash('error', data.error);
          } else {
            flash('error');
          }
        },
      });

      $scope.test = testData;
      $scope.results = historicalData;
      $scope.testPaginator = paginator;
    },
    resolve: {
      testData: function($http, $stateParams, projectData) {
        return $http.get('/api/0/projects/' + projectData.id + '/tests/' + $stateParams.test_id + '/').then(function(response){
          return response.data;
        });
      },
    }
  };
});

