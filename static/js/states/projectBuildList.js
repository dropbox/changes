define([
  'app',
  'utils',
  'utils/chartHelpers',
  'utils/escapeHtml',
  'utils/sortBuildList'
], function(app, utils, chartHelpers, escapeHtml, sortBuildList) {
  'use strict';

  var PER_PAGE = 50;

  function getEndpoint($stateParams, options) {
    if (options === undefined) {
      options = {};
    }

    var per_page = options.per_page || PER_PAGE;
    var url = '/api/0/projects/' + $stateParams.project_id + '/builds/?per_page=' + per_page;

    if ($stateParams.query) {
      url += '&query=' + $stateParams.query;
    }

    if ($stateParams.result) {
      url += '&result=' + $stateParams.result;
    }

    if ($stateParams.source) {
      url += '&source=' + $stateParams.source;
    }

    if ($stateParams.author) {
      url += '&author=' + $stateParams.author;
    }

    return url;
  }

  return {
    parent: 'project_details',
    url: 'builds/?query&result&source&author',
    templateUrl: 'partials/project-build-list.html',
    controller: function($scope, $state, $stateParams, flash,
                         Collection, CollectionPoller, Paginator, PageTitle, projectData) {
      var chart_options = {
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
            content += '<p>' + utils.time.duration(item.duration) + ' build time';
          } else if ($scope.selectedChart == 'test_rerun_count') {
            content += '<p>' + (item.stats.test_rerun_count || 0) + ' total retries';
          } else if ($scope.selectedChart == 'tests_missing') {
            content += '<p>' + (item.stats.tests_missing || 0) + ' job steps missing tests';
          }

          return content;
        },
        limit: PER_PAGE
      };

      function selectChart(chart) {
        if (chart) {
          $scope.selectedChart = chart;
        }
        $scope.chartData = chartHelpers.getChartData(collection, null, chart_options);
      }

      var collection = new Collection([], {
        sortFunc: sortBuildList,
        limit: PER_PAGE,
        onUpdate: $scope.selectChart
      });

      var poller = new CollectionPoller({
        $scope: $scope,
        collection: collection,
        endpoint: getEndpoint($stateParams, {per_page: 25}),
        shouldUpdate: function(item, existing) {
          if (existing.dateModified < item.dateModified) {
            return true;
          }
          return false;
        }
      });

      var paginator = new Paginator(getEndpoint($stateParams), {
        collection: collection,
        poller: poller,
        onLoadError: function(url, data){
          if (data.message) {
            flash('error', data.message);
          } else {
            flash('error');
          }
        },
      });

      PageTitle.set(projectData.name + ' Builds');

      $scope.getBuildStatus = function(build) {
        if (build.status.id == 'finished') {
          return build.result.name;
        } else {
          return build.status.name;
        }
      };

      if ($stateParams.author) {
        var activeUser = ($scope.activeUser) ? $scope.activeUser.email : null;
        if ($stateParams.author == 'me' || $stateParams.author == activeUser) {
          $scope.authorName  = 'me';
        } else {
          $scope.authorName = $stateParams.author;
        }
      }

      $scope.selectChart = selectChart;
      $scope.selectChart('duration');

      $scope.buildList = collection;
      $scope.buildPaginator = paginator;

    }
  };
});
