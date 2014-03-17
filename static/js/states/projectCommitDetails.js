define([
  'app',
  'utils/sortBuildList'
], function(app, sortBuildList) {
  'use strict';

  return {
    parent: 'project_commits',
    url: ':commit_id/',
    templateUrl: 'partials/project-commit-details.html',
    controller: function($scope, $http, $state, projectData, commitData, Collection, flash) {
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
      $scope.builds = new Collection($scope, commitData.data.builds, {
        sortFunc: sortBuildList,
        limit: 100
      });
    },
    resolve: {
      commitData: function($http, $stateParams, projectData) {
        return $http.get('/api/0/projects/' + projectData.id + '/commits/' + $stateParams.commit_id + '/');
      }
    }
  };
});
