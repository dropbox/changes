define([
  'app',
  'utils/chartHelpers',
  'utils/duration',
  'utils/escapeHtml',
  'utils/sortBuildList'
], function(app, chartHelpers, duration, escapeHtml, sortBuildList) {
  'use strict';

  var PER_PAGE = 50;

  function getEndpoint($stateParams) {
    var url = '/api/0/projects/' + $stateParams.project_id + '/commits/?per_page=' + PER_PAGE;
    return url;
  }

  function getCommitSubject(commit) {
    if (commit.message) {
      return commit.message.split('\n')[0].substr(0, 128);
    } else if (commit.build) {
      return commit.build.label;
    } else {
      return 'A homeless commit';
    }
  }

  return {
    parent: 'project_details',
    url: 'commits/',
    templateUrl: 'partials/project-commit-list.html',
    controller: function($scope, $state, $stateParams, Collection, CollectionPoller,
                         Paginator, PageTitle, projectData) {
      var chartOptions = {
        linkFormatter: function(item) {
          if (item.build) {
            return $state.href('build_details', {build_id: item.build.id});
          }
        },
        limit: 50,
        className: function(item) {
          if (item.build) {
            return 'result-' + item.build.result.id;
          } else {
            return 'result-unknown';
          }
        },
        value: function(item) {
          if (item.build) {
            if ($scope.selectedChart == 'test_count') {
              return item.build.stats.test_count;
            } else if ($scope.selectedChart == 'duration') {
              return item.build.duration;
            } else if ($scope.selectedChart == 'test_duration') {
              return item.build.stats.test_duration / item.build.stats.test_count;
            } else if ($scope.selectedChart == 'test_rerun_count') {
              return item.build.stats.test_rerun_count;
            } else if ($scope.selectedChart == 'tests_missing') {
              return item.build.stats.tests_missing;
            }
          } else {
            return 0;
          }
        },
        tooltipFormatter: function(item) {
          var content = '';

          content += '<h5>';
          content += escapeHtml(item.subject);
          content += '<br><small>';
          content += escapeHtml(item.id.substr(0, 12));
          if (item.author) {
            content += ' &mdash; ' + item.author.name;
          }
          content += '</small>';
          content += '</h5>';

          if (item.build) {
            if ($scope.selectedChart == 'test_count') {
              content += '<p>' + (item.build.stats.test_count || 0) + ' tests recorded';
            } else if ($scope.selectedChart == 'test_duration') {
              content += '<p>' + parseInt(item.build.stats.test_duration / item.build.stats.test_count || 0, 10) + 'ms avg test duration';
            } else if ($scope.selectedChart == 'duration') {
              content += '<p>' + duration(item.build.duration) + ' build time';
            } else if ($scope.selectedChart == 'test_rerun_count') {
              content += '<p>' + (item.build.stats.test_rerun_count || 0) + ' total retries';
            } else if ($scope.selectedChart == 'tests_missing') {
              content += '<p>' + (item.build.stats.tests_missing || 0) + ' job steps missing tests';
            }
          }

          return content;
        }
      };

      var collection = new Collection([], {
        limit: PER_PAGE,
        transform: function(data) {
          data.subject = getCommitSubject(data);
          return data;
        },
        equals: function(item, other) {
          return item.repository_id == other.repository_id && item.sha == other.sha;
        },
        onUpdate: function(value) {
          $scope.chartData = chartHelpers.getChartData(value, null, chartOptions);
        }
      });

      var poller = new CollectionPoller({
        $scope: $scope,
        collection: collection,
        endpoint: '/api/0/projects/' + $stateParams.project_id + '/commits/?per_page=25',
        shouldUpdate: function(item, existing) {
          if (!existing.build && !item.build) {
            return false;
          } else if (!existing.build) {
            return true;
          } else if (existing.build.dateCreated < item.build.dateCreated) {
            return true;
          } else if (existing.build.id == item.build.id &&
                     existing.build.dateModified < item.build.dateModified) {
            return true;
          }
        }
      });

      var paginator = new Paginator(getEndpoint($stateParams), {
        collection: collection,
        poller: poller,
        onLoadBegin: function(){
          $scope.loading = true;
        },
        onLoadComplete: function(){
          $scope.loading = false;
        }
      });

      PageTitle.set(projectData.name + ' Commits');

      $scope.loading = true;
      $scope.selectChart = function(chart) {
        $scope.selectedChart = chart;
        $scope.chartData = chartHelpers.getChartData(collection, null, chartOptions);
      };
      $scope.selectChart('duration');

      $scope.commitList = collection;
      $scope.commitPaginator = paginator;
    }
  };
});
