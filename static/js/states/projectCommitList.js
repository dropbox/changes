define([
  'app',
  'utils/chartHelpers',
  'utils/duration',
  'utils/escapeHtml',
  'utils/parseLinkHeader',
  'utils/sortBuildList'
], function(app, chartHelpers, duration, escapeHtml, parseLinkHeader, sortBuildList) {
  'use strict';

  var PER_PAGE = 50;

  var COLLECTION_OPTIONS = {
    equals: function(item, other) {
      return item.repository_id == other.repository_id && item.sha == other.sha;
    },
    limit: PER_PAGE
  };

  function getEndpoint($stateParams) {
    var url = '/api/0/projects/' + $stateParams.project_id + '/commits/?per_page=' + PER_PAGE;
    return url;
  }

  return {
    parent: 'project_details',
    url: 'commits/',
    templateUrl: 'partials/project-commit-list.html',
    controller: function($http, $scope, $state, $stateParams, Collection, CollectionPoller,
                         commitList) {
      var chart_options = {
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

      function updatePageLinks(links) {
        var value = parseLinkHeader(links);

        $scope.pageLinks = value;
        $scope.nextPage = value.next || null;
        $scope.previousPage = value.previous || null;

        if (value.previous) {
          poller.stop();
        } else {
          poller.start();
        }
      }

      function loadCommitList(url) {
        if (!url) {
          return;
        }
        $http.get(url)
          .success(function(data, status, headers){
            $scope.commits = new Collection(fromCommits(data), COLLECTION_OPTIONS);
            updatePageLinks(headers('Link'));
          });
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

      function fromCommits(commitList) {
        return commitList.map(function(commit){
          commit.subject = getCommitSubject(commit);
          return commit;
        });
      }

      $scope.selectChart = function(chart) {
        $scope.selectedChart = chart;
        $scope.chartData = chartHelpers.getChartData($scope.commits, null, chart_options);
      };

      $scope.selectedChart = 'duration';
      $scope.$watchCollection("commits", function(value) {
        $scope.chartData = chartHelpers.getChartData(value, null, chart_options);
      });

      $scope.loadPreviousPage = function() {
        $(document.body).scrollTop(0);
        loadCommitList($scope.pageLinks.previous);
      };

      $scope.loadNextPage = function() {
        $(document.body).scrollTop(0);
        loadCommitList($scope.pageLinks.next);
      };

      $scope.commits = new Collection(fromCommits(commitList.data), COLLECTION_OPTIONS);

      var poller = new CollectionPoller({
        $scope: $scope,
        collection: $scope.commits,
        endpoint: '/api/0/projects/' + $stateParams.project_id + '/commits/?per_page=25',
        transform: function(response) {
          return fromCommits(response);
        },
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

      updatePageLinks(commitList.headers('Link'));
    },
    resolve: {
      commitList: function($http, $stateParams) {
        return $http.get(getEndpoint($stateParams));
      }
    }
  };
});
