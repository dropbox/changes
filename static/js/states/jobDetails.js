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
                         jobData, phaseList, ItemPoller, PageTitle, Pagination) {

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

      $.map(phaseList, function(phase){
        phase.isVisible = phase.status.id != 'finished' || phase.result.id != 'passed';
      });

      $scope.job = jobData;
      $scope.phaseList = new Collection(phaseList, {
          sortFunc: function(arr) {
            function getScore(object) {
              return [-new Date(object.dateStarted || object.dateCreated).getTime()];
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
      var phasesPoller = new ItemPoller({
        $scope: $scope,
        endpoint: '/api/0/jobs/' + jobData.id + '/phases/',
        update: function(response) {
          $scope.phaseList.extend(response);
          $.map($scope.phaseList, function(phase){
            if (phase.isVisible === undefined) {
              phase.isVisible = true;
            }
          });
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
