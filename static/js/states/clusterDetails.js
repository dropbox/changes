define([
  'app',
  'utils/parseLinkHeader'
], function(app, parseLinkHeader) {
  'use strict';

  return {
    parent: 'clusters',
    url: ':cluster_id/',
    templateUrl: 'partials/cluster-details.html',
    controller: function($scope, clusterData, nodeList, Collection, PageTitle) {
      function loadNodeList(url) {
        if (!url) {
          return;
        }
        $http.get(url)
          .success(function(data, status, headers){
            $scope.nodeList = new Collection(data);
            $scope.pageLinks = parseLinkHeader(headers('Link'));
          });
      }

      $scope.loadPreviousPage = function() {
        $(document.body).scrollTop(0);
        loadJobList($scope.pageLinks.previous);
      };

      $scope.loadNextPage = function() {
        $(document.body).scrollTop(0);
        loadJobList($scope.pageLinks.next);
      };

      $scope.$watch("pageLinks", function(value) {
        $scope.nextPage = value.next || null;
        $scope.previousPage = value.previous || null;
      });

      $scope.pageLinks = parseLinkHeader(nodeList.headers('Link'));
      $scope.nodeList = new Collection(nodeList.data);
      $scope.cluster = clusterData;

      PageTitle.set('Cluster ' + clusterData.name);
    },
    resolve: {
      clusterData: function($http, $stateParams) {
        return $http.get('/api/0/clusters/' + $stateParams.cluster_id + '/').then(function(response){
          return response.data;
        });
      },
      nodeList: function($http, $stateParams) {
        return $http.get('/api/0/clusters/' + $stateParams.cluster_id + '/nodes/?since=7');
      }
    }
  };
});
