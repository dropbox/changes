define([
  'app',
  'utils/sortArray'
], function(app, sortArray) {
  'use strict';

  return {
    parent: 'project_details',
    url: "builds/:build_id/",
    templateUrl: 'partials/build-details.html',
    controller: function($document, $scope, $state, $http, $filter, features, projectData, buildData,
                         coverageData, stream, flash, Collection, PageTitle) {
      function getCoveragePercent(lines_covered, lines_uncovered) {
        var total_lines = lines_covered + lines_uncovered;
        if (!total_lines) {
          return 0;
        }
        return parseInt(lines_covered / total_lines * 100, 10);
      }

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
            $state.go('build_details', {build_id: $scope.build.id});
          })
          .error(function(){
            flash('error', 'There was an error cancelling this build.');
          });
      };

      $scope.restartBuild = function() {
        $http.post('/api/0/builds/' + $scope.build.id + '/retry/')
          .success(function(data){
            $state.go('build_details', {build_id: data.id});
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

      $scope.eventList = buildData.events;
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

      if (features.coverage) {
        $scope.hasCoverage = (buildData.stats.lines_covered + buildData.stats.lines_uncovered) > 0;
        $scope.coveragePercent = getCoveragePercent(buildData.stats.lines_covered, buildData.stats.lines_uncovered);

        var fileCoverageData = [];
        $.each(coverageData, function(filename, item) {
          item.hasCoverage = (item.linesCovered + item.linesUncovered) > 0;
          item.hasDiffCoverage = (item.diffLinesCovered + item.diffLinesUncovered) > 0;
          item.coveragePercent = getCoveragePercent(item.linesCovered, item.linesUncovered);
          item.diffCoveragePercent = getCoveragePercent(item.diffLinesCovered, item.diffLinesUncovered);
          item.filename = filename;
          fileCoverageData.push(item);
        });

        $scope.coverageData = sortArray(fileCoverageData, function(item) { return [item.filename]; });
      }

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
      },
      coverageData: function($http, $stateParams) {
        return $http.get('/api/0/builds/' + $stateParams.build_id + '/stats/coverage/?diff=1').then(function(response){
          return response.data;
        });
      }
    }
  };
});
