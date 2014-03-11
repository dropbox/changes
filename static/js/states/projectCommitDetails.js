define([
  'app',
  'utils/sortBuildList'
], function(app, sortBuildList) {
  'use strict';

  return {
    parent: 'project_commits',
    url: ':commit_id/',
    templateUrl: 'partials/project-commit-details.html',
    controller: function($scope, $rootScope, $http, $state, projectData, commitData, flash) {
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

        $http.post('/api/0/builds/', data)
          .success(function(data){
            $state.go('build_details', {build_id: data.build.id});
          })
          .error(function(){
            flash('error', 'There was an error while creating this build.');
          });
      };

      $scope.commit = commitData.data;
      $scope.repository = commitData.data.repository;
      $scope.builds = sortBuildList(commitData.data.builds);
    },
    resolve: {
      commitData: function($http, $stateParams, projectData) {
        return $http.get('/api/0/projects/' + projectData.data.id + '/commits/' + $stateParams.commit_id + '/');
      }
    }
  };
});
