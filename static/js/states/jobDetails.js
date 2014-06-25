define([
  'app',
  'utils/sortArray'
], function(app, sortArray) {
  'use strict';

  var BUFFER_SIZE = 10000;

  return {
    url: "jobs/:job_id/",
    parent: 'build_details',
    templateUrl: 'partials/job-details.html',
    controller: function($scope, $http, $filter, projectData, buildData, Collection,
                         jobData, ItemPoller, PageTitle, Pagination) {
      var logStreams = {};

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

      function updateJob(data){
        if (data.id !== $scope.job.id) {
          return;
        }

        $scope.$apply(function() {
          $scope.job = data;
        });
      }

      function getPageTitle(build, job) {
        if (build.number) {
          return 'Job #' + build.number + '.' + job.number +' - ' + projectData.name;
        }
        return 'Job ' + job.id + ' - ' + projectData.name;
      }

      function organizeLogSources(sourcesByPhase, logSources) {
        $.each(logSources, function(_, source){
          if (!source.step.phase) {
            // legacy, incompatible
            return;
          }
          var phaseId = source.step.phase.id;
          if (sourcesByPhase[phaseId] === undefined) {
            sourcesByPhase[phaseId] = new Collection($scope, []);
          }
          sourcesByPhase[phaseId].update(source);
        });
      }

      $.map(jobData.phases, function(phase){
        phase.isVisible = phase.status.id != 'finished' || phase.result.id != 'passed';
      });

      $scope.job = jobData;
      $scope.phases = new Collection(jobData.phases, {
          sortFunc: function(arr) {
            function getScore(object) {
              return [-new Date(object.dateStarted || object.dateCreated).getTime()];
            }
            return sortArray(arr, getScore);
          }
      });
      $scope.testFailures = jobData.testFailures;
      $scope.previousRuns = new Collection(jobData.previousRuns);
      $scope.logSourcesByPhase = {};

      organizeLogSources($scope.logSourcesByPhase, jobData.logs);

      PageTitle.set(getPageTitle(buildData, $scope.job));

      // TODO(dcramer): support log polling with offsets
      var poller = new ItemPoller({
        $scope: $scope,
        endpoint: '/api/0/jobs/' + jobData.id + '/',
        update: function(response) {
          if (response.dateModified < $scope.job.dateModified) {
            return;
          }
          $.extend(true, $scope.job, response);
          $.extend(true, $scope.testFailures, response.testFailures);
          $scope.previousRuns.extend(response.previousRuns);
          $scope.phases.extend(response.phases);
          $.map($scope.phases, function(phase){
            if (phase.isVisible === undefined) {
              phase.isVisible = true;
            }
          });


          organizeLogSources($scope.logSourcesByPhase, response.logs);
        }
      });
    },
    resolve: {
      jobData: function($http, $stateParams) {
        return $http.get('/api/0/jobs/' + $stateParams.job_id + '/').then(function(response){
          return response.data;
        });
      }
    }
  };
});
