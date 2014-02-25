(function(){
  'use strict';

  define([
      'app',
      'utils/duration',
      'utils/escapeHtml',
      'utils/parseLinkHeader',
      'utils/sortBuildList'], function(app, duration, escapeHtml, parseLinkHeader, sortBuildList) {
    app.controller('projectBuildSearchCtrl', [
        '$scope', '$rootScope', 'initialProject', 'initialBuildList', '$http', '$stateParams', '$window', 'collection',
        function($scope, $rootScope, initialProject, initialBuildList, $http, $stateParams, $window, Collection) {

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
      $rootScope.activeProject = $scope.project;
      $rootScope.pageTitle = $scope.project.name + ' Builds';
    }]);
  });
})();
