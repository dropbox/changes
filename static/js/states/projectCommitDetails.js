define([
  'app',
  'utils/sortBuildList'
], function(app, sortBuildList) {
  'use strict';

  return {
    parent: 'project_commits',
    url: ':commit_id/',
    templateUrl: 'partials/project-commit-details.html',
    controller: function($scope, $http, $state, $stateParams, projectData, commitData, buildList,
                         Collection, CollectionPoller, flash) {

      // TODO(vishal): Figure out if we can replace this with createBuild.js
      $scope.createBuild = function() {
        var data = {
          repository: $scope.repository.url,
          sha: $scope.commit.sha
        };

        $http.post('/api/0/builds/', data)
          .success(function(data){
            $state.go('build_details', {build_id: data[0].id});
          })
          .error(function(){
            flash('error', 'There was an error while creating this build.');
          });
      };

      $scope.commit = commitData;
      $scope.repository = commitData.repository;
      $scope.builds = new Collection(buildList, {
        sortFunc: sortBuildList,
        limit: 100
      });

      var poller = new CollectionPoller({
        $scope: $scope,
        collection: $scope.builds,
        endpoint: '/api/0/projects/' + projectData.id + '/commits/' + $stateParams.commit_id + '/builds/'
      });
    },
    resolve: {
      commitData: function($http, $stateParams, projectData) {
        return $http.get('/api/0/projects/' + projectData.id + '/commits/' + $stateParams.commit_id + '/')
          .then(function(response){
            return response.data;
          });
      },
      buildList: function($http, $stateParams, projectData) {
        return $http.get('/api/0/projects/' + projectData.id + '/commits/' + $stateParams.commit_id + '/builds/')
          .then(function(response){
            return response.data;
          });
      }
    }
  };
});
