define([
  'app',
  'utils/chartHelpers',
  'utils/duration',
  'utils/escapeHtml',
  'utils/parseLinkHeader',
  'utils/sortBuildList'
], function(app, chartHelpers, duration, escapeHtml, parseLinkHeader, sortBuildList) {
  'use strict';

  return {
    parent: 'project_details',
    url: '',
    templateUrl: 'partials/project-build-list.html',
    controller: function($scope, $http, $state, projectData, buildList, stream, Collection, PageTitle) {
      var entrypoint = '/api/0/projects/' + projectData.id + '/builds/',
          chart_options = {
            linkFormatter: function(item) {
              return $state.href('build_details', {build_id: item.id});
            },
            value: function(item) {
              if ($scope.selectedChart == 'test_count') {
                return item.stats.test_count;
              } else if ($scope.selectedChart == 'duration') {
                return item.duration;
              } else if ($scope.selectedChart == 'test_duration') {
                return item.stats.test_duration / item.stats.test_count;
              } else if ($scope.selectedChart == 'test_rerun_count') {
                return item.stats.test_rerun_count;
              } else if ($scope.selectedChart == 'tests_missing') {
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

              if ($scope.selectedChart == 'test_count') {
                content += '<p>' + (item.stats.test_count || 0) + ' tests recorded';
              } else if ($scope.selectedChart == 'test_duration') {
                content += '<p>' + parseInt(item.stats.test_duration / item.stats.test_count || 0, 10) + 'ms avg test duration';
              } else if ($scope.selectedChart == 'duration') {
                content += '<p>' + duration(item.duration) + ' build time';
              } else if ($scope.selectedChart == 'test_rerun_count') {
                content += '<p>' + (item.stats.test_rerun_count || 0) + ' total retries';
              } else if ($scope.selectedChart == 'tests_missing') {
                content += '<p>' + (item.stats.tests_missing || 0) + ' job steps missing tests';
              }

              return content;
            }
          };

      function updatePageLinks(links) {
        var value = parseLinkHeader(links);

        $scope.pageLinks = value;
        $scope.nextPage = value.next || null;
        $scope.previousPage = value.previous || null;
      }

      $scope.getBuildStatus = function(build) {
        if (build.status.id == 'finished') {
          return build.result.name;
        } else {
          return build.status.name;
        }
      };

      function loadBuildList(url) {
        if (!url) {
          return;
        }
        $http.get(url)
          .success(function(data, status, headers){
            $scope.builds = new Collection($scope, data, {
              sortFunc: sortBuildList,
              limit: 100
            });
            updatePageLinks(headers('Link'));
          });
      }

      $scope.loadPreviousPage = function() {
        $(document.body).scrollTop(0);
        loadBuildList($scope.pageLinks.previous);
      };

      $scope.loadNextPage = function() {
        $(document.body).scrollTop(0);
        loadBuildList($scope.pageLinks.next);
      };

      updatePageLinks(buildList.headers('Link'));

      $scope.builds = new Collection($scope, buildList.data, {
        sortFunc: sortBuildList,
        limit: 100
      });

      $scope.selectChart = function(chart) {
        $scope.selectedChart = chart;
        $scope.chartData = chartHelpers.getChartData($scope.builds, null, chart_options);
      };
      $scope.selectChart('duration');

      $scope.includePatches = false;

      PageTitle.set(projectData.name + ' Builds');

      $scope.$watchCollection("builds", function() {
        $scope.chartData = chartHelpers.getChartData($scope.builds, null, chart_options);
      });

      stream.addScopedChannels($scope, [
        'projects:' + $scope.project.id + ':builds'
      ]);
      stream.addScopedSubscriber($scope, 'build.update', function(data){
        if (data.project.id != $scope.project.id) {
          return;
        }
        if (data.source.patch && !$scope.includePatches) {
          return;
        }
        $scope.builds.updateItem(data);
      });
    },
    resolve: {
      buildList: function($http, projectData) {
        return $http.get('/api/0/projects/' + projectData.id + '/builds/?include_patches=0');
      }
    }
  };
});
