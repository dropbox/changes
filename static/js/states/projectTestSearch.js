define([
  'app',
  'utils/chartHelpers',
  'utils/duration',
  'utils/escapeHtml',
  'utils/parseLinkHeader'
], function(app, chartHelpers, duration, escapeHtml, parseLinkHeader) {
  'use strict';

  var defaults = {
    per_page: 100,
    sort: 'duration',
    query: '',
    min_duration: 0
  };

  var buildTestListUrl = function(project_id, params) {
    var query = $.param({
      query: params.query,
      sort: params.sort,
      per_page: params.per_page,
      min_duration: params.min_duration
    });

    return '/api/0/projects/' + project_id + '/tests/?' + query;
  };

  return {
    parent: 'project_details',
    url: 'search/tests/?sort&query&per_page&min_duration',
    templateUrl: 'partials/project-test-search.html',
    controller: function($http, $scope, $state, $stateParams, testList) {
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

      $scope.searchTests = function(params) {
        if (params !== undefined) {
          $.each(params, function(key, value){
            $scope.searchParams[key] = value;
          });
        }
        $state.go('project_test_search', $scope.searchParams);
      };

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

      $scope.searchParams = {
        sort: $stateParams.duration,
        query: $stateParams.query,
        min_duration: $stateParams.min_duration,
        per_page: $stateParams.per_page
      };

      $scope.pageLinks = parseLinkHeader(testList.headers('Link'));
      $scope.testList = testList.data;

    },
    resolve: {
      testList: function($http, $stateParams, projectData) {
        if (!$stateParams.sort) $stateParams.sort = defaults.sort;
        if (!$stateParams.query) $stateParams.query = defaults.query;
        if (!$stateParams.per_page) $stateParams.per_page = defaults.per_page;
        if (!$stateParams.min_duration) $stateParams.min_duration = defaults.min_duration;

        return $http.get(buildTestListUrl(projectData.id, $stateParams));
      }
    }
  };
});
