define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'admin_layout',
    url: 'projects/',
    templateUrl: 'partials/admin/project-list.html',
    controller: function($scope, Collection, Paginator) {
      var collection = new Collection();
      var paginator = new Paginator('/api/0/projects/?per_page=50', {
        collection: collection
      });

      $scope.projectList = collection;
      $scope.projectPaginator = paginator;
    }
  };
});
