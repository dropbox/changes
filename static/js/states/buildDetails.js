define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'project_details',
    url: "builds/:build_id/",
    templateUrl: 'partials/build-details.html',
    controller: function($document, $scope, $state, $http, $filter, projectData, buildData, stream, flash, Collection, PageTitle) {
      function getFormattedBuildMessage(message) {
        return $filter('linkify')($filter('escape')(message));
      }

      function getPageTitle(build) {
        if (build.number) {
          return 'Build #' + build.number + ' - ' + projectData.name;
        }
        return 'Build ' + build.id + ' - ' + projectData.name;
      }

      function updateBuild(data){
        if (data.id !== $scope.build.id) {
          return;
        }
        $scope.$apply(function() {
          $scope.build = data;
        });
      }

      $scope.cancelBuild = function() {
        $http.post('/api/0/builds/' + $scope.build.id + '/cancel/')
          .success(function(data){
            $scope.build = data;
          })
          .error(function(){
            flash('error', 'There was an error cancelling this build.');
          });
      };

      $scope.restartBuild = function() {
        $http.post('/api/0/builds/' + $scope.build.id + '/restart/')
          .success(function(data){
            $scope.jobList = new Collection($scope, []);
            $scope.build = data;
            $scope.testFailures = {}
            $scope.testChanges = [];
          })
          .error(function(){
            flash('error', 'There was an error restarting this build.');
          });
      };


      $scope.getBuildStatus = function(build) {
        if (build.status.id == 'finished') {
          return build.result.name;
        } else {
          return build.status.name;
        }
      };

      $scope.build = buildData;
      if ($scope.build.message) {
        $scope.formattedBuildMessage = getFormattedBuildMessage($scope.build.message);
      } else {
        $scope.formattedBuildMessage = null;
      }

      $scope.previousRuns = buildData.previousRuns;
      $scope.testFailures = buildData.testFailures;
      $scope.testChanges = buildData.testChanges;
      $scope.seenBy = buildData.seenBy.slice(0, 14);
      $scope.jobList = new Collection($scope, buildData.jobs);
      $scope.phaseList = [
        {
          name: "Test",
          result: $scope.build.result,
          status: $scope.build.status
        }
      ];
      // show phase list if > 1 phase
      $scope.showPhaseList = true;

      PageTitle.set(getPageTitle($scope.build));

      stream.addScopedChannels($scope, [
        'builds:' + $scope.build.id,
        'builds:' + $scope.build.id + ':jobs'
      ]);
      stream.addScopedSubscriber($scope, 'build.update', updateBuild);
      stream.addScopedSubscriber($scope, 'job.update', function(data) {
        if (data.build.id == $scope.build.id) {
          $scope.jobList.updateItem(data);
        }
      });

      if (buildData.status.id === 'finished') {
        $http.post('/api/0/builds/' + buildData.id + '/mark_seen/');
      }

      // TODO(dcramer): we should actually find out if there could be > 1 job ever for this
      $scope.isSingleJob = buildData.jobs.length === 1;

      $scope.$on('$stateChangeSuccess', function(event, toState, toParams, fromState, fromParams){
        if (toState.name !== 'build_details') {
          return;
        }

        if ($scope.isSingleJob) {
          $state.go('job_details', {job_id: buildData.jobs[0].id}, {location: false});
        }
      });
    },
    resolve: {
      buildData: function($http, $stateParams) {
        return $http.get('/api/0/builds/' + $stateParams.build_id + '/').then(function(response){
          return response.data;
        });
      }
    }
  };
});
