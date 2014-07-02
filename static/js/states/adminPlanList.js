define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'admin_layout',
    url: 'plans/',
    templateUrl: 'partials/admin/plan-list.html',
    controller: function($scope, Collection, Paginator) {
      var collection = new Collection();
      var paginator = new Paginator('/api/0/plans/?per_page=50', {
        collection: collection
      });


      $scope.planList = collection;
      $scope.planPaginator = paginator;
    }
  };
});
