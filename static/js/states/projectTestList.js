define([
  'app',
  'utils/chartHelpers',
  'utils/duration',
  'utils/escapeHtml',
  'utils/parseLinkHeader'
], function(app, chartHelpers, duration, escapeHtml, parseLinkHeader) {
  'use strict';

  return {
    parent: 'project_details',
    url: 'tests/',
    templateUrl: 'partials/project-test-list.html',
    controller: function($http, $scope, $state, buildList, testList) {
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
                content += '<p>' + parseInt(item.stats.test_duration / item.stats.test_count || 0, 10) + 's avg test duration';
              } else if ($scope.selectedChart == 'retries') {
                content += '<p>' + (item.stats.test_rerun_count || 0) + ' total retries';
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
            $scope.testList = data;
            $scope.pageLinks = parseLinkHeader(headers('Link'));
          });
      }

      $scope.loadPreviousPage = function() {
        $(document.body).scrollTop(0);
        loadTestList($scope.pageLinks.previous);
      };

      $scope.loadNextPage = function() {
        $(document.body).scrollTop(0);
        loadTestList($scope.pageLinks.next);
      };

      $scope.$watch("pageLinks", function(value) {
        $scope.nextPage = value.next || null;
        $scope.previousPage = value.previous || null;
      });

      $scope.pageLinks = parseLinkHeader(testList.headers('Link'));
      $scope.testList = testList.data;
      $scope.selectChart = function(chart) {
        $scope.selectedChart = chart;
        $scope.chartData = chartHelpers.getChartData(buildList, null, chart_options);
      };
      $scope.selectChart('count');

    },
    resolve: {
      testList: function($http, projectData) {
        return $http.get('/api/0/projects/' + projectData.id + '/tests/');
      },
      buildList: function($http, projectData) {
        return $http.get('/api/0/projects/' + projectData.id + '/builds/?include_patches=0').then(function(response){
          return response.data;
        });
      }
    }
  };
});
