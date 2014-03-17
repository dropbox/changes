define([
  'app',
  'utils/duration',
  'utils/escapeHtml',
  'utils/parseLinkHeader',
  'utils/sortBuildList'
], function(app, duration, escapeHtml, parseLinkHeader, sortBuildList) {
  'use strict';

  return {
    parent: 'project_details',
    url: 'search/',
    templateUrl: 'partials/project-build-list.html',
    controller: function($scope, $http, $stateParams, buildList, Collection) {
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

      $scope.pageLinks = parseLinkHeader(buildList.headers('Link'));

      $scope.builds = new Collection($scope, buildList.data, {
        sortFunc: sortBuildList,
        limit: 100
      });
    },
    resolve: {
      buildList: function($http, $window, projectData) {
        return $http.get('/api/0/projects/' + projectData.id + '/builds/search/' + $window.location.search);
      }
    }
  };
});
