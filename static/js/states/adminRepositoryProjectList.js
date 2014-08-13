define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'admin_repository_details',
    url: 'projects/',
    templateUrl: 'partials/admin/repository-project-list.html',
    controller: function($http, $scope, $stateParams, Collection, Paginator) {
      var collection = new Collection();
      var paginator = new Paginator('/api/0/repositories/' + $stateParams.repository_id + '/projects/', {
        collection: collection
      });

      $scope.projectList = collection;
      $scope.projectPaginator = paginator;
    }
  };
});
