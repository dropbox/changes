define([
  'app',
  'utils',
  'utils/chartHelpers',
  'utils/createBuild',
  'utils/escapeHtml',
  'utils/sortBuildList'
], function(app, utils, chartHelpers, createBuild, escapeHtml, sortBuildList) {
  'use strict';

  var PER_PAGE = 50;
  var GRG_PER_PAGE = 200;
  var MASTER_REPOSITORY = 'master';
  var DEFAULT_REPOSITORY = 'default';

  function getEndpoint($stateParams, per_page_size) {
    var url = '/api/0/projects/' + $stateParams.project_id + '/commits/?' +
              'per_page=' + per_page_size;

    if ($stateParams.branch) {
      url += '&branch=' + $stateParams.branch;
    }

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

  function ensureDefaults(lowercaseFunc, params, repository) {
    if (repository.branches && repository.branches.length > 0) {
      if (!params.branch) {
        params.branch = repository.defaultBranch;
      }
      params.branch = lowercaseFunc(params.branch);
    }
  }

  return {
    custom: {
      ensureDefaults: ensureDefaults,
    },
    parent: 'project_details',
    url: 'commits/?branch&grg',
    templateUrl: 'partials/project-commit-list.html',
    controller: function($scope, $http, $state, $stateParams, flash,
                         Collection, CollectionPoller, Paginator, PageTitle, projectData) {
      $scope.grg = ($stateParams.grg == "true");

      var perPage = PER_PAGE;
      if ($scope.grg) {
          perPage = GRG_PER_PAGE;
      }

      $scope.perPage = perPage;

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
              content += '<p>' + utils.time.duration(item.build.duration) + ' build time';
            } else if ($scope.selectedChart == 'test_rerun_count') {
              content += '<p>' + (item.build.stats.test_rerun_count || 0) + ' total retries';
            } else if ($scope.selectedChart == 'tests_missing') {
              content += '<p>' + (item.build.stats.tests_missing || 0) + ' job steps missing tests';
            }
          }

          return content;
        }
      };

      $scope.commitList = [];

      var collection = new Collection([], {
        limit: perPage,
        transform: function(data) {
          data.subject = getCommitSubject(data);
          return data;
        },
        equals: function(item, other) {
          return item.repository_id == other.repository_id && item.sha == other.sha;
        },
        onUpdate: function(list) {
          var i;

          if (list.length) {
            var startDate, endDate;

            for (i = 0; i < list.length; i++) {
              if (list[i].build) {
                endDate = new Date(list[i].build.dateCreated);
                break;
              }
            }

            for (i = list.length-1; i >= 0; i--) {
              if (list[i].build) {
                startDate = new Date(list[i].build.dateCreated);
                break;
              }
            }

            if (startDate && endDate) {
                $scope.startDate = moment(startDate).format('llll');
                $scope.endDate = moment(endDate).format('llll');
                $scope.intervalHours =
                  Math.round((endDate.getTime() - startDate.getTime()) / (60*60));
            }
          }

          if ($scope.grg) {
            var commitList = [];
            for (i = 1; i < list.length-1; i++) {
              var build = list[i].build;
              var prev_build = list[i+1].build;
              var next_build = list[i-1].build;
              if (prev_build && prev_build.result.id == 'passed' &&
                  build && build.result.id == 'failed' &&
                  next_build && next_build.result.id == 'passed') {
                list[i].prev_build = prev_build;
                list[i].next_build = next_build;
                commitList.push(list[i]);
              }
            }
            $scope.commitList = commitList;
          } else {
            $scope.commitList = collection;
            $scope.chartData = chartHelpers.getChartData(list, null, chartOptions);
          }
        }
      });

      var poller = new CollectionPoller({
        $scope: $scope,
        collection: collection,
        endpoint: getEndpoint($stateParams, perPage/2),
        shouldUpdate: function(item, existing) {
          if (!item.build) {
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

      var paginator = new Paginator(getEndpoint($stateParams, perPage), {
        collection: collection,
        poller: poller,
        onLoadBegin: function(){
          $scope.loading = true;
        },
        onLoadComplete: function(){
          $scope.loading = false;
        },
        onLoadError: function(url, data){
          if (data.error) {
            flash('error', data.error);
          } else {
            flash('error');
          }
        },
      });

      PageTitle.set(projectData.name + ' Commits');
      $scope.branch = $stateParams.branch;
      $scope.projectData = projectData;

      $scope.loading = true;

      $scope.startBuild = function(commit) {
        var buildData = {
          project: projectData.slug,
          sha: commit.sha
        };
        createBuild($http, $state, flash, buildData);
      };
      $scope.selectChart = function(chart) {
        $scope.selectedChart = chart;
        $scope.chartData = chartHelpers.getChartData(collection, null, chartOptions);
      };
      // We don't want to have a chart for G-R-G builds
      if (!$scope.grg) {
        $scope.selectChart('duration');
      }

      $scope.commitPaginator = paginator;
    },
    onEnter: function($filter, $stateParams, repositoryData) {
      ensureDefaults($filter('lowercase'), $stateParams, repositoryData);
    }
  };
});
