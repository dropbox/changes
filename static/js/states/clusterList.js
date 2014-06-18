define([
  'app',
  'utils/parseLinkHeader'
], function(app, parseLinkHeader) {
  'use strict';

  return {
    parent: 'layout',
    url: '/clusters/',
    templateUrl: 'partials/cluster-list.html',
    controller: function($scope, $http, clusterList, Collection, PageTitle) {
      function loadClusterList(url) {
        if (!url) {
          return;
        }
        $http.get(url)
          .success(function(data, status, headers){
            $scope.clusterList = new Collection(data, {
              limit: 100
            });
            $scope.pageLinks = parseLinkHeader(headers('Link'));
          });
      }

      $scope.loadPreviousPage = function() {
        $(document.body).scrollTop(0);
        loadNodeList($scope.pageLinks.previous);
      };

      $scope.loadNextPage = function() {
        $(document.body).scrollTop(0);
        loadNodeList($scope.pageLinks.next);
      };

      $scope.$watch("pageLinks", function(value) {
        $scope.nextPage = value.next || null;
        $scope.previousPage = value.previous || null;
      });

      $scope.pageLinks = parseLinkHeader(clusterList.headers('Link'));

      $scope.clusterList = new Collection(clusterList.data);

      PageTitle.set('Clusters');
    },
    resolve: {
      clusterList: function($http, $stateParams) {
        return $http.get('/api/0/clusters/');
      }
    }
  };
});
