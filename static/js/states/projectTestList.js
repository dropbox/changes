define([
  'app',
  'utils/parseLinkHeader'
], function(app, parseLinkHeader) {
  'use strict';

  return {
    parent: 'project_details',
    url: 'tests/',
    templateUrl: 'partials/project-test-list.html',
    controller: function($scope, testList) {
      function loadTestList(url) {
        if (!url) {
          return;
        }
        $http.get(url)
          .success(function(data, status, headers){
            $scope.testList = data;
            $scope.pageLinks = parseLinkHeader(headers('Link'));
          });
      }

      $scope.loadPreviousPage = function() {
        $(document.body).scrollTop(0);
        loadTestList($scope.pageLinks.previous);
      };

      $scope.loadNextPage = function() {
        $(document.body).scrollTop(0);
        loadTestList($scope.pageLinks.next);
      };

      $scope.$watch("pageLinks", function(value) {
        $scope.nextPage = value.next || null;
        $scope.previousPage = value.previous || null;
      });

      $scope.pageLinks = parseLinkHeader(testList.headers('Link'));
      $scope.testList = testList.data;
    },
    resolve: {
      testList: function($http, projectData) {
        return $http.get('/api/0/projects/' + projectData.id + '/tests/');
      }
    }
  };
});
