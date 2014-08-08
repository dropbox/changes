define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'admin_project_details',
    url: 'snapshots/',
    templateUrl: 'partials/admin/project-snapshot-list.html',
    controller: function($http, $scope, $stateParams, Collection, Paginator, projectData) {
      var collection = new Collection();
      var paginator = new Paginator('/api/0/projects/' + $stateParams.project_id + '/snapshots/', {
        collection: collection
      });

      $scope.activateSnapshot = function(snapshotId) {
        $http.post('/api/0/projects/' + $stateParams.project_id + '/options/', {
          'snapshot.current': snapshotId,
        }).success(function(){
          $scope.currentSnapshotId = snapshotId;
        });
      };

      $scope.deactivateSnapshot = function(snapshotId) {
        $http.post('/api/0/projects/' + $stateParams.project_id + '/options/', {
          'snapshot.current': '',
        }).success(function(){
          $scope.currentSnapshotId = '';
        });
      };

      $scope.currentSnapshotId = projectData.options['snapshot.current'] || '';
      $scope.snapshotList = collection;
      $scope.snapshotPaginator = paginator;
    }
  };
});
