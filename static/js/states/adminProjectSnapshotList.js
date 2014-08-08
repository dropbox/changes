define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'admin_project_details',
    url: 'snapshots/',
    templateUrl: 'partials/admin/project-snapshot-list.html',
    controller: function($scope, $stateParams, Collection, Paginator) {
      var collection = new Collection();
      var paginator = new Paginator('/api/0/projects/' + $stateParams.project_id + '/snapshots/', {
        collection: collection
      });

      $scope.snapshotList = collection;
      $scope.snapshotPaginator = paginator;
    }
  };
});
