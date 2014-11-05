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
                         coverageData, flash, Collection, ItemPoller, PageTitle) {
      function getCoveragePercent(lines_covered, lines_uncovered) {
        var total_lines = lines_covered + lines_uncovered;
        if (!total_lines) {
          return '';
        }
        return parseInt(lines_covered / total_lines * 100, 10) + '%';
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

        $scope.hasTests = (features.tests && buildData.stats.test_count);
        $scope.isFinished = (buildData.status.id == 'finished');
        $scope.build = data;
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
      $scope.eventList = new Collection(buildData.events);
      $scope.failureList = new Collection(buildData.failures);
      $scope.testFailures = buildData.testFailures;
      $scope.testChanges = buildData.testChanges;
      $scope.seenBy = buildData.seenBy.slice(0, 14);
      $scope.jobList = new Collection(buildData.jobs);
      $scope.phaseList = [
        {
          name: "Test",
          result: buildData.result,
          status: buildData.status
        }
      ];

      updateBuild(buildData);

      // show phase list if > 1 phase
      $scope.showPhaseList = true;

      if (features.coverage && buildData.status.id == 'finished') {
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

        $scope.coverageData = sortArray(fileCoverageData, function(item) { return [item.filename]; }).reverse();
      }

      PageTitle.set(getPageTitle(buildData));

      if (buildData.status.id === 'finished') {
        $http.post('/api/0/builds/' + buildData.id + '/mark_seen/');
      }

      // TODO(dcramer): we should actually find out if there could be > 1 job ever for this
      if (buildData.jobs.length === 1) {
        $scope.isSingleJob = true;
        $scope.job = buildData.jobs[0];
      } else {
        $scope.isSingleJob = false;
        $scope.job = null;
      }

      $scope.$on('$stateChangeSuccess', function(event, toState, toParams, fromState, fromParams){
        if (toState.name !== 'build_details') {
          return;
        }

        if ($scope.isSingleJob) {
          $state.go('job_details', {job_id: buildData.jobs[0].id}, {location: false});
        }
      });

      var poller = new ItemPoller({
        $scope: $scope,
        endpoint: '/api/0/builds/' + buildData.id + '/',
        update: function(response) {
          if (response.dateModified < $scope.build.dateModified) {
            return;
          }
          $.extend(true, $scope.build, response);
          updateBuild(response);
          $scope.jobList.extend(response.jobs);
          $scope.eventList.extend(response.events);
          $scope.failureList.extend(response.failures);
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
