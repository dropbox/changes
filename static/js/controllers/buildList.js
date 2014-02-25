(function(){
  'use strict';

  define([
      'app',
      'utils/parseLinkHeader',
      'utils/sortBuildList'
    ], function(app, parseLinkHeader, sortBuildList) {
    var buildListCtrl = function(initial, $scope, $http, $stateParams, $location, Stream, Collection) {
      var stream,
          entrypoint = initial.entrypoint;

      function loadBuildList(url) {
        if (!url) {
          return;
        }
        $http.get(url)
          .success(function(data, status, headers){
            $scope.builds = new Collection($scope, data, {
              sortFunc: sortBuildList,
              limit: 100
            });
            $scope.pageLinks = parseLinkHeader(headers('Link'));
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

      $scope.pageLinks = parseLinkHeader(initial.headers('Link'));

      $scope.builds = new Collection($scope, initial.data, {
        sortFunc: sortBuildList,
        limit: 100
      });

      stream = new Stream($scope, entrypoint);
      stream.subscribe('build.update', function(data){
        $scope.builds.updateItem(data);
      });
    };

    app.controller('buildListCtrl', ['initial', '$scope', '$http', '$stateParams', '$location', 'stream', 'collection', buildListCtrl]);

    return buildListCtrl;
  });
})();
