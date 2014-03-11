define([
  'app',
  'utils/chartHelpers',
  'utils/duration',
  'utils/escapeHtml'
], function(app, chartHelpers, duration, escapeHtml) {
  'use strict';

  return {
    parent: 'project_details',
    url: "builds/:build_id/",
    templateUrl: 'partials/build-details.html',
    controller: function($scope, $rootScope, $http, $stateParams, $filter, projectData, buildData, Stream, flash, Collection) {
      var stream,
          entrypoint = '/api/0/builds/' + $stateParams.build_id + '/',
          chart_options = {
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
              if (item.status.id == 'finished') {
                content += '<p>Build ' + item.result.name;
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

      function getFormattedBuildMessage(message) {
        return $filter('linkify')($filter('escape')(message));
      }

      function getPageTitle(build) {
        if (build.number) {
          return 'Build #' + build.number + ' - ' + projectData.data.name;
        }
        return 'Build ' + build.id + ' - ' + projectData.data.name;
      }

      function updateBuild(data){
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
            $scope.build = data;
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

      $scope.$watch("build.message", function(value) {
        if (value) {
          $scope.formattedBuildMessage = getFormattedBuildMessage(value);
        } else {
          $scope.formattedBuildMessage = null;
        }
      });

      $scope.build = buildData.data;
      $scope.previousRuns = buildData.data.previousRuns;
      $scope.chartData = chartHelpers.getChartData($scope.previousRuns, $scope.build, chart_options);
      $scope.testFailures = buildData.data.testFailures;
      $scope.testChanges = buildData.data.testChanges;
      $scope.seenBy = buildData.data.seenBy.slice(0, 14);
      $scope.jobList = new Collection($scope, buildData.data.jobs);
      $scope.phaseList = [
        {
          name: "Test",
          result: $scope.build.result,
          status: $scope.build.status
        }
      ];
      // show phase list if > 1 phase
      $scope.showPhaseList = true;

      $rootScope.pageTitle = getPageTitle($scope.build);

      stream = new Stream($scope, entrypoint);
      stream.subscribe('build.update', updateBuild);
      stream.subscribe('job.update', function(data) { $scope.jobList.updateItem(data); });

      if ($scope.build.status.id == 'finished') {
        $http.post('/api/0/builds/' + $scope.build.id + '/mark_seen/');
      }
    },
    resolve: {
      buildData: function($http, $stateParams) {
        return $http.get('/api/0/builds/' + $stateParams.build_id + '/');
      }
    }
  };
});
