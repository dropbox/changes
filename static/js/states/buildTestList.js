define([
  'app',
  'utils/parseLinkHeader'
], function(app, parseLinkHeader) {
  'use strict';

  var defaults = {
    per_page: 100,
    sort: 'duration',
    query: ''
  };

  var buildTestListUrl = function(build_id, params) {
    var query = $.param({
      query: params.query,
      sort: params.sort,
      per_page: params.per_page
    });

    return '/api/0/builds/' + build_id + '/tests/?' + query;
  };

  return {
    parent: 'build_details',
    url: 'tests/?sort&query&per_page',
    templateUrl: 'partials/build-test-list.html',
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

      $scope.searchTests = function() {
        $state.go('build_test_list', $scope.searchParams);
      };

      $scope.searchParams = {
        sort: $stateParams.duration,
        query: $stateParams.query,
        per_page: $stateParams.per_page
      };

      $scope.pageLinks = parseLinkHeader(testList.headers('Link'));
      $scope.testList = testList.data;
    },
    resolve: {
      testList: function($http, $stateParams, buildData) {
        if (!$stateParams.sort) $stateParams.sort = defaults.sort;
        if (!$stateParams.query) $stateParams.query = defaults.query;
        if (!$stateParams.per_page) $stateParams.per_page = defaults.per_page;

        return $http.get(buildTestListUrl(buildData.id, $stateParams));
      }
    }
  };
});
