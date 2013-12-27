(function(){
  'use strict';

  define([
      'app',
      'utils/chartHelpers',
      'utils/duration',
      'utils/escapeHtml',
      'directives/radialProgressBar',
      'directives/timeSince',
      'directives/duration',
      'filters/escape',
      'filters/wordwrap',
      'modules/pagination'], function(app, chartHelpers, duration, escapeHtml) {
    app.controller('buildDetailsCtrl', [
        '$scope', '$rootScope', 'initialData', '$window', '$timeout', '$http', '$routeParams', '$filter', 'stream', 'pagination', 'flash',
        function($scope, $rootScope, initialData, $window, $timeout, $http, $routeParams, $filter, Stream, Pagination, flash) {

      var stream,
          entrypoint = '/api/0/builds/' + $routeParams.build_id + '/',
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

      function getFormattedBuildMessage(build) {
        return $filter('linkify')($filter('escape')(build.message));
      }

      function getPageTitle(build) {
        if (build.number) {
          return 'Build #' + build.number + ' - ' + $scope.project.name;
        }
        return 'Build ' + build.id + ' - ' + $scope.project.name;
      }

      function updateBuild(data){
        $scope.$apply(function() {
          $scope.build = data;
        });
      }

      function addJob(data) {
        $scope.$apply(function() {
          var updated = false,
              item_id = data.id,
              attr, result, item;

          if ($scope.jobs.length > 0) {
            result = $.grep($scope.jobs, function(e){ return e.id == item_id; });
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
            $scope.jobs.unshift(data);
          }
        });
      }

      $scope.retryBuild = function() {
        $http.post('/api/0/builds/' + $scope.job.id + '/retry/')
          .success(function(data){
            $window.location.href = data.build.link;
          })
          .error(function(){
            flash('error', 'There was an error while retrying this build.');
          });
      };

      $scope.getBuildStatus = function(build) {
        if (build.status.id == 'finished') {
          return build.result.name;
        } else {
          return build.status.name;
        }
      };

      $scope.$watch("build.message", function() {
        $scope.formattedBuildMessage = getFormattedBuildMessage($scope.build);
      });

      $scope.project = initialData.data.project;
      $scope.build = initialData.data.build;
      $scope.jobs = initialData.data.jobs;
      $scope.previousRuns = initialData.data.previousRuns;
      $scope.chartData = chartHelpers.getChartData($scope.previousRuns, $scope.build, chart_options);
      $scope.testFailures = initialData.data.testFailures;

      $rootScope.activeProject = $scope.project;
      $rootScope.pageTitle = getPageTitle($scope.build);

      stream = new Stream($scope, entrypoint);
      stream.subscribe('build.update', updateBuild);
      stream.subscribe('job.update', addJob);
    }]);
  });
})();
