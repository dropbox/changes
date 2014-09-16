define([
  'app'
], function(app) {
  'use strict';

  function getEndpoint(params) {
    var endpoint = '/api/0/users/?';

    if (params.query !== null) {
      endpoint += '&query=' + params.query;
    }

    if (params.sort !== null) {
      endpoint += '&sort=' + params.sort;
    }

    if (params.per_page !== null) {
      endpoint += '&per_page=' + params.per_page;
    }

    return endpoint;
  }

  return {
    parent: 'admin_layout',
    url: 'users/?query&per_page&sort',
    templateUrl: 'partials/admin/user-list.html',
    controller: function($scope, $state, $stateParams, Collection, Paginator) {
      var collection = new Collection();
      var paginator = new Paginator(getEndpoint($stateParams), {
        collection: collection
      });

      $scope.searchForm = {
        query: $stateParams.query
      };

      $scope.search = function(){
        $state.go('admin_user_list', $scope.searchForm);
      };

      $scope.userList = collection;
      $scope.userPaginator = paginator;
    }
  };
});
