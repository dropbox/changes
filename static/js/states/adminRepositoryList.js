define([
  'app'
], function(app) {
  'use strict';

  function getEndpoint(params) {
    var endpoint = '/api/0/repositories/?';

    if (params.query) {
      endpoint += '&query=' + params.query;
    }

    if (params.sort) {
      endpoint += '&sort=' + params.sort;
    }

    if (params.backend) {
      endpoint += '&backend=' + params.backend;
    }

    if (params.per_page) {
      endpoint += '&per_page=' + params.per_page;
    }

    return endpoint;
  }

  return {
    parent: 'admin_layout',
    url: 'repositories/?query&sort&backend&per_page',
    templateUrl: 'partials/admin/repository-list.html',
    controller: function($scope, $state, $stateParams, Collection, Paginator) {
      var collection = new Collection();
      var paginator = new Paginator(getEndpoint($stateParams), {
        collection: collection
      });

      $scope.repositoryList = collection;
      $scope.repositoryPaginator = paginator;

      $scope.searchForm = {
        query: $stateParams.query
      };

      $scope.search = function(){
        $state.go('admin_repository_list', $scope.searchForm);
      };
    }
  };
});
