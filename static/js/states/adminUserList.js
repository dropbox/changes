define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'admin_layout',
    url: 'users/',
    templateUrl: 'partials/admin/user-list.html',
    controller: function($scope, Collection, Paginator) {
      var collection = new Collection();
      var paginator = new Paginator('/api/0/users/', {
        collection: collection
      });

      $scope.userList = collection;
      $scope.userPaginator = paginator;
    }
  };
});
