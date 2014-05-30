define([
  'app',
  'utils/parseLinkHeader'
], function(app, parseLinkHeader) {
  'use strict';

  var PER_PAGE = 50;

  return {
    parent: 'layout',
    url: '/plans/',
    templateUrl: 'partials/plan-list.html',
    controller: function($scope, planList, Collection) {
      function updatePageLinks(links) {
        var value = parseLinkHeader(links);

        $scope.pageLinks = value;
        $scope.nextPage = value.next || null;
        $scope.previousPage = value.previous || null;
      }

      $scope.getBuildStatus = function(build) {
        if (build.status.id == 'finished') {
          return build.result.name;
        } else {
          return build.status.name;
        }
      };

      function loadPlanList(url) {
        if (!url) {
          return;
        }
        $http.get(url)
          .success(function(data, status, headers){
            $scope.plans = new Collection(data, {
              limit: PER_PAGE
            });
            updatePageLinks(headers('Link'));
          });
      }

      $scope.loadPreviousPage = function() {
        $(document.body).scrollTop(0);
        loadBuildList($scope.pageLinks.previous);
      };

      $scope.loadNextPage = function() {
        $(document.body).scrollTop(0);
        loadBuildList($scope.pageLinks.next);
      };

      updatePageLinks(planList.headers('Link'));

      $scope.plans = new Collection(planList.data, {
        limit: PER_PAGE
      });
    },
    resolve: {
      planList: function($http) {
        return $http.get('/api/0/plans/?per_page=' + PER_PAGE);
      }
    }
  };
});
