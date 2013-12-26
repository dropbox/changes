(function(){
  'use strict';

  define(['app'], function(app) {
    app.controller('projectListCtrl', ['initial', '$scope', 'stream', function(initial, $scope, Stream) {
      var entrypoint = '/api/0/projects/',
          stream;

      function sortByDateCreated(a, b){
        if (a.dateCreated < b.dateCreated) {
          return 1;
        } else if (a.dateCreated > b.dateCreated) {
          return -1;
        } else {
          return 0;
        }
      }

      function getProjectClass(project) {
        if (project.lastBuild) {
          return 'result-' + project.lastBuild.result.id;
        }
        return 'result-unknown';
      }

      function addBuild(data) {
        var project_id = data.project.id,
            result, project;

        result = $.grep($scope.projects, function(e){ return e.id == project_id; });
        if (!result.length) {
          // project not found
          return;
        }

        project = result[0];

        if (data.status.id != 'finished') {
          // not finished, so not relevant
          return;
        }

        // older than the 'current' last build
        if (data.dateCreated < project.lastBuild.dateCreated) {
          return;
        }

        $scope.$apply(function() {
          project.lastBuild = data;
        });
      }

      $scope.getProjectClass = getProjectClass;
      $scope.projects = initial.data.projects;

      stream = new Stream($scope, entrypoint);
      stream.subscribe('build.update', addBuild);
    }]);
  });
})();
