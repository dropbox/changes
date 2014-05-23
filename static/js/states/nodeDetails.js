define([
  'app',
  'utils/parseLinkHeader'
], function(app, parseLinkHeader) {
  'use strict';

  return {
    parent: 'nodes',
    url: ':node_id/',
    templateUrl: 'partials/node-details.html',
    controller: function($scope, $http, nodeData, jobList, Collection, PageTitle) {
      function loadJobList(url) {
        if (!url) {
          return;
        }
        $http.get(url)
          .success(function(data, status, headers){
            $scope.jobList = new Collection(data, {
              limit: 100
            });
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

      $scope.getBuildStatus = function(build) {
        if (build.status.id == 'finished') {
          return build.result.name;
        } else {
          return build.status.name;
        }
      };

      $scope.$watch("pageLinks", function(value) {
        $scope.nextPage = value.next || null;
        $scope.previousPage = value.previous || null;
      });

      $scope.pageLinks = parseLinkHeader(jobList.headers('Link'));

      $scope.node = nodeData.data;
      $scope.jobList = new Collection(jobList.data);

      PageTitle.set('Node ' + $scope.node.name);
    },
    resolve: {
      nodeData: function($http, $stateParams) {
        return $http.get('/api/0/nodes/' + $stateParams.node_id + '/');
      },
      jobList: function($http, $stateParams) {
        return $http.get('/api/0/nodes/' + $stateParams.node_id + '/jobs/');
      }
    }
  };
});
