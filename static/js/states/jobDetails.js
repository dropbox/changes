define([
  'app',
  'utils/chartHelpers',
  'utils/duration',
  'utils/escapeHtml'
], function(app, chartHelpers, duration, escapeHtml) {
  'use strict';

  var BUFFER_SIZE = 10000;

  return {
    url: "jobs/:job_id/",
    parent: 'build_details',
    templateUrl: 'partials/job-details.html',
    controller: function($scope, $rootScope, $http, $filter, projectData, buildData, jobData, stream, Pagination) {
      var logStreams = {},
          chart_options = {
            tooltipFormatter: function(item) {
              var content = '';

              content += '<h5>';
              content += escapeHtml(item.name);
              content += '<br><small>';
              content += escapeHtml(buildData.data.target);
              if (buildData.data.author) {
                content += ' &mdash; ' + buildData.data.author.name;
              }
              content += '</small>';
              content += '</h5>';
              if (item.status.id == 'finished') {
                content += '<p>Job ' + item.result.name;
                if (item.duration) {
                  content += ' in ' + duration(item.duration);
                }
                content += '</p>';
              } else {
                content += '<p>' + item.status.name + '</p>';
              }

              return content;
            }
          };

      function getLogSourceEntrypoint(jobId, logSourceId) {
        return '/api/0/jobs/' + jobId + '/logs/' + logSourceId + '/';
      }

      function updateBuildLog(data) {
        // Angular isn't intelligent enough to optimize this.
        var $el = $('#log-' + data.source.id + ' > .build-log'),
            item, source_id = data.source.id,
            chars_to_remove, lines_to_remove,
            frag;

        if ($el.length === 0) {
          // logsource isnt available in viewpane
          return;
        }

        if (!logStreams[source_id]) {
          return;
        }

        item = logStreams[source_id];
        if (data.offset < item.nextOffset) {
          return;
        }

        item.nextOffset = data.offset + data.size;

        if (item.size > BUFFER_SIZE) {
          $el.empty();
        } else {
          // determine how much space we need to clear up to append data.size
          chars_to_remove = 0 - (BUFFER_SIZE - item.size - data.size);

          if (chars_to_remove > 0) {
            // determine the number of actual lines to remove
            lines_to_remove = item.text.substr(0, chars_to_remove).split('\n').length;

            // remove number of lines (accounted by <div>'s)
            $el.find('div').slice(0, lines_to_remove - 1).remove();
          }
        }

        frag = document.createDocumentFragment();

        // add each additional new line
        $.each(data.text.split('\n'), function(_, line){
          var div = document.createElement('div');
          div.className = 'line';
          div.innerHTML = line;
          frag.appendChild(div);
        });


        item.text = (item.text + data.text).substr(-BUFFER_SIZE);
        item.size = item.text.length;

        $el.append(frag);

        if ($el.is(':visible')) {
          var el = $el.get(0);
          el.scrollTop = Math.max(el.scrollHeight, el.clientHeight) - el.clientHeight;
        }
      }

      $scope.loadLogSource = function(logSource){
        logStreams[logSource.id] = {
          text: '',
          size: 0,
          nextOffset: 0
        };

        $http.get(getLogSourceEntrypoint($scope.job.id, logSource.id) + '?limit=' + BUFFER_SIZE)
          .success(function(data){
            $.each(data.chunks, function(_, chunk){
              updateBuildLog(chunk);
            });
          });
      };

      function getFormattedBuildMessage(message) {
        return $filter('linkify')($filter('escape')(message));
      }

      function getTestStatus() {
        if ($scope.job.status.id == "finished") {
          if ($scope.testGroups.length === 0) {
            return "no-results";
          } else {
            return "has-results";
          }
        }
        return "pending";
      }

      function updateJob(data){
        $scope.$apply(function() {
          $scope.job = data;
        });
      }

      function updateTestGroup(data) {
        $scope.$apply(function() {
          var updated = false,
              item_id = data.id,
              attr, result, item;

          // TODO(dcramer); we need to refactor all of this logic as its repeated in nealry
          // every stream
          if ($scope.testGroups.length > 0) {
            result = $.grep($scope.testGroups, function(e){ return e.id == item_id; });
            if (result.length > 0) {
              item = result[0];
              for (attr in data) {
                // ignore dateModified as we're updating this frequently and it causes
                // the dirty checking behavior in angular to respond poorly
                if (item[attr] != data[attr] && attr != 'dateModified') {
                  updated = true;
                  item[attr] = data[attr];
                }
                if (updated) {
                  item.dateModified = data.dateModified;
                }
              }
            }
          }
          if (!updated) {
            $scope.testGroups.unshift(data);
          }

          if (data.result.id == 'failed') {
            if ($scope.testFailures.length > 0) {
              result = $.grep($scope.testFailures, function(e){ return e.id == item_id; });
              if (result.length > 0) {
                item = result[0];
                for (attr in data) {
                  // ignore dateModified as we're updating this frequently and it causes
                  // the dirty checking behavior in angular to respond poorly
                  if (item[attr] != data[attr] && attr != 'dateModified') {
                    updated = true;
                    item[attr] = data[attr];
                  }
                  if (updated) {
                    item.dateModified = data.dateModified;
                  }
                }
              }
            }
            if (!updated) {
              $scope.testFailures.unshift(data);
            }
          }
        });
      }

      function getPageTitle(build, job) {
        if (build.number) {
          return 'Job #' + build.number + '.' + job.number +' - ' + projectData.data.name;
        }
        return 'Job ' + job.id + ' - ' + projectData.data.name;
      }

      $scope.$watch("job.status", function() {
        $scope.testStatus = getTestStatus();
      });
      $scope.$watch("build.message", function(value) {
        if (value) {
          $scope.formattedBuildMessage = getFormattedBuildMessage(value);
        } else {
          $scope.formattedBuildMessage = null;
        }
      });
      $scope.$watchCollection("tests", function() {
        $scope.testStatus = getTestStatus();
      });

      $scope.job = jobData.data;
      $scope.logSources = jobData.data.logs;
      $scope.phases = jobData.data.phases;
      $scope.testFailures = jobData.data.testFailures;
      $scope.testGroups = jobData.data.testGroups;
      $scope.previousRuns = jobData.data.previousRuns;
      $scope.chartData = chartHelpers.getChartData($scope.previousRuns, $scope.job, chart_options);

      $rootScope.pageTitle = getPageTitle(buildData.data, $scope.job);

      stream.addScopedChannels($scope, [
        'jobs:' + $scope.job.id,
        'testgroups:' + $scope.job.id + ':*',
        'logsources:' + $scope.job.id + ':*'
      ]);
      stream.addScopedSubscriber($scope, 'job.update', updateJob);
      stream.addScopedSubscriber($scope, 'buildlog.update', updateBuildLog);
      stream.addScopedSubscriber($scope, 'testgroup.update', updateTestGroup);

      if (buildData.data.status.id == 'finished') {
        $http.post('/api/0/builds/' + buildData.data.id + '/mark_seen/');
      }
    },
    resolve: {
      jobData: function($http, $stateParams) {
        return $http.get('/api/0/jobs/' + $stateParams.job_id + '/');
      }
    }
  };
});
