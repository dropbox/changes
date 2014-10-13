define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'admin_project_details',
    url: 'plans/',
    templateUrl: 'partials/admin/project-plan-list.html',
    controller: function($scope, $stateParams, Collection, Paginator, projectData) {
      var collection = new Collection();
      var paginator = new Paginator('/api/0/projects/' + $stateParams.project_id + '/plans/?status=', {
        collection: collection
      });

      $scope.planList = collection;
      $scope.planPaginator = paginator;
    }
  };
});
