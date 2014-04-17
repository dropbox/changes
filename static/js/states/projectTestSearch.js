define([
  'app',
  'utils/chartHelpers',
  'utils/duration',
  'utils/escapeHtml',
  'utils/parseLinkHeader'
], function(app, chartHelpers, duration, escapeHtml, parseLinkHeader) {
  'use strict';

  return {
    parent: 'project_details',
    url: 'search/tests/',
    templateUrl: 'partials/project-test-search.html',
    controller: function($http, $scope, $state, testList) {
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
