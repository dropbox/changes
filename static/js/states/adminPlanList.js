define([
  'app'
], function(app) {
  'use strict';

  function getEndpoint(params) {
    var endpoint = '/api/0/plans/?';

    if (params.query !== null) {
      endpoint += '&query=' + params.query;
    }

    if (params.sort !== null) {
      endpoint += '&sort=' + params.sort;
    }

    if (params.status !== null) {
      endpoint += '&status=' + params.status;
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
    url: 'plans/?query&sort&per_page&status',
    templateUrl: 'partials/admin/plan-list.html',
    controller: function($scope, $state, $stateParams, Collection, Paginator) {
      var collection = new Collection();
      var paginator = new Paginator(getEndpoint($stateParams), {
        collection: collection
      });

      $scope.searchForm = {
        query: $stateParams.query
      };

      $scope.search = function(){
        $state.go('admin_plan_list', $scope.searchForm);
      };

      $scope.planList = collection;
      $scope.planPaginator = paginator;
    },
    onEnter: function($stateParams) {
      ensureDefaults($stateParams);
    }
  };
});
