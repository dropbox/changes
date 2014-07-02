define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'admin_layout',
    url: 'repositories/',
    templateUrl: 'partials/admin/repository-list.html',
    controller: function($scope, Collection, Paginator) {
      var collection = new Collection();
      var paginator = new Paginator('/api/0/repositories/?per_page=50', {
        collection: collection
      });

      $scope.repositoryList = collection;
      $scope.repositoryPaginator = paginator;
    }
  };
});
