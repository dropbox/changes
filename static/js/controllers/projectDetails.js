(function(){
  'use strict';

  define([
      'app',
      'utils/chartHelpers',
      'utils/duration',
      'utils/escapeHtml',
      'utils/parseLinkHeader',
      'utils/sortBuildList',
      'modules/collection',
      'directives/radialProgressBar',
      'directives/timeSince'], function(app, chartHelpers, duration, escapeHtml, parseLinkHeader, sortBuildList) {
    app.controller('projectDetailsCtrl', [
        '$scope', '$rootScope', 'initialProject', 'initialBuildList', '$http', '$routeParams', 'stream', 'collection',
        function($scope, $rootScope, initialProject, initialBuildList, $http, $routeParams, Stream, Collection) {
      var stream,
          entrypoint = '/api/0/projects/' + $routeParams.project_id + '/builds/',
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

      $scope.getBuildStatus = function(build) {
        if (build.status.id == 'finished') {
          return build.result.name;
        } else {
          return build.status.name;
        }
      };

      function loadBuildList(url) {
        if (!url) {
          return;
        }
        $http.get(url)
          .success(function(data, status, headers){
            $scope.builds = new Collection($scope, data, {
              sortFunc: sortBuildList,
              limit: 100
            });
            $scope.pageLinks = parseLinkHeader(headers('Link'));
          });
      }

      $scope.loadPreviousPage = function() {
        $(document.body).scrollTop(0);
        loadBuildList($scope.pageLinks.previous);
      };

      $scope.loadNextPage = function() {
        $(document.body).scrollTop(0);
        loadBuildList($scope.pageLinks.next);
      };

      $scope.$watch("pageLinks", function(value) {
        $scope.nextPage = value.next || null;
        $scope.previousPage = value.previous || null;
      });

      $scope.pageLinks = parseLinkHeader(initialBuildList.headers('Link'));

      $scope.project = initialProject.data;
      $scope.builds = new Collection($scope, initialBuildList.data, {
        sortFunc: sortBuildList,
        limit: 100
      });
      $scope.chartData = chartHelpers.getChartData($scope.builds, null, chart_options);
      $scope.includePatches = false;
      $rootScope.activeProject = $scope.project;
      $rootScope.pageTitle = $scope.project.name + ' Builds';

      $scope.$watch("includePatches", function() {
        loadBuildList(entrypoint + '?include_patches=' + ($scope.includePatches ? '1' : '0'));
      });

      $scope.$watch("builds", function() {
        $scope.chartData = chartHelpers.getChartData($scope.builds, null, chart_options);
      });

      stream = new Stream($scope, entrypoint);
      stream.subscribe('build.update', function(data){
        if (data.source.patch && !$scope.includePatches) {
          return;
        }
        $scope.builds.updateItem(data);
      });
    }]);
  });
})();
