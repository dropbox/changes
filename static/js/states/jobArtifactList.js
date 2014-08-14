define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'job_details',
    url: 'artifacts/',
    templateUrl: 'partials/job-artifact-list.html',
    controller: function($scope, $stateParams, Collection, Paginator) {
      var collection = new Collection();
      var paginator = new Paginator('/api/0/jobs/' + $stateParams.job_id + '/artifacts/', {
        collection: collection
      });

      $scope.artifactList = collection;
      $scope.artifactPaginator = paginator;
    }
  };
});
