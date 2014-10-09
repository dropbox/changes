define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'admin_project_details',
    url: 'snapshots/:snapshot_id/',
    templateUrl: 'partials/admin/project-snapshot-details.html',
    controller: function($http, $scope, $stateParams, projectData, snapshotData) {
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
      $scope.snapshot = snapshotData;
      $scope.imageList = snapshotData.images;
    },
    resolve: {
      snapshotData: function($http, $stateParams) {
        return $http.get('/api/0/snapshots/' + $stateParams.snapshot_id + '/')
          .then(function(response){
            return response.data;
          });
      }
    }
  };
});
