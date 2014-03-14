define(['app'], function(app) {
  'use strict';

  return {
    parent: 'project_details',
    url: 'commits/',
    templateUrl: 'partials/project-commit-list.html',
    controller: function($scope, commitList) {
      function fromCommits(commitList) {
        return commitList.map(function(commit){
          if (commit.message) {
            commit.subject = commit.message.split('\n')[0].substr(0, 128);
          } else if (commit.build) {
            commit.subject = commit.build.label;
          } else {
            commit.subject = 'A homeless commit';
          }
          return commit;
        });
      }

      $scope.commits = fromCommits(commitList.data);
    },
    resolve: {
      commitList: function($http, projectData) {
        return $http.get('/api/0/projects/' + projectData.data.id + '/commits/');
      }
    }
  };
});
