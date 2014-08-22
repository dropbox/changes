define([
  'app'
], function(app) {
  'use strict';

  function getEndpoint(params) {
    var endpoint = '/api/0/projects/?';

    if (params.query !== null) {
      endpoint += '&query=' + params.query;
    }

    if (params.status !== null) {
      endpoint += '&status=' + params.status;
    }

    if (params.sort !== null) {
      endpoint += '&sort=' + params.sort;
    }

    if (params.per_page !== null) {
      endpoint += '&per_page=' + params.per_page;
    }

    return endpoint;
  }


  function ensureDefaults(params) {
    if (params.status === null) {
      params.status = 'active';
    }
  }

  return {
    parent: 'admin_layout',
    url: 'projects/?query&per_page&sort&status',
    templateUrl: 'partials/admin/project-list.html',
    controller: function($scope, $state, $stateParams, Collection, Paginator) {
      var collection = new Collection();
      var paginator = new Paginator(getEndpoint($stateParams), {
        collection: collection
      });

      $scope.projectList = collection;
      $scope.projectPaginator = paginator;

      $scope.searchForm = {
        query: $stateParams.query
      };

      $scope.search = function(){
        $state.go('admin_project_list', $scope.searchForm);
      };
    },
    onEnter: function($stateParams) {
      ensureDefaults($stateParams);
    }
  };
});
