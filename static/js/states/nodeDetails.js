define([
  'app'
], function(app) {
  'use strict';

  return {
    parent: 'layout',
    url: '/nodes/:node_id/',
    templateUrl: 'partials/node-details.html',
    controller: function($scope, $http, nodeData, Collection, PageTitle, Paginator, flash) {
      var collection = new Collection();
      var paginator = new Paginator('/api/0/nodes/' + nodeData.id + '/jobs/', {
        collection: collection
      });

      PageTitle.set('Node ' + nodeData.name);

      $scope.node = nodeData;

      $scope.jobList = collection;
      $scope.jobPaginator = paginator;

      var status_endpoint = '/api/0/nodes/' + nodeData.id + '/status/';

      var update_offline_status = function(data) {
        if ('offline' in data) {
          $scope.offline = data.offline;
        }
      };

      $scope.toggle_offline = function() {
        var confirm_msg = 'Are you sure you want to temporarily disable this node?';
        if ($scope.offline) {
          confirm_msg = 'Are you sure you want to bring this node back?';
        }
        if (confirm(confirm_msg)) {
          /* We delete $scope.offline here to not show the button to toggle the status
           * while we are fetching new status information. */
          var was_offline = $scope.offline;
          delete $scope.offline;
          $http.post(status_endpoint + '?toggle=1')
            .success(update_offline_status)
            .error(function(response) {
              var error = response.error;
              flash('error', 'There was an error changing the status of this node: ' + error);
              $scope.offline = was_offline;
            });
        }
      };

      $http.get(status_endpoint).success(update_offline_status);
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
