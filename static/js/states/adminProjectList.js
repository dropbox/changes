define([
  'app'
], function(app) {
  'use strict';

  function getEndpoint(params) {
    var endpoint = '/api/0/projects/?';

    if (params.query) {
      endpoint += '&query=' + params.query;
    }

    if (params.sort) {
      endpoint += '&sort=' + params.sort;
    }

    if (params.per_page) {
      endpoint += '&per_page=' + params.per_page;
    }

    return endpoint;
  }

  return {
    parent: 'admin_layout',
    url: 'projects/?query&per_page&sort',
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
    }
  };
});
