define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'nodes',
    url: ':node_id/',
    templateUrl: 'partials/node-details.html',
    controller: function($scope, nodeData, Collection, PageTitle, Paginator) {
      var collection = new Collection();
      var paginator = new Paginator('/api/0/nodes/' + nodeData.id + '/jobs/', {
        collection: collection
      });

      PageTitle.set('Node ' + nodeData.name);

      $scope.node = nodeData;

      $scope.jobList = collection;
      $scope.jobPaginator = paginator;
    },
    resolve: {
      nodeData: function($http, $stateParams) {
        return $http.get('/api/0/nodes/' + $stateParams.node_id + '/')
          .then(function(response){
            return response.data;
          });
      }
    }
  };
});
