(function(){
  'use strict';

  define([
      'app',
      'utils/chartHelpers',
      'utils/duration',
      'utils/escapeHtml',
      'utils/sortBuildList',
      'directives/radialProgressBar',
      'directives/timeSince'], function(app, chartHelpers, duration, escapeHtml, sortBuildList) {
    app.controller('projectDetailsCtrl', [
        '$scope', '$rootScope', 'initialProject', 'initialBuildList', '$http', '$routeParams', 'stream',
        function($scope, $rootScope, initialProject, initialBuildList, $http, $routeParams, Stream) {
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

      function addBuild(data) {
        if (data.patch && !$scope.includePatches) {
          return;
        }

        $scope.$apply(function() {
          var updated = false,
              item_id = data.id,
              attr, result, item;

          if ($scope.builds.length > 0) {
            result = $.grep($scope.builds, function(e){ return e.id == item_id; });
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
            $scope.builds.unshift(data);
            sortBuildList($scope.builds);
            $scope.builds = $scope.builds.slice(0, 100);
          }
        });
      }

      $scope.getBuildStatus = function(build) {
        if (build.status.id == 'finished') {
          return build.result.name;
        } else {
          return build.status.name;
        }
      };

      // TODO: abstract pagination functionality
      function parseLinkHeader(header) {
        if (header === null) {
          return {};
        }

        var header_vals = header.split(','),
            links = {};

        $.each(header_vals, function(_, val){
            var match = /<([^>]+)>; rel="([^"]+)"/g.exec(val);

            links[match[2]] = match[1];
        });

        return links;
      }

      function loadBuildList(url) {
        if (!url) {
          return;
        }
        $http.get(url)
          .success(function(data, status, headers){
            $scope.builds = sortBuildList(data);
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

      $scope.project = initialProject.data.project;
      $scope.builds = sortBuildList(initialBuildList.data);
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
      stream.subscribe('job.update', addBuild);
    }]);
  });
})();
