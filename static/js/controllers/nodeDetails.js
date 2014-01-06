(function(){
  'use strict';

  define([
      'app',
      'utils/chartHelpers',
      'utils/duration',
      'utils/parseLinkHeader',
      'directives/radialProgressBar',
      'directives/timeSince',
      'directives/duration',
      'modules/collection',
      'modules/pagination'], function(app, chartHelpers, duration, parseLinkHeader) {
    app.controller('nodeDetailsCtrl', [
        '$scope', '$rootScope', '$http', 'initialNode', 'initialJobList', 'collection',
        function($scope, $rootScope, $http, initialNode, initialJobList, Collection) {

      function loadJobList(url) {
        if (!url) {
          return;
        }
        $http.get(url)
          .success(function(data, status, headers){
            $scope.jobList = new Collection($scope, data, {
              limit: 100
            });
            $scope.pageLinks = parseLinkHeader(headers('Link'));
          });
      }

      $scope.loadPreviousPage = function() {
        $(document.body).scrollTop(0);
        loadJobList($scope.pageLinks.previous);
      };

      $scope.loadNextPage = function() {
        $(document.body).scrollTop(0);
        loadJobList($scope.pageLinks.next);
      };

      $scope.getBuildStatus = function(build) {
        if (build.status.id == 'finished') {
          return build.result.name;
        } else {
          return build.status.name;
        }
      };

      $scope.$watch("pageLinks", function(value) {
        $scope.nextPage = value.next || null;
        $scope.previousPage = value.previous || null;
      });

      $scope.pageLinks = parseLinkHeader(initialJobList.headers('Link'));

      $scope.node = initialNode.data;
      $scope.jobList = new Collection($scope, initialJobList.data);

      $rootScope.pageTitle = 'Node ' + $scope.node.name;
    }]);
  });
})();
