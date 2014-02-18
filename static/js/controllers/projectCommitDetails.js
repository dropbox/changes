(function(){
  'use strict';

  define([
      'app',
      'utils/sortBuildList'], function(app, sortBuildList) {
    app.controller('projectCommitDetailsCtrl', [
        '$scope', '$rootScope', 'initialProject', 'initialCommit', '$http', '$location', '$routeParams', 'stream', 'flash',
        function($scope, $rootScope, initialProject, initialCommit, $http, $location, $routeParams, Stream, flash) {
      var stream,
          entrypoint = '/api/0/projects/' + $routeParams.project_id + '/commits/' + $routeParams.commit_id + '/';

      function addBuild(data) {
        $scope.$apply(function() {
          var updated = false,
              item_id = data.id,
              attr, result, item;

          if ($scope.builds.length > 0) {
            result = $.grep($scope.builds, function(e){ return e.id == item_id; });
            if (result.length > 0) {
              item = result[0];
              for (attr in data) {
                // ignore dateModified as we're updating this frequently and it causes
                // the dirty checking behavior in angular to respond poorly
                if (item[attr] != data[attr] && attr != 'dateModified') {
                  updated = true;
                  item[attr] = data[attr];
                }
                if (updated) {
                  item.dateModified = data.dateModified;
                }
              }
            }
          }
          if (!updated) {
            $scope.builds.unshift(data);
            sortBuildList($scope.builds);
            $scope.builds = $scope.builds.slice(0, 100);
          }
        });
      }

      $scope.getBuildStatus = function(build) {
        if (build.status.id == 'finished') {
          return build.result.name;
        } else {
          return build.status.name;
        }
      };

      $scope.createBuild = function() {
        var data = {
          repository: $scope.repository.url,
          sha: $scope.commit.sha
        };

        $http.post('/api/0/builds/' + $scope.build.id + '/', data)
          .success(function(data){
            $location.path(data.build.link);
          })
          .error(function(){
            flash('error', 'There was an error while creating this build.');
          });
      };

      $scope.project = initialProject.data;
      $scope.commit = initialCommit.data.commit;
      $scope.repository = initialCommit.data.repository;
      $scope.builds = sortBuildList(initialCommit.data.builds);
      $rootScope.activeProject = $scope.project;

      stream = new Stream($scope, entrypoint);
      stream.subscribe('job.update', addBuild);
    }]);
  });
})();
