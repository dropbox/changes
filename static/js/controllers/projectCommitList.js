(function(){
  'use strict';

  define([
      'app',
      'directives/radialProgressBar',
      'directives/timeSince'], function(app) {
    app.controller('projectCommitListCtrl', [
      'initialProject', 'initialCommitList', '$scope', '$rootScope',
      function(initialProject, initialBuildList, $scope, $rootScope) {

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

      $scope.project = initialProject.data.project;
      $rootScope.activeProject = $scope.project;
      $scope.commits = fromCommits(initialBuildList.data.commits);

      $scope.getBuildStatus = function(build) {
        if (build.status.id == 'finished') {
          return build.result.name;
        } else {
          return build.status.name;
        }
      };

    }]);
  });
})();
