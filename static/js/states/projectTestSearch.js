define([
  'app',
  'utils/chartHelpers',
  'utils/escapeHtml',
  'utils/parseLinkHeader'
], function(app, chartHelpers, escapeHtml, parseLinkHeader) {
  'use strict';

  var defaults = {
    per_page: 100,
    sort: 'duration',
    query: '',
    min_duration: 0
  };

  function getEndpoint(params) {
    var query = $.param({
      query: params.query || defaults.query,
      sort: params.sort || defaults.sort,
      per_page: params.per_page || defaults.per_page,
      min_duration: params.min_duration || defaults.min_duration
    });

    return '/api/0/projects/' + params.project_id + '/tests/?' + query;
  }

  return {
    parent: 'project_details',
    url: 'search/tests/?sort&query&per_page&min_duration',
    templateUrl: 'partials/project-test-search.html',
    controller: function($scope, $state, $stateParams, Collection, PageTitle,
                         Paginator, projectData) {
      $scope.searchTests = function(params) {
        if (params !== undefined) {
          $.each(params, function(key, value){
            $scope.searchParams[key] = value;
          });
        }
        $state.go('project_test_search', $scope.searchParams);
      };

      $scope.searchParams = {
        sort: $stateParams.duration,
        query: $stateParams.query,
        min_duration: $stateParams.min_duration,
        per_page: $stateParams.per_page
      };

      var paginator = new Paginator(getEndpoint($stateParams), {
        collection: new Collection([], {
          equals: function(item, other) {
            return item.hash == other.hash;
          }
        })
      });

      PageTitle.set(projectData.name + ' Tests');

      $scope.testList = paginator.collection;
      $scope.testPaginator = paginator;
    }
  };
});
