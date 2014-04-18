define([
  'app',
  'utils/chartHelpers',
  'utils/duration',
  'utils/escapeHtml'
], function(app, chartHelpers, duration, escapeHtml) {
  'use strict';

  return {
    parent: 'project_details',
    url: 'tests/?parent',
    templateUrl: 'partials/project-test-list.html',
    controller: function($http, $scope, $state, $stateParams, buildList, projectData, testGroupData) {
      var chart_options = {
            linkFormatter: function(item) {
              return $state.href('build_details', {build_id: item.id});
            },
            value: function(item) {
              if ($scope.selectedChart == 'count') {
                return item.stats.test_count;
              } else if ($scope.selectedChart == 'duration') {
                return item.stats.test_duration / item.stats.test_count;
              } else if ($scope.selectedChart == 'retries') {
                return item.stats.test_rerun_count;
              } else if ($scope.selectedChart == 'missing') {
                return item.stats.tests_missing;
              }
            },
            tooltipFormatter: function(item) {
              var content = '';

              content += '<h5>';
              content += escapeHtml(item.name);
              content += '<br><small>';
              content += escapeHtml(item.target);
              if (item.author) {
                content += ' &mdash; ' + item.author.name;
              }
              content += '</small>';
              content += '</h5>';
              if ($scope.selectedChart == 'count') {
                content += '<p>' + (item.stats.test_count || 0) + ' tests recorded';
              } else if ($scope.selectedChart == 'duration') {
                content += '<p>' + parseInt(item.stats.test_duration / item.stats.test_count || 0, 10) + 'ms avg test duration';
              } else if ($scope.selectedChart == 'retries') {
                content += '<p>' + (item.stats.test_rerun_count || 0) + ' total retries';
              } else if ($scope.selectedChart == 'missing') {
                content += '<p>' + (item.stats.tests_missing || 0) + ' job steps missing tests';
              }
              return content;
            }
          };

      function loadTestList(url) {
        if (!url) {
          return;
        }
        $http.get(url)
          .success(function(data, status, headers){
            $scope.testGroupList = data.groups;
            $scope.trail = data.trail;
          });
      }

      $scope.selectChart = function(chart) {
        $scope.selectedChart = chart;
        $scope.chartData = chartHelpers.getChartData(buildList, null, chart_options);
      };

      $scope.selectChart('count');

      $scope.testGroupList = testGroupData.data.groups;
      $scope.trail = testGroupData.data.trail;
    },
    resolve: {
      testGroupData: function($http, $stateParams, projectData) {
        return $http.get('/api/0/projects/' + projectData.id + '/testgroups/?parent=' + ($stateParams.parent || ''));
      },
      buildList: function($http, projectData) {
        return $http.get('/api/0/projects/' + projectData.id + '/builds/?include_patches=0').then(function(response){
          return response.data;
        });
      }
    }
  };
});
