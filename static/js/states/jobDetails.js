define([
  'app',
  'utils/sortArray'
], function(app, sortArray) {
  'use strict';

  return {
    url: "jobs/:job_id/",
    parent: 'build_details',
    templateUrl: 'partials/job-details.html',
    controller: function($scope, $http, $filter, projectData, buildData, Collection,
                         jobData, phaseList, CollectionPoller, ItemPoller, PageTitle) {

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

      function processPhase(phase) {
        if (phase.isVisible === undefined) {
          phase.isVisible = phase.status.id != 'finished' || phase.result.id != 'passed';
        }

        phase.steps = new Collection(phase.steps, {
          sortFunc: function(arr) {
            function getScore(object) {
              return [object.result.id == 'failed' ? 1 : 2, (object.dateStarted || object.dateCreated)];
            }
            return sortArray(arr, getScore, false);
          }
        });

        phase.totalSteps = phase.steps.length;

        var finishedSteps = 0;
        $.each(phase.steps, function(_, step){
          if (step.status.id == 'finished') {
            finishedSteps += 1;
          }
        });
        phase.finishedSteps = finishedSteps;
      }

      $.map(phaseList, processPhase);

      $scope.job = jobData;
      $scope.phaseList = new Collection(phaseList, {
          sortFunc: function(arr) {
            function getScore(object) {
              return [new Date(object.dateStarted || object.dateCreated)];
            }
            return sortArray(arr, getScore);
          }
      });
      $scope.testFailures = jobData.testFailures;
      $scope.previousRuns = new Collection(jobData.previousRuns);

      PageTitle.set(getPageTitle(buildData, $scope.job));

      // TODO(dcramer): support long polling with offsets
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
        }
      });
      var phasesPoller = new CollectionPoller({
        $scope: $scope,
        collection: $scope.phaseList,
        endpoint: '/api/0/jobs/' + jobData.id + '/phases/',
        update: function(response) {
          $scope.phaseList.extend(response);
          $.map($scope.phaseList, processPhase);
        }
      });
    },
    resolve: {
      jobData: function($http, $stateParams) {
        return $http.get('/api/0/jobs/' + $stateParams.job_id + '/').then(function(response){
          return response.data;
        });
      },
      phaseList: function($http, $stateParams) {
        return $http.get('/api/0/jobs/' + $stateParams.job_id + '/phases/').then(function(response){
          return response.data;
        });
      }
    }
  };
});
